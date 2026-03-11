"""
Hybrid Strategy Analysis

Test degree-aware hybrid: use PE for d=3 nodes, ego for all others.
Motivated by ablation finding that ego loses at d=3 (-7.2pp aggregate)
but wins at all other degree levels.
"""

import json
from pathlib import Path
from collections import defaultdict

from phase2_max2sat import votes_to_soft_scores


def compute_hybrid(results_path, pe_degrees={3}):
    """Compute hybrid accuracy: PE for specified degrees, ego for rest.

    Args:
        results_path: path to Phase 1 results
        pe_degrees: set of degrees where PE should be used instead of ego
    """
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})
    raw_pe = data.get("raw_results_a", [])
    raw_ego = data.get("raw_results_b", [])

    pe_correct = 0
    ego_correct = 0
    hybrid_correct = 0
    total = 0

    per_degree = defaultdict(lambda: {"pe": 0, "ego": 0, "hybrid": 0, "total": 0})

    for node, info in per_node.items():
        d = info.get("degree", 0)
        if d < 2:
            continue

        gt_edges = info.get("gt_edges", [])
        gt_map = {}
        for e in gt_edges:
            u, v = e
            gt_map[v if u == node else u] = f"{u}->{v}"

        neighbors = info.get("neighbors", [])
        use_pe = d in pe_degrees

        for nbr in neighbors:
            if nbr not in gt_map:
                continue
            total += 1
            gt = gt_map[nbr]

            # PE
            s_pe = votes_to_soft_scores(raw_pe, node, [nbr])
            t, a = s_pe.get(nbr, (0.5, 0.5))
            pe_dir = f"{nbr}->{node}" if t > a else f"{node}->{nbr}"
            pe_ok = pe_dir == gt
            if pe_ok:
                pe_correct += 1

            # Ego
            s_ego = votes_to_soft_scores(raw_ego, node, [nbr])
            t, a = s_ego.get(nbr, (0.5, 0.5))
            ego_dir = f"{nbr}->{node}" if t > a else f"{node}->{nbr}"
            ego_ok = ego_dir == gt
            if ego_ok:
                ego_correct += 1

            # Hybrid
            hybrid_dir = pe_dir if use_pe else ego_dir
            hybrid_ok = hybrid_dir == gt
            if hybrid_ok:
                hybrid_correct += 1

            dkey = f"d={d}" if d <= 5 else "d>=6"
            per_degree[dkey]["pe"] += int(pe_ok)
            per_degree[dkey]["ego"] += int(ego_ok)
            per_degree[dkey]["hybrid"] += int(hybrid_ok)
            per_degree[dkey]["total"] += 1

    return {
        "pe": pe_correct / max(total, 1) * 100,
        "ego": ego_correct / max(total, 1) * 100,
        "hybrid": hybrid_correct / max(total, 1) * 100,
        "total": total,
        "per_degree": dict(per_degree),
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
    print("HYBRID STRATEGY: PE for d=3, Ego for d!=3")
    print("=" * 80)

    # Test various hybrid configurations
    configs = [
        ("PE for d=3", {3}),
        ("PE for d=2,3", {2, 3}),
        ("PE for d<=3", {2, 3}),
        ("PE for d=3,4", {3, 4}),
        ("Ego only (no hybrid)", set()),
        ("PE only", {2, 3, 4, 5, 6, 7, 8, 9, 10}),
    ]

    for config_name, pe_degrees in configs:
        print(f"\n{'='*60}")
        print(f"Config: {config_name}")
        print(f"{'='*60}")

        all_results = []
        for label, dirname in targets:
            p1_path = results_dir / dirname / "mve_results.json"
            if not p1_path.exists():
                continue

            r = compute_hybrid(str(p1_path), pe_degrees)
            r["network"] = label
            all_results.append(r)

            print(f"  {label:<12} PE: {r['pe']:.1f}%  Ego: {r['ego']:.1f}%  Hybrid: {r['hybrid']:.1f}%  "
                  f"(N={r['total']})")

        # Aggregate
        n = sum(r["total"] for r in all_results)
        agg_pe = sum(r["pe"] * r["total"] for r in all_results) / n
        agg_ego = sum(r["ego"] * r["total"] for r in all_results) / n
        agg_hybrid = sum(r["hybrid"] * r["total"] for r in all_results) / n
        print(f"  {'Aggregate':<12} PE: {agg_pe:.1f}%  Ego: {agg_ego:.1f}%  Hybrid: {agg_hybrid:.1f}%  "
              f"({agg_hybrid-agg_pe:+.1f}pp vs PE, {agg_hybrid-agg_ego:+.1f}pp vs Ego)")


if __name__ == "__main__":
    main()
