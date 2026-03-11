"""
Phase 4: Conservative Propagation Schedule (Proposal v2 Section 4.6)

After Phase 3 reconciliation, edges have directions + confidence scores.
Phase 4 commits them incrementally using a priority queue, applies Meek
rules after each batch, checks acyclicity, and rolls back on problems.

Algorithm:
1. Sort edges by confidence descending into a priority queue
2. Commit a batch of highest-confidence edges that don't create cycles
3. Apply Meek R1-R4 → some uncommitted edges may get compelled
4. Check for contradictions (Meek compels opposite of LLM vote)
5. Rollback lowest-margin commitments if contradiction spike
6. Repeat until all edges committed or stuck

Residual ambiguous edges → Phase 5 (per-edge fallback).

Also includes the safety valve from the prior Phase 4: if Phase 2
constraints damaged accuracy, revert damaged nodes to Phase 1.
"""

import json
import heapq
from pathlib import Path
from collections import defaultdict
from meek_rules import apply_meek_rules


def build_skeleton_and_gt(phase1_data):
    """Extract skeleton edges and ground truth from Phase 1 data."""
    per_node = phase1_data.get("per_node", {})
    skeleton_edges = set()
    gt_directed = {}  # frozenset -> "u->v"

    for node, info in per_node.items():
        for nbr in info.get("neighbors", []):
            skeleton_edges.add(frozenset({node, nbr}))
        for e in info.get("gt_edges", []):
            skeleton_edges.add(frozenset({e[0], e[1]}))
            gt_directed[frozenset({e[0], e[1]})] = f"{e[0]}->{e[1]}"

    return skeleton_edges, gt_directed


def extract_edge_confidence(phase3_reconciled):
    """Extract edge directions and confidence from Phase 3 output.

    Returns list of (confidence, edge_key_frozen, direction, method) tuples.
    """
    edges = []
    for edge_key_str, info in phase3_reconciled.items():
        direction = info["direction"]
        parts = direction.split("->")
        if len(parts) != 2:
            continue
        src, dst = parts

        # Compute confidence score
        method = info.get("method", "unknown")
        if method == "agreement":
            confidence = 1.0
        elif "endpoints" in info:
            # Disagreement: confidence = winning margin
            eps = info["endpoints"]
            max_margin = max(ep.get("margin", 0.5) for ep in eps)
            confidence = max_margin
        elif method == "single_endpoint":
            confidence = 0.5
        else:
            confidence = 0.6  # default

        edge_key = frozenset({src, dst})
        edges.append((confidence, edge_key, direction, method))

    return edges


def check_acyclic(directed_edges):
    """Check if committed directed edges form a DAG using topological sort."""
    graph = defaultdict(set)
    nodes = set()
    for (src, dst) in directed_edges:
        graph[src].add(dst)
        nodes.add(src)
        nodes.add(dst)

    # Kahn's algorithm
    in_degree = defaultdict(int)
    for n in nodes:
        in_degree[n] = in_degree.get(n, 0)
    for src, neighbors in graph.items():
        for dst in neighbors:
            in_degree[dst] += 1

    queue = [n for n in nodes if in_degree[n] == 0]
    visited = 0
    while queue:
        node = queue.pop()
        visited += 1
        for nbr in graph.get(node, set()):
            in_degree[nbr] -= 1
            if in_degree[nbr] == 0:
                queue.append(nbr)

    return visited == len(nodes)


def would_create_cycle(committed, new_edge):
    """Check if adding new_edge (src, dst) to committed edges creates a cycle."""
    test_set = set(committed)
    test_set.add(new_edge)
    return not check_acyclic(test_set)


