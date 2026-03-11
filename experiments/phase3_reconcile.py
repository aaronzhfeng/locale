"""
Phase 3: Dual-Endpoint Reconciliation

Each undirected edge (u,v) appears in two ego-graphs: Ego(u) and Ego(v).
Phase 2 produces locally optimal orientations at each endpoint.
Phase 3 reconciles disagreements between endpoints.

Reconciliation strategies:
1. Agreement: both endpoints agree → accept direction
2. Confidence-weighted: use the endpoint with higher soft score margin
3. Degree-weighted: trust the higher-degree endpoint (more CI constraints)
4. Dawid-Skene (simplified): treat endpoints as annotators with latent error rates
"""

import json
from pathlib import Path
from collections import Counter


def reconcile_edges(phase2_results, raw_ego_results, per_node_info):
    """Reconcile edge orientations from dual endpoints.

    For each edge (u,v), both Ego(u) and Ego(v) may have oriented it.
    This function resolves disagreements.

    Returns dict of reconciled edges with provenance.
    """
    # Build per-edge predictions from both endpoints
    edge_predictions = {}  # (u,v) sorted -> list of (endpoint, direction, score_margin)

    for node, info in phase2_results["per_node"].items():
        directions = info.get("directions", {})
        for nbr, direction in directions.items():
            edge_key = tuple(sorted([node, nbr]))

            # Get soft score margin from votes
            toward = 0
            away = 0
            for r in raw_ego_results:
                if r["center_node"] != node:
                    continue
                if set(r["edge"]) != {node, nbr}:
                    continue
                if r["predicted"] == f"{nbr}->{node}":
                    toward += 1
                elif r["predicted"] == f"{node}->{nbr}":
                    away += 1
            total = toward + away
            margin = abs(toward - away) / max(total, 1)

            degree = per_node_info.get(node, {}).get("degree", 0)
            n_constraints = len(per_node_info.get(node, {}).get("ci_facts", []))

            edge_predictions.setdefault(edge_key, []).append({
                "endpoint": node,
                "direction": direction,
                "margin": margin,
                "degree": degree,
                "n_constraints": n_constraints,
                "was_flipped": any(
                    f[0] == nbr for f in info.get("hard_flips", [])
                ),
            })

    # Reconcile
    reconciled = {}
    for edge_key, preds in edge_predictions.items():
        if len(preds) == 1:
            # Only one endpoint (edge appears in one ego-graph)
            reconciled[edge_key] = {
                "direction": preds[0]["direction"],
                "method": "single_endpoint",
                "endpoint": preds[0]["endpoint"],
            }
        elif len(preds) == 2:
            p1, p2 = preds
            if p1["direction"] == p2["direction"]:
                reconciled[edge_key] = {
                    "direction": p1["direction"],
                    "method": "agreement",
                }
            else:
                # Disagreement — use multiple resolution strategies
                strategies = {}

                # 1. Confidence: higher margin wins
                if p1["margin"] > p2["margin"]:
                    strategies["confidence"] = p1["direction"]
                elif p2["margin"] > p1["margin"]:
                    strategies["confidence"] = p2["direction"]
                else:
                    strategies["confidence"] = p1["direction"]  # tie-break: first

                # 2. Degree: higher degree endpoint wins
                if p1["degree"] > p2["degree"]:
                    strategies["degree"] = p1["direction"]
                elif p2["degree"] > p1["degree"]:
                    strategies["degree"] = p2["direction"]
                else:
                    strategies["degree"] = strategies["confidence"]

                # 3. Constraint count: more CI constraints = more constrained
                if p1["n_constraints"] > p2["n_constraints"]:
                    strategies["constraints"] = p1["direction"]
                elif p2["n_constraints"] > p1["n_constraints"]:
                    strategies["constraints"] = p2["direction"]
                else:
                    strategies["constraints"] = strategies["confidence"]

                # 4. Hard-flip aware: if one was hard-flipped, trust the constraint
                if p1["was_flipped"] and not p2["was_flipped"]:
                    strategies["hard_flip"] = p1["direction"]
                elif p2["was_flipped"] and not p1["was_flipped"]:
                    strategies["hard_flip"] = p2["direction"]
                else:
                    strategies["hard_flip"] = strategies["confidence"]

                # Default: use confidence
                reconciled[edge_key] = {
                    "direction": strategies["confidence"],
                    "method": "disagreement_confidence",
                    "strategies": strategies,
                    "endpoints": [
                        {"node": p["endpoint"], "dir": p["direction"],
                         "margin": p["margin"], "degree": p["degree"]}
                        for p in preds
                    ],
                }
        else:
            # Edge in 3+ ego-graphs (shouldn't happen in standard setup)
            # Majority vote across endpoints
            dirs = [p["direction"] for p in preds]
            majority = Counter(dirs).most_common(1)[0][0]
            reconciled[edge_key] = {
                "direction": majority,
                "method": "multi_endpoint_majority",
            }

    return reconciled


