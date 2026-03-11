"""
Phase 5: Budgeted Hard-Tail Fallback (Proposal v2 Section 4.7)

After Phase 4 propagation, a set of low-confidence edges remains. Phase 5
queries these specific edges with per-edge prompts (MosaCD-style), optionally
enriched with nearby oriented-chain context.

Two modes:
1. PE-fallback: Use existing per-edge (PE) results from Phase 1 for
   disagreement/low-confidence edges. No new LLM queries.
2. Enriched fallback: Make new per-edge queries with context from
   already-committed orientations. Requires LLM API.

Budget: max 10-15% of skeleton edges get fallback queries.
If residual exceeds budget, output partial selective orientations instead
of forcing completion.
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict


def identify_hard_tail(phase3_results, phase4_results=None,
                       confidence_threshold=0.6):
    """Identify edges in the hard tail that need fallback.

    Hard-tail edges: disagreement edges, single-endpoint edges with low
    margin, or any edge where Phase 3 confidence < threshold.

    Returns list of (edge_key_str, info, reason) tuples sorted by
    difficulty (hardest first).
    """
    reconciled = phase3_results["reconciled"]
    hard_tail = []

    for edge_key_str, info in reconciled.items():
        method = info.get("method", "unknown")
        reason = None

        if method == "disagreement_confidence":
            # Endpoints disagree — always hard tail
            reason = "disagreement"
        elif method == "single_endpoint":
            # Only one endpoint saw this edge — potentially unreliable
            reason = "single_endpoint"
        elif method == "agreement":
            # Both agree — skip unless very low margin
            continue
        else:
            reason = f"unknown_method_{method}"

        if reason:
            # Compute difficulty score (lower = harder)
            if "endpoints" in info:
                margins = [ep.get("margin", 0.5) for ep in info["endpoints"]]
                difficulty = max(margins) - min(margins)
            else:
                difficulty = 0.5
            hard_tail.append((edge_key_str, info, reason, difficulty))

    # Sort by difficulty ascending (hardest first)
    hard_tail.sort(key=lambda x: x[3])

    return hard_tail


def pe_fallback(hard_tail_edges, phase1_data, gt_edges_set=None,
                budget_fraction=0.15, override_mode="tiebreak"):
    """Use existing per-edge results as fallback for hard-tail edges.

    For each hard-tail edge, check if per-edge (PE) results from Phase 1
    give a different (possibly better) orientation.

    Args:
        hard_tail_edges: list from identify_hard_tail
        phase1_data: Phase 1 mve_results.json data
        gt_edges_set: set of "u->v" ground truth strings (for eval)
        budget_fraction: max fraction of skeleton to query

    Returns dict of edge_key_str -> {direction, source, ...}
    """
    raw_pe = phase1_data.get("raw_results_a", [])
    per_node = phase1_data.get("per_node", {})

    # Count skeleton edges for budget
    skeleton_edges = set()
    for node, info in per_node.items():
        for nbr in info.get("neighbors", []):
            skeleton_edges.add(frozenset({node, nbr}))
    max_fallback = max(1, int(len(skeleton_edges) * budget_fraction))

    # Build PE vote counts per edge
    pe_votes = defaultdict(lambda: defaultdict(int))
    for r in raw_pe:
        edge_key = tuple(sorted(r["edge"]))
        predicted = r["predicted"]
        pe_votes[edge_key][predicted] += 1

    fallback_results = {}
    n_queried = 0

    for edge_key_str, info, reason, difficulty in hard_tail_edges:
        if n_queried >= max_fallback:
            break

        # Parse edge key
        try:
            parts = edge_key_str.strip("()' ").replace("'", "").split(", ")
            u, v = parts[0].strip(), parts[1].strip()
        except (ValueError, IndexError):
            continue

        edge_key = tuple(sorted([u, v]))

        # Get PE votes for this edge
        votes = pe_votes.get(edge_key, {})
        if not votes:
            # PE didn't cover this edge
            fallback_results[edge_key_str] = {
                "direction": info["direction"],
                "source": "no_pe_data",
                "original_source": info.get("method"),
                "changed": False,
            }
            continue

        n_queried += 1

        # PE majority vote
        best_dir = max(votes, key=votes.get)
        total_votes = sum(votes.values())
        pe_margin = votes[best_dir] / max(total_votes, 1)

        # Compare PE with ego-graph direction
        ego_dir = info["direction"]
        pe_agrees = best_dir == ego_dir

        # Only consider PE override for disagreement edges.
        # Single-endpoint edges already have a clear ego signal.
        is_disagreement = reason == "disagreement"

        if pe_agrees:
            # PE confirms ego — keep ego direction
            fallback_results[edge_key_str] = {
                "direction": ego_dir,
                "source": "pe_confirmed",
                "pe_direction": best_dir,
                "pe_margin": pe_margin,
                "pe_votes": dict(votes),
                "original_source": info.get("method"),
                "changed": False,
            }
        elif not is_disagreement:
            # Single-endpoint edge: PE disagrees but ego had clear signal.
            # Keep ego (safer).
            fallback_results[edge_key_str] = {
                "direction": ego_dir,
                "source": "ego_kept_single",
                "pe_direction": best_dir,
                "pe_margin": pe_margin,
                "pe_votes": dict(votes),
                "original_source": info.get("method"),
                "changed": False,
            }
        else:
            # Disagreement edge: use PE as a 2-out-of-3 tiebreaker.
            # Both endpoints gave different directions. PE votes with one.
            # Override to PE direction only if PE agrees with one endpoint
            # (forming a 2/3 majority) AND the endpoint it agrees with
            # has reasonable margin.
            endpoints = info.get("endpoints", [])
            pe_agrees_with_endpoint = False
            agreeing_endpoint_margin = 0

            for ep in endpoints:
                if ep.get("dir") == best_dir:
                    pe_agrees_with_endpoint = True
                    agreeing_endpoint_margin = ep.get("margin", 0)
                    break

            if pe_agrees_with_endpoint and best_dir != ego_dir:
                # PE + one endpoint form 2/3 majority against current direction
                fallback_results[edge_key_str] = {
                    "direction": best_dir,
                    "source": "pe_tiebreak",
                    "pe_direction": best_dir,
                    "pe_margin": pe_margin,
                    "pe_votes": dict(votes),
                    "ego_direction": ego_dir,
                    "agreeing_endpoint_margin": agreeing_endpoint_margin,
                    "original_source": info.get("method"),
                    "changed": True,
                }
            else:
                # PE doesn't form a majority — keep current
                fallback_results[edge_key_str] = {
                    "direction": ego_dir,
                    "source": "ego_kept_no_majority",
                    "pe_direction": best_dir,
                    "pe_margin": pe_margin,
                    "pe_votes": dict(votes),
                    "original_source": info.get("method"),
                    "changed": False,
                }

    return fallback_results, n_queried, max_fallback


def run_phase5(results_dir_path, budget_fraction=0.15):
    """Run Phase 5 budgeted fallback on Phase 3/4 results.

    Uses existing PE data (no new LLM queries).
    """
    results_dir = Path(results_dir_path)
    phase3_path = results_dir / "phase3_results.json"
    phase1_path = results_dir / "mve_results.json"

    if not phase3_path.exists() or not phase1_path.exists():
        return None

    with open(phase3_path) as f:
        phase3 = json.load(f)
    with open(phase1_path) as f:
        phase1 = json.load(f)

    # Phase 4 results (optional — if not available, use Phase 3)
    phase4_path = results_dir / "phase4_propagation_results.json"
    phase4 = None
    if phase4_path.exists():
        with open(phase4_path) as f:
            phase4 = json.load(f)

    # Build GT
    per_node = phase1.get("per_node", {})
    gt_edges_set = set()
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            gt_edges_set.add(f"{e[0]}->{e[1]}")

    # Identify hard tail
    hard_tail = identify_hard_tail(phase3)

    # Run PE fallback
    fallback_results, n_queried, max_budget = pe_fallback(
        hard_tail, phase1, gt_edges_set, budget_fraction
    )

    # Build final orientations: start with Phase 3, override with fallback
    reconciled = phase3["reconciled"]
    final = {}
    for edge_key_str, info in reconciled.items():
        if edge_key_str in fallback_results:
            fb = fallback_results[edge_key_str]
            final[edge_key_str] = {
                "direction": fb["direction"],
                "source": fb["source"],
                "changed": fb.get("changed", False),
            }
        else:
            final[edge_key_str] = {
                "direction": info["direction"],
                "source": info.get("method", "phase3"),
                "changed": False,
            }

    # Evaluate
    p3_correct = 0
    p5_correct = 0
    total = 0
    changes = []

    for edge_key_str, info in final.items():
        try:
            parts = edge_key_str.strip("()' ").replace("'", "").split(", ")
            u, v = parts[0].strip(), parts[1].strip()
        except (ValueError, IndexError):
            continue

        gt_dir = None
        if f"{u}->{v}" in gt_edges_set:
            gt_dir = f"{u}->{v}"
        elif f"{v}->{u}" in gt_edges_set:
            gt_dir = f"{v}->{u}"
        if gt_dir is None:
            continue

        total += 1
        p5_is_correct = info["direction"] == gt_dir
        if p5_is_correct:
            p5_correct += 1

        # P3 baseline
        p3_dir = reconciled.get(edge_key_str, {}).get("direction")
        if p3_dir == gt_dir:
            p3_correct += 1

        if info.get("changed"):
            old_dir = reconciled.get(edge_key_str, {}).get("direction")
            changes.append({
                "edge": edge_key_str,
                "old": old_dir,
                "new": info["direction"],
                "gt": gt_dir,
                "improved": info["direction"] == gt_dir and old_dir != gt_dir,
                "worsened": old_dir == gt_dir and info["direction"] != gt_dir,
            })

    n_improved = sum(1 for c in changes if c["improved"])
    n_worsened = sum(1 for c in changes if c["worsened"])

    result = {
        "metadata": {
            "phase": 5,
            "method": "pe_fallback",
            "budget_fraction": budget_fraction,
        },
        "hard_tail": {
            "n_identified": len(hard_tail),
            "n_queried": n_queried,
            "max_budget": max_budget,
            "by_reason": {},
        },
        "fallback": {
            "n_changes": len(changes),
            "n_improved": n_improved,
            "n_worsened": n_worsened,
            "net_gain": n_improved - n_worsened,
            "changes": changes,
        },
        "evaluation": {
            "phase3_accuracy": p3_correct / max(total, 1),
            "phase3_correct": p3_correct,
            "phase5_accuracy": p5_correct / max(total, 1),
            "phase5_correct": p5_correct,
            "total_edges": total,
            "delta_pp": round((p5_correct - p3_correct) / max(total, 1) * 100, 1),
        },
        "final_orientations": final,
    }

    # Count by reason
    for _, _, reason, _ in hard_tail:
        result["hard_tail"]["by_reason"][reason] = \
            result["hard_tail"]["by_reason"].get(reason, 0) + 1

    return result


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_10k_k10_debiased"),
        ("Alarm", "mve_27b_alarm_10k_k10_debiased"),
        ("Sachs", "mve_27b_sachs_10k_k10_debiased"),
        ("Child", "mve_27b_child_10k_k10_debiased"),
        ("Asia", "mve_27b_asia_10k_k10_debiased"),
        ("Hepar2", "mve_27b_hepar2_10k_k10_debiased"),
    ]

    print("=" * 70)
    print("LOCALE Phase 5: Budgeted Hard-Tail Fallback (PE)")
    print("=" * 70)

    summary_rows = []

    for label, dirname in targets:
        result = run_phase5(results_dir / dirname)
        if result is None:
            continue

        ht = result["hard_tail"]
        fb = result["fallback"]
        ev = result["evaluation"]

        print(f"\n{'='*50}")
        print(f"{label}")
        print(f"{'='*50}")
        print(f"  Hard tail: {ht['n_identified']} edges "
              f"(budget: {ht['max_budget']}, queried: {ht['n_queried']})")
        print(f"  By reason: {ht['by_reason']}")
        print(f"  Changes: {fb['n_changes']} "
              f"(improved: {fb['n_improved']}, worsened: {fb['n_worsened']}, "
              f"net: {fb['net_gain']:+d})")

        p3_pct = ev["phase3_accuracy"] * 100
        p5_pct = ev["phase5_accuracy"] * 100
        print(f"\n  Phase 3: {ev['phase3_correct']}/{ev['total_edges']} ({p3_pct:.1f}%)")
        print(f"  Phase 5: {ev['phase5_correct']}/{ev['total_edges']} ({p5_pct:.1f}%)")
        print(f"  Delta: {ev['delta_pp']:+.1f}pp")

        if fb["changes"]:
            print(f"\n  Edge changes:")
            for c in fb["changes"]:
                status = "IMPROVED" if c["improved"] else "WORSENED" if c["worsened"] else "NEUTRAL"
                print(f"    {c['edge']}: {c['old']} -> {c['new']} (gt={c['gt']}) [{status}]")

        summary_rows.append({
            "network": label,
            "hard_tail": ht["n_identified"],
            "changes": fb["n_changes"],
            "improved": fb["n_improved"],
            "worsened": fb["n_worsened"],
            "p3": p3_pct,
            "p5": p5_pct,
            "delta": ev["delta_pp"],
        })

        # Save
        out_path = results_dir / dirname / "phase5_fallback_results.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

    if summary_rows:
        print(f"\n{'='*70}")
        print("SUMMARY: PE Fallback")
        print(f"{'='*70}")
        print(f"{'Network':<12} {'Tail':>5} {'Chg':>4} {'Imp':>4} {'Wrs':>4} "
              f"{'P3':>7} {'P5':>7} {'Delta':>7}")
        for r in summary_rows:
            print(f"{r['network']:<12} {r['hard_tail']:>5} {r['changes']:>4} "
                  f"{r['improved']:>4} {r['worsened']:>4} "
                  f"{r['p3']:>6.1f}% {r['p5']:>6.1f}% {r['delta']:>+6.1f}pp")


if __name__ == "__main__":
    main()