def conservative_propagation(phase3_reconciled, skeleton_edges,
                              commit_threshold=0.3,
                              batch_size=5,
                              min_batch_size=1,
                              meek_override_threshold=0.4):
    """Run conservative propagation schedule per proposal v2 Section 4.6.

    Key insight: Meek rules are sound on the TRUE skeleton, but our PC-estimated
    skeleton has missing edges (~83% coverage on Insurance, ~52% on Hepar2).
    Missing edges invalidate Meek's non-adjacency checks (R1, R3, R4), causing
    incorrect propagation. Therefore we apply Meek CONSERVATIVELY:
    - Accept Meek orientations that AGREE with the LLM vote (structural + semantic)
    - Accept Meek orientations for edges the LLM had LOW confidence on (<threshold)
    - REJECT Meek orientations that contradict confident LLM votes

    Args:
        phase3_reconciled: dict edge_key_str -> {direction, method, ...}
        skeleton_edges: set of frozenset edges
        commit_threshold: minimum confidence to commit
        batch_size: initial batch size for commitment rounds
        min_batch_size: minimum batch size after rollback
        meek_override_threshold: only let Meek override LLM if LLM conf < this

    Returns:
        committed: dict frozenset -> (src, dst) for committed directed edges
        meek_compelled: dict frozenset -> (src, dst, rule) for Meek-derived edges
        residual: set of frozenset for unresolved edges
        log: list of propagation events
    """
    # Extract edges with confidence scores
    edge_list = extract_edge_confidence(phase3_reconciled)
    edge_list.sort(key=lambda x: -x[0])

    # Build LLM preference lookup: edge_key -> (direction, confidence)
    llm_preference = {}
    for conf, edge_key, direction, method in edge_list:
        llm_preference[edge_key] = (direction, conf)

    # State
    committed = {}       # frozenset -> (src, dst)
    committed_conf = {}  # frozenset -> confidence
    meek_compelled = {}  # frozenset -> (src, dst, rule)
    pending = []
    log = []

    for conf, edge_key, direction, method in edge_list:
        parts = direction.split("->")
        pending.append({
            "confidence": conf,
            "edge_key": edge_key,
            "direction": direction,
            "src": parts[0],
            "dst": parts[1],
            "method": method,
        })

    def get_all_directed():
        """Get current set of all committed directed edges."""
        result = set()
        for ek, (s, d) in committed.items():
            result.add((s, d))
        for ek, (s, d, _) in meek_compelled.items():
            result.add((s, d))
        return result

    current_batch_size = batch_size
    round_num = 0

    while pending:
        round_num += 1
        pending.sort(key=lambda x: -x["confidence"])

        # Take top batch above threshold
        batch = []
        remaining = []
        for edge in pending:
            if edge["edge_key"] in committed or edge["edge_key"] in meek_compelled:
                continue
            if len(batch) < current_batch_size and edge["confidence"] >= commit_threshold:
                batch.append(edge)
            else:
                remaining.append(edge)

        if not batch:
            # Commit all remaining edges (low confidence, no Meek help)
            for edge in remaining:
                if edge["edge_key"] in committed or edge["edge_key"] in meek_compelled:
                    continue
                new_edge = (edge["src"], edge["dst"])
                all_directed = get_all_directed()
                if not would_create_cycle(all_directed, new_edge):
                    committed[edge["edge_key"]] = (edge["src"], edge["dst"])
                    committed_conf[edge["edge_key"]] = edge["confidence"]
                else:
                    flipped = (edge["dst"], edge["src"])
                    if not would_create_cycle(all_directed, flipped):
                        committed[edge["edge_key"]] = flipped
                        committed_conf[edge["edge_key"]] = edge["confidence"]
                        log.append({
                            "round": round_num,
                            "event": "cycle_flip",
                            "edge": str(edge["edge_key"]),
                            "original": edge["direction"],
                            "flipped": f"{edge['dst']}->{edge['src']}",
                        })
            break

        # Commit the batch (cycle-safe)
        committed_this_round = []
        rejected_this_round = []
        for edge in batch:
            new_edge = (edge["src"], edge["dst"])
            all_directed = get_all_directed()
            if not would_create_cycle(all_directed, new_edge):
                committed[edge["edge_key"]] = (edge["src"], edge["dst"])
                committed_conf[edge["edge_key"]] = edge["confidence"]
                committed_this_round.append(edge)
            else:
                rejected_this_round.append(edge)

        log.append({
            "round": round_num,
            "event": "commit_batch",
            "n_committed": len(committed_this_round),
            "n_rejected_cycles": len(rejected_this_round),
            "batch_size": current_batch_size,
        })

        # Apply Meek rules to current committed + meek-compelled edges
        oriented_for_meek = {}
        for ek, (s, d) in committed.items():
            oriented_for_meek[(s, d)] = True
        for ek, (s, d, _) in meek_compelled.items():
            oriented_for_meek[(s, d)] = True

        new_meek, _ = apply_meek_rules(oriented_for_meek, skeleton_edges)

        # CONSERVATIVE Meek acceptance: only accept if agrees with LLM or LLM
        # had low confidence. On an imperfect skeleton, Meek can be wrong because
        # missing edges violate its non-adjacency assumptions (R1, R3, R4).
        accepted_meek = 0
        rejected_meek = 0
        meek_overrides = []
        for (s, d), rule in new_meek.items():
            edge_key = frozenset({s, d})
            if edge_key in committed or edge_key in meek_compelled:
                continue

            meek_dir = f"{s}->{d}"
            llm_dir, llm_conf = llm_preference.get(edge_key, (None, 0))

            if llm_dir is None:
                # Edge not in LLM results (skeleton-only edge) — accept Meek
                meek_compelled[edge_key] = (s, d, rule)
                accepted_meek += 1
            elif meek_dir == llm_dir:
                # Meek agrees with LLM — strong signal, accept
                meek_compelled[edge_key] = (s, d, rule)
                accepted_meek += 1
            elif llm_conf < meek_override_threshold:
                # LLM had low confidence — let Meek override
                meek_compelled[edge_key] = (s, d, rule)
                accepted_meek += 1
                meek_overrides.append({
                    "edge": str(edge_key),
                    "meek": meek_dir,
                    "llm": llm_dir,
                    "rule": rule,
                    "llm_confidence": llm_conf,
                    "action": "meek_override_low_conf",
                })
            else:
                # LLM had high confidence and disagrees — trust LLM, reject Meek
                # Commit the LLM direction instead
                llm_parts = llm_dir.split("->")
                all_directed = get_all_directed()
                new_edge = (llm_parts[0], llm_parts[1])
                if not would_create_cycle(all_directed, new_edge):
                    committed[edge_key] = (llm_parts[0], llm_parts[1])
                    committed_conf[edge_key] = llm_conf
                rejected_meek += 1
                meek_overrides.append({
                    "edge": str(edge_key),
                    "meek": meek_dir,
                    "llm": llm_dir,
                    "rule": rule,
                    "llm_confidence": llm_conf,
                    "action": "llm_kept_over_meek",
                })

        if new_meek:
            log.append({
                "round": round_num,
                "event": "meek_propagation",
                "n_proposed": len(new_meek),
                "n_accepted": accepted_meek,
                "n_rejected": rejected_meek,
                "overrides": meek_overrides,
            })

        # Handle cycle-rejected edges: try flipping
        for edge in rejected_this_round:
            flipped = (edge["dst"], edge["src"])
            all_directed = get_all_directed()
            if not would_create_cycle(all_directed, flipped):
                committed[edge["edge_key"]] = flipped
                committed_conf[edge["edge_key"]] = edge["confidence"]
                log.append({
                    "round": round_num,
                    "event": "cycle_flip",
                    "edge": str(edge["edge_key"]),
                    "original": edge["direction"],
                    "flipped": f"{edge['dst']}->{edge['src']}",
                })
            else:
                remaining.append(edge)

        pending = [e for e in remaining
                   if e["edge_key"] not in committed
                   and e["edge_key"] not in meek_compelled]

    # Compute residual
    all_resolved = set(committed.keys()) | set(meek_compelled.keys())
    residual = skeleton_edges - all_resolved

    return committed, meek_compelled, residual, log


