"""
Compute accuracy on unique edges (each edge counted once).

For edges appearing in 2 ego-graphs, use the reconciled direction
(Phase 3/4 output). For baselines, use majority vote across both
ego-graph appearances.
"""

import json
from pathlib import Path
from collections import defaultdict

from phase2_max2sat import run_phase2, votes_to_soft_scores


def compute_unique_edge_accuracy(results_path, collider_mode="non-collider-only"):
    """Compute accuracy on unique edges."""
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})
    raw_pe = data.get("raw_results_a", [])
    raw_ego = data.get("raw_results_b", [])

    # Build GT map for unique edges
    gt_map = {}  # (u,v) sorted -> "u->v"
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            edge_key = tuple(sorted(e))
            gt_map[edge_key] = f"{e[0]}->{e[1]}"

    # Aggregate votes per unique edge
    pe_votes = defaultdict(lambda: defaultdict(int))   # edge_key -> direction -> count
    ego_votes = defaultdict(lambda: defaultdict(int))

    for r in raw_pe:
        edge_key = tuple(sorted(r["edge"]))
        if r["predicted"] and r["predicted"] != "uncertain":
            pe_votes[edge_key][r["predicted"]] += 1

    for r in raw_ego:
        edge_key = tuple(sorted(r["edge"]))
        if r["predicted"] and r["predicted"] != "uncertain":
            ego_votes[edge_key][r["predicted"]] += 1

    # Compute accuracy
    pe_correct = 0
    ego_correct = 0
    total = 0

    for edge_key, gt_dir in gt_map.items():
        total += 1

        # PE: majority across all votes for this edge
        if pe_votes[edge_key]:
            pe_majority = max(pe_votes[edge_key], key=pe_votes[edge_key].get)
            if pe_majority == gt_dir:
                pe_correct += 1

        # Ego: majority across all votes for this edge
        if ego_votes[edge_key]:
            ego_majority = max(ego_votes[edge_key], key=ego_votes[edge_key].get)
            if ego_majority == gt_dir:
                ego_correct += 1

    # NCO Phase 2 (unique edge accuracy)
    p2 = run_phase2(results_path, use_pe=False, collider_mode=collider_mode)
    # Collect Phase 2 directions per unique edge
    p2_directions = {}  # edge_key -> list of (direction, margin)
    p2_edge_votes = defaultdict(lambda: defaultdict(float))

    for node, info in p2["per_node"].items():
        directions = info.get("directions", {})
        for nbr, direction in directions.items():
            edge_key = tuple(sorted([node, nbr]))
            p2_edge_votes[edge_key][direction] += 1

    p2_correct = 0
    for edge_key, gt_dir in gt_map.items():
        if p2_edge_votes[edge_key]:
            p2_majority = max(p2_edge_votes[edge_key], key=p2_edge_votes[edge_key].get)
            if p2_majority == gt_dir:
                p2_correct += 1

    return {
        "total": total,
        "pe_correct": pe_correct,
        "pe_accuracy": pe_correct / max(total, 1) * 100,
        "ego_correct": ego_correct,
        "ego_accuracy": ego_correct / max(total, 1) * 100,
        "p2_correct": p2_correct,
        "p2_accuracy": p2_correct / max(total, 1) * 100,
    }


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_full"),
        ("Alarm", "mve_27b_alarm_full"),
        ("Sachs", "mve_27b_sachs_full"),
        ("Child", "mve_27b_child_full"),
        ("Asia", "mve_27b_asia_full"),
        ("Hepar2", "mve_27b_hepar2_full"),
    ]

    print("=" * 80)
    print("UNIQUE EDGE ACCURACY (each edge counted once)")
    print("=" * 80)

    print(f"\n{'Network':<12} {'Unique':>6} {'PE':>7} {'Ego':>7} {'NCO P2':>8}")
    print("-" * 50)

    totals = {"n": 0, "pe": 0, "ego": 0, "p2": 0}

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        r = compute_unique_edge_accuracy(str(p1_path))
        print(f"{label:<12} {r['total']:>6} {r['pe_accuracy']:>6.1f}% {r['ego_accuracy']:>6.1f}% "
              f"{r['p2_accuracy']:>7.1f}%")

        totals["n"] += r["total"]
        totals["pe"] += r["pe_correct"]
        totals["ego"] += r["ego_correct"]
        totals["p2"] += r["p2_correct"]

    n = totals["n"]
    print("-" * 50)
    print(f"{'Aggregate':<12} {n:>6} {totals['pe']/n*100:>6.1f}% {totals['ego']/n*100:>6.1f}% "
          f"{totals['p2']/n*100:>7.1f}%")

    print(f"\n  Note: 'per-center' metric used 338 decisions (edges counted per ego-graph)")
    print(f"  Unique edge metric uses {n} edges (each counted once)")


if __name__ == "__main__":
    main()
