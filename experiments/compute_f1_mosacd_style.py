"""
Compute F1 on oriented edges (MosaCD-style) for fair comparison.

MosaCD F1 = directed edge F1 against full ground truth DAG.
- TP: edge oriented correctly (matches GT direction)
- FP: edge oriented but wrong direction, OR edge not in GT but oriented
- FN: GT edge not in output (missing from skeleton or oriented wrong)

This is different from our "accuracy on unique edges" which only counts
edges present in both skeleton and GT.
"""

import json
from pathlib import Path
from collections import defaultdict
import pgmpy.utils

from phase2_max2sat import run_phase2


def get_true_dag_edges(network_name):
    """Get all directed edges from the true Bayesian network."""
    model = pgmpy.utils.get_example_model(network_name)
    return list(model.edges())


def compute_directed_f1(results_path, network_name, collider_mode="non-collider-only"):
    """Compute MosaCD-style directed edge F1."""
    with open(results_path) as f:
        data = json.load(f)

    # Get full ground truth DAG
    true_edges = get_true_dag_edges(network_name)
    gt_directed = set()
    for u, v in true_edges:
        gt_directed.add((u, v))

    n_gt = len(gt_directed)

    per_node = data.get("per_node", {})
    raw_pe = data.get("raw_results_a", [])
    raw_ego = data.get("raw_results_b", [])

    # Build skeleton edges (all edges we tested)
    skeleton_edges = set()
    for node, info in per_node.items():
        for nbr in info.get("neighbors", []):
            skeleton_edges.add(tuple(sorted([node, nbr])))

    # --- PE baseline: majority vote per unique edge ---
    pe_votes = defaultdict(lambda: defaultdict(int))
    for r in raw_pe:
        edge_key = tuple(sorted(r["edge"]))
        if r["predicted"] and r["predicted"] != "uncertain":
            pe_votes[edge_key][r["predicted"]] += 1

    pe_output = set()
    for edge_key, votes in pe_votes.items():
        majority = max(votes, key=votes.get)
        src, tgt = majority.split("->")
        pe_output.add((src, tgt))

    # --- Ego baseline: majority vote per unique edge ---
    ego_votes = defaultdict(lambda: defaultdict(int))
    for r in raw_ego:
        edge_key = tuple(sorted(r["edge"]))
        if r["predicted"] and r["predicted"] != "uncertain":
            ego_votes[edge_key][r["predicted"]] += 1

    ego_output = set()
    for edge_key, votes in ego_votes.items():
        majority = max(votes, key=votes.get)
        src, tgt = majority.split("->")
        ego_output.add((src, tgt))

    # --- NCO P2: Phase 2 directions per unique edge ---
    p2 = run_phase2(results_path, use_pe=False, collider_mode=collider_mode)
    p2_edge_votes = defaultdict(lambda: defaultdict(float))
    for node, info in p2["per_node"].items():
        directions = info.get("directions", {})
        for nbr, direction in directions.items():
            edge_key = tuple(sorted([node, nbr]))
            p2_edge_votes[edge_key][direction] += 1

    nco_output = set()
    for edge_key, votes in p2_edge_votes.items():
        majority = max(votes, key=votes.get)
        src, tgt = majority.split("->")
        nco_output.add((src, tgt))

    # --- Compute F1 for each method ---
    results = {}
    for name, output in [("PE", pe_output), ("Ego", ego_output), ("NCO", nco_output)]:
        tp = len(output & gt_directed)
        fp = len(output - gt_directed)
        fn = len(gt_directed - output)

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        results[name] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision * 100,
            "recall": recall * 100,
            "f1": f1 * 100,
            "n_output": len(output),
            "n_gt": n_gt,
            "n_skeleton": len(skeleton_edges),
        }

    return results


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_full", "insurance"),
        ("Alarm", "mve_27b_alarm_full", "alarm"),
        ("Sachs", "mve_27b_sachs_full", "sachs"),
        ("Child", "mve_27b_child_full", "child"),
        ("Asia", "mve_27b_asia_full", "asia"),
        ("Hepar2", "mve_27b_hepar2_full", "hepar2"),
    ]

    print("=" * 100)
    print("DIRECTED EDGE F1 (MosaCD-style comparison)")
    print("=" * 100)

    # Header
    print(f"\n{'Network':<12} {'|GT|':>5} {'|Skel|':>6} {'Coverage':>9} | "
          f"{'PE F1':>7} {'PE P':>6} {'PE R':>6} | "
          f"{'Ego F1':>7} {'Ego P':>6} {'Ego R':>6} | "
          f"{'NCO F1':>7} {'NCO P':>6} {'NCO R':>6} | "
          f"{'MosaCD':>7}")
    print("-" * 120)

    mosacd_f1 = {
        "Insurance": 87, "Alarm": 93, "Child": 90,
        "Asia": 93, "Hepar2": 72, "Sachs": None,
    }

    agg = {"pe_tp": 0, "pe_fp": 0, "pe_fn": 0,
           "ego_tp": 0, "ego_fp": 0, "ego_fn": 0,
           "nco_tp": 0, "nco_fp": 0, "nco_fn": 0,
           "n_gt": 0, "n_skel": 0}

    for label, dirname, net_name in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            print(f"{label:<12} MISSING")
            continue

        r = compute_directed_f1(str(p1_path), net_name)

        pe = r["PE"]
        ego = r["Ego"]
        nco = r["NCO"]
        n_gt = pe["n_gt"]
        n_skel = pe["n_skeleton"]
        coverage = n_skel / n_gt * 100

        mcd = mosacd_f1.get(label)
        mcd_str = f"{mcd:.0f}" if mcd else "—"

        print(f"{label:<12} {n_gt:>5} {n_skel:>6} {coverage:>8.1f}% | "
              f"{pe['f1']:>6.1f}% {pe['precision']:>5.1f}% {pe['recall']:>5.1f}% | "
              f"{ego['f1']:>6.1f}% {ego['precision']:>5.1f}% {ego['recall']:>5.1f}% | "
              f"{nco['f1']:>6.1f}% {nco['precision']:>5.1f}% {nco['recall']:>5.1f}% | "
              f"{mcd_str:>7}")

        for method, prefix in [("PE", "pe"), ("Ego", "ego"), ("NCO", "nco")]:
            agg[f"{prefix}_tp"] += r[method]["tp"]
            agg[f"{prefix}_fp"] += r[method]["fp"]
            agg[f"{prefix}_fn"] += r[method]["fn"]
        agg["n_gt"] += n_gt
        agg["n_skel"] += n_skel

    # Aggregate
    print("-" * 120)
    for prefix, name in [("pe", "PE"), ("ego", "Ego"), ("nco", "NCO")]:
        tp = agg[f"{prefix}_tp"]
        fp = agg[f"{prefix}_fp"]
        fn = agg[f"{prefix}_fn"]
        p = tp / max(tp + fp, 1) * 100
        r_ = tp / max(tp + fn, 1) * 100
        f1 = 2 * p * r_ / max(p + r_, 1e-9)
        print(f"  {name} aggregate: F1={f1:.1f}% (P={p:.1f}%, R={r_:.1f}%) "
              f"[TP={tp}, FP={fp}, FN={fn}]")

    coverage = agg["n_skel"] / agg["n_gt"] * 100
    print(f"\n  Skeleton coverage: {agg['n_skel']}/{agg['n_gt']} = {coverage:.1f}%")
    print(f"\n  Note: MosaCD numbers from their Table 1 (PC skeleton, GPT-4o-mini)")
    print(f"  Our numbers use Qwen3.5-27B on the same PC skeleton approach")


if __name__ == "__main__":
    main()