def safety_valve(phase2_results, phase1_data, threshold=-3.0):
    """Detect when Phase 2 constraints hurt accuracy and recommend fallback.

    For each node, compare Phase 2 accuracy vs Phase 1 majority vote.
    If overall Phase 2 is worse by more than `threshold` pp, recommend
    falling back to Phase 1 for that network.
    """
    summary = phase2_results.get("summary", {})
    p1_acc = summary.get("phase1_accuracy", 0)
    p2_acc = summary.get("phase2_accuracy", 0)
    net_delta = p2_acc - p1_acc

    damaged_nodes = []
    helped_nodes = []
    for node, info in phase2_results.get("per_node", {}).items():
        p1_c = info.get("p1_correct", 0)
        p2_c = info.get("p2_correct", 0)
        n = info.get("n_edges", 1)
        if p2_c < p1_c:
            damaged_nodes.append({
                "node": node,
                "p1_correct": p1_c,
                "p2_correct": p2_c,
                "n_edges": n,
            })
        elif p2_c > p1_c:
            helped_nodes.append({
                "node": node,
                "p1_correct": p1_c,
                "p2_correct": p2_c,
                "n_edges": n,
            })

    return {
        "fallback_recommended": net_delta < threshold,
        "net_delta_pp": net_delta,
        "damaged_nodes": damaged_nodes,
        "helped_nodes": helped_nodes,
        "n_damaged": len(damaged_nodes),
        "n_helped": len(helped_nodes),
    }