def evaluate_reconciled(reconciled, gt_edges_set):
    """Evaluate reconciled edges against ground truth."""
    correct = 0
    total = 0
    agreements = 0
    disagreements = 0
    results_by_method = {}

    for edge_key, info in reconciled.items():
        u, v = edge_key
        gt_dir = None
        if f"{u}->{v}" in gt_edges_set:
            gt_dir = f"{u}->{v}"
        elif f"{v}->{u}" in gt_edges_set:
            gt_dir = f"{v}->{u}"
        else:
            continue  # edge not in GT

        total += 1
        is_correct = info["direction"] == gt_dir
        if is_correct:
            correct += 1

        method = info["method"]
        if method not in results_by_method:
            results_by_method[method] = {"correct": 0, "total": 0}
        results_by_method[method]["total"] += 1
        if is_correct:
            results_by_method[method]["correct"] += 1

        if method == "agreement":
            agreements += 1
        elif method.startswith("disagreement"):
            disagreements += 1

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / max(total, 1),
        "agreements": agreements,
        "disagreements": disagreements,
        "by_method": results_by_method,
    }


def run_phase3(results_dir_path):
    """Run Phase 3 on Phase 2 results."""
    results_dir = Path(results_dir_path)
    phase2_path = results_dir / "phase2_results.json"
    phase1_path = results_dir / "mve_results.json"

    if not phase2_path.exists() or not phase1_path.exists():
        return None

    with open(phase2_path) as f:
        phase2 = json.load(f)
    with open(phase1_path) as f:
        phase1 = json.load(f)

    raw_ego = phase1.get("raw_results_b", [])
    per_node = phase1.get("per_node", {})

    # Build GT edge set
    gt_edges_set = set()
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            gt_edges_set.add(f"{e[0]}->{e[1]}")

    reconciled = reconcile_edges(phase2, raw_ego, per_node)
    evaluation = evaluate_reconciled(reconciled, gt_edges_set)

    # Also evaluate alternative strategies for disagreements
    alt_evals = {}
    for strategy_name in ["degree", "constraints", "hard_flip"]:
        alt_reconciled = dict(reconciled)
        for edge_key, info in reconciled.items():
            if "strategies" in info:
                alt_info = dict(info)
                alt_info["direction"] = info["strategies"].get(strategy_name, info["direction"])
                alt_reconciled[edge_key] = alt_info
        alt_evals[strategy_name] = evaluate_reconciled(alt_reconciled, gt_edges_set)

    return {
        "reconciled": {str(k): v for k, v in reconciled.items()},
        "evaluation": evaluation,
        "alt_evaluations": alt_evals,
        "n_unique_edges": len(reconciled),
    }


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance Full", "mve_27b_insurance_full"),
        ("Alarm Full", "mve_27b_alarm_full"),
        ("Sachs Full", "mve_27b_sachs_full"),
        ("Child Full", "mve_27b_child_full"),
    ]

    print("=" * 70)
    print("LOCALE Phase 3: Dual-Endpoint Reconciliation")
    print("=" * 70)

    for label, dirname in targets:
        result = run_phase3(results_dir / dirname)
        if result is None:
            print(f"\n{label}: SKIP (missing Phase 2 results)")
            continue

        print(f"\n{'='*50}")
        print(f"{label}")
        print(f"{'='*50}")

        ev = result["evaluation"]
        n_unique = result["n_unique_edges"]
        print(f"  Unique edges: {n_unique}")
        print(f"  Accuracy: {ev['correct']}/{ev['total']} ({ev['accuracy']:.1%})")
        print(f"  Agreements: {ev['agreements']}, Disagreements: {ev['disagreements']}")

        if ev["by_method"]:
            print(f"\n  By resolution method:")
            for method, stats in sorted(ev["by_method"].items()):
                acc = stats["correct"] / max(stats["total"], 1)
                print(f"    {method}: {stats['correct']}/{stats['total']} ({acc:.1%})")

        # Alternative strategies
        print(f"\n  Disagreement resolution strategies:")
        print(f"    confidence:  {ev['accuracy']:.1%}")
        for strat, alt_ev in result["alt_evaluations"].items():
            print(f"    {strat:12s}: {alt_ev['accuracy']:.1%}")

        # Save
        out_path = results_dir / dirname / "phase3_results.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