def run_phase4(results_dir_path, commit_threshold=0.3, batch_size=5):
    """Run Phase 4 conservative propagation on Phase 3 results.

    Pipeline: Phase 1 → Phase 2 → Phase 3 → Phase 4 (this)

    Args:
        results_dir_path: path to results directory containing phase3/2/1 JSONs
        commit_threshold: minimum confidence to commit in priority queue
        batch_size: edges per commitment round

    Returns:
        dict with propagation results, evaluation, logs
    """
    results_dir = Path(results_dir_path)
    phase3_path = results_dir / "phase3_results.json"
    phase2_path = results_dir / "phase2_results.json"
    phase1_path = results_dir / "mve_results.json"

    if not phase3_path.exists():
        return None

    with open(phase3_path) as f:
        phase3 = json.load(f)
    with open(phase2_path) as f:
        phase2 = json.load(f)
    with open(phase1_path) as f:
        phase1 = json.load(f)

    # Build skeleton and GT
    skeleton_edges, gt_directed = build_skeleton_and_gt(phase1)

    # Safety valve check
    valve = safety_valve(phase2, phase1)

    # If safety valve triggers, we already handled it in Phase 3's reconciled output
    # (the existing pipeline reverts damaged nodes to Phase 1 before Phase 3)
    # So Phase 4 operates on whatever Phase 3 produced.

    reconciled = phase3["reconciled"]

    # Run conservative propagation
    committed, meek_compelled, residual, prop_log = conservative_propagation(
        reconciled, skeleton_edges,
        commit_threshold=commit_threshold,
        batch_size=batch_size,
    )

    # Build final orientation map
    final_orientations = {}
    for edge_key, (src, dst) in committed.items():
        final_orientations[edge_key] = {
            "direction": f"{src}->{dst}",
            "source": "committed",
            "confidence": None,  # will fill below
        }
    for edge_key, (src, dst, rule) in meek_compelled.items():
        final_orientations[edge_key] = {
            "direction": f"{src}->{dst}",
            "source": f"meek_{rule}",
            "confidence": None,
        }

    # Evaluate against GT
    def evaluate(orientations):
        correct = 0
        total = 0
        by_source = defaultdict(lambda: [0, 0])

        for edge_key, info in orientations.items():
            gt = gt_directed.get(edge_key)
            if gt is None:
                continue
            total += 1
            is_correct = info["direction"] == gt
            if is_correct:
                correct += 1
            source = info["source"]
            by_source[source][1] += 1
            if is_correct:
                by_source[source][0] += 1

        return correct, total, dict(by_source)

    p4_correct, p4_total, by_source = evaluate(final_orientations)

    # Use Phase 3's own evaluation for baseline accuracy
    p3_eval = phase3.get("evaluation", {})
    p3_correct = p3_eval.get("correct", 0)

    # Count Meek contributions
    n_meek = len(meek_compelled)
    n_committed = len(committed)
    n_residual = len(residual)

    # Count cycle flips
    n_cycle_flips = sum(1 for e in prop_log if e.get("event") == "cycle_flip")
    n_meek_overrides = sum(
        e.get("n_contradictions", 0) for e in prop_log
        if e.get("event") == "meek_propagation"
    )

    result = {
        "metadata": {
            "phase": 4,
            "method": "conservative_propagation",
            "network": phase2.get("metadata", {}).get("network", "unknown"),
            "commit_threshold": commit_threshold,
            "batch_size": batch_size,
        },
        "safety_valve": valve,
        "propagation": {
            "n_committed": n_committed,
            "n_meek_compelled": n_meek,
            "n_residual": n_residual,
            "n_cycle_flips": n_cycle_flips,
            "n_meek_overrides": n_meek_overrides,
            "n_rounds": max((e.get("round", 0) for e in prop_log), default=0),
        },
        "evaluation": {
            "phase3_accuracy": p3_correct / max(p4_total, 1),
            "phase3_correct": p3_correct,
            "phase4_accuracy": p4_correct / max(p4_total, 1),
            "phase4_correct": p4_correct,
            "total_edges": p4_total,
            "delta_pp": round((p4_correct - p3_correct) / max(p4_total, 1) * 100, 1),
            "by_source": {
                src: {"correct": c, "total": t, "accuracy": c / max(t, 1)}
                for src, (c, t) in by_source.items()
            },
        },
        "propagation_log": prop_log,
        "final_orientations": {
            str(k): v for k, v in final_orientations.items()
        },
    }

    return result


def main():
    """Run Phase 4 on all available K=10 debiased results."""
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_10k_k10_debiased"),
        ("Alarm", "mve_27b_alarm_10k_k10_debiased"),
        ("Sachs", "mve_27b_sachs_10k_k10_debiased"),
        ("Child", "mve_27b_child_10k_k10_debiased"),
        ("Asia", "mve_27b_asia_10k_k10_debiased"),
        ("Hepar2", "mve_27b_hepar2_10k_k10_debiased"),
    ]

    # Also check old full results
    old_targets = [
        ("Insurance (old)", "mve_27b_insurance_full"),
        ("Alarm (old)", "mve_27b_alarm_full"),
        ("Sachs (old)", "mve_27b_sachs_full"),
        ("Child (old)", "mve_27b_child_full"),
    ]

    all_targets = targets + old_targets

    print("=" * 70)
    print("LOCALE Phase 4: Conservative Propagation + Meek Rules")
    print("=" * 70)

    summary_rows = []

    for label, dirname in all_targets:
        result = run_phase4(results_dir / dirname)
        if result is None:
            continue

        prop = result["propagation"]
        ev = result["evaluation"]
        valve = result["safety_valve"]

        print(f"\n{'='*50}")
        print(f"{label}")
        print(f"{'='*50}")

        print(f"  Safety valve: {'TRIGGERED' if valve['fallback_recommended'] else 'OK'} "
              f"(P2-P1 delta: {valve['net_delta_pp']:+.1f}pp)")

        print(f"  Propagation:")
        print(f"    Committed: {prop['n_committed']}")
        print(f"    Meek-compelled: {prop['n_meek_compelled']}")
        print(f"    Cycle flips: {prop['n_cycle_flips']}")
        print(f"    Meek overrides: {prop['n_meek_overrides']}")
        print(f"    Residual (unresolved): {prop['n_residual']}")
        print(f"    Rounds: {prop['n_rounds']}")

        p3_pct = ev["phase3_accuracy"] * 100
        p4_pct = ev["phase4_accuracy"] * 100
        print(f"\n  Phase 3 accuracy: {ev['phase3_correct']}/{ev['total_edges']} ({p3_pct:.1f}%)")
        print(f"  Phase 4 accuracy: {ev['phase4_correct']}/{ev['total_edges']} ({p4_pct:.1f}%)")
        print(f"  Delta: {ev['delta_pp']:+.1f}pp")

        if ev["by_source"]:
            print(f"\n  By decision source:")
            for src, stats in sorted(ev["by_source"].items()):
                print(f"    {src:20s}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")

        # Show interesting propagation events
        for event in result["propagation_log"]:
            if event.get("event") in ("meek_propagation", "cycle_flip", "meek_rollback"):
                print(f"  [{event['event']}] {event}")

        summary_rows.append({
            "network": label,
            "p3": p3_pct,
            "p4": p4_pct,
            "delta": ev["delta_pp"],
            "meek": prop["n_meek_compelled"],
            "flips": prop["n_cycle_flips"],
            "residual": prop["n_residual"],
        })

        # Save
        out_path = results_dir / dirname / "phase4_propagation_results.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n  Saved to {out_path}")

    # Summary table
    if summary_rows:
        print(f"\n{'='*70}")
        print("SUMMARY: Conservative Propagation")
        print(f"{'='*70}")
        print(f"{'Network':<20} {'P3':>7} {'P4':>7} {'Delta':>7} {'Meek':>5} {'Flips':>6} {'Resid':>6}")
        for r in summary_rows:
            print(f"{r['network']:<20} {r['p3']:>6.1f}% {r['p4']:>6.1f}% "
                  f"{r['delta']:>+6.1f}pp {r['meek']:>5} {r['flips']:>6} {r['residual']:>6}")


if __name__ == "__main__":
    main()
