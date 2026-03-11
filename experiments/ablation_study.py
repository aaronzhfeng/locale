"""
Ablation Study: Contribution of each pipeline phase

Systematically evaluates the contribution of each pipeline component
by running all possible phase combinations.

Configurations:
1. PE majority vote (Phase 1 only, per-edge)
2. Ego majority vote (Phase 1 only, ego-graph)
3. PE + Phase 2 constraints
4. Ego + Phase 2 constraints
5. Ego + Phase 2 + Phase 3 reconciliation
6. Ego + Phase 2 + Phase 3 + Phase 4 (safety valve)
7. PE + Phase 2 + Phase 3 reconciliation (PE variant)

Also computes:
- Per-degree analysis (does ego help more at higher degree?)
- Cost analysis (query count savings)
"""

import json
from pathlib import Path
from collections import defaultdict

from phase2_max2sat import run_phase2, votes_to_soft_scores


def compute_per_degree(results_path):
    """Compute accuracy broken down by node degree."""
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})
    raw_pe = data.get("raw_results_a", [])
    raw_ego = data.get("raw_results_b", [])

    degree_bins = defaultdict(lambda: {
        "pe_correct": 0, "ego_correct": 0, "total": 0, "n_nodes": 0
    })

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

        bin_key = f"d={d}" if d <= 5 else "d>=6"
        degree_bins[bin_key]["n_nodes"] += 1

        for nbr in neighbors:
            if nbr not in gt_map:
                continue
            gt = gt_map[nbr]
            degree_bins[bin_key]["total"] += 1

            # PE majority
            pe_toward = sum(1 for r in raw_pe
                          if r["center_node"] == node and set(r["edge"]) == {node, nbr}
                          and r["predicted"] == f"{nbr}->{node}")
            pe_away = sum(1 for r in raw_pe
                        if r["center_node"] == node and set(r["edge"]) == {node, nbr}
                        and r["predicted"] == f"{node}->{nbr}")
            pe_dir = f"{nbr}->{node}" if pe_toward > pe_away else f"{node}->{nbr}"
            if pe_dir == gt:
                degree_bins[bin_key]["pe_correct"] += 1

            # Ego majority
            ego_toward = sum(1 for r in raw_ego
                           if r["center_node"] == node and set(r["edge"]) == {node, nbr}
                           and r["predicted"] == f"{nbr}->{node}")
            ego_away = sum(1 for r in raw_ego
                          if r["center_node"] == node and set(r["edge"]) == {node, nbr}
                          and r["predicted"] == f"{node}->{nbr}")
            ego_dir = f"{nbr}->{node}" if ego_toward > ego_away else f"{node}->{nbr}"
            if ego_dir == gt:
                degree_bins[bin_key]["ego_correct"] += 1

    return dict(degree_bins)


def compute_bootstrap_ci(raw_results, per_node, n_bootstrap=1000, seed=42):
    """Compute bootstrap confidence intervals for majority vote accuracy.

    Uses K=5 votes per edge. Bootstrap resamples the K votes and recomputes
    majority vote for each edge, then computes accuracy.
    """
    import random
    rng = random.Random(seed)

    # Group votes by (center_node, edge)
    vote_groups = defaultdict(list)
    for r in raw_results:
        key = (r["center_node"], tuple(sorted(r["edge"])))
        vote_groups[key].append(r["predicted"])

    # Build GT map
    gt_map = {}
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            edge_key = tuple(sorted(e))
            gt_map[(node, edge_key)] = f"{e[0]}->{e[1]}"

    # Bootstrap
    boot_accs = []
    for _ in range(n_bootstrap):
        correct = 0
        total = 0
        for key, votes in vote_groups.items():
            if key not in gt_map:
                continue
            # Resample with replacement
            boot_votes = [rng.choice(votes) for _ in range(len(votes))]
            # Majority vote
            from collections import Counter
            counts = Counter(boot_votes)
            majority = counts.most_common(1)[0][0]
            if majority == gt_map[key]:
                correct += 1
            total += 1
        if total > 0:
            boot_accs.append(correct / total)

    if not boot_accs:
        return None, None, None

    boot_accs.sort()
    mean_acc = sum(boot_accs) / len(boot_accs)
    ci_low = boot_accs[int(0.025 * len(boot_accs))]
    ci_high = boot_accs[int(0.975 * len(boot_accs))]
    return mean_acc, ci_low, ci_high


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

    print("=" * 90)
    print("LOCALE Ablation Study")
    print("=" * 90)

    # ── 1. Pipeline Ablation ──
    print("\n1. PIPELINE ABLATION (accuracy by phase)")
    print("-" * 90)

    all_configs = []

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        with open(p1_path) as f:
            data = json.load(f)

        per_node = data.get("per_node", {})
        raw_pe = data.get("raw_results_a", [])
        raw_ego = data.get("raw_results_b", [])

        # PE baseline
        pe_correct = 0
        ego_correct = 0
        total = 0
        for node, info in per_node.items():
            gt_edges = info.get("gt_edges", [])
            gt_map = {}
            for e in gt_edges:
                u, v = e
                gt_map[v if u == node else u] = f"{u}->{v}"

            neighbors = info.get("neighbors", [])
            for nbr in neighbors:
                if nbr not in gt_map:
                    continue
                total += 1
                gt = gt_map[nbr]

                s = votes_to_soft_scores(raw_pe, node, [nbr])
                pe_dir = f"{nbr}->{node}" if s.get(nbr, (0.5, 0.5))[0] > s.get(nbr, (0.5, 0.5))[1] else f"{node}->{nbr}"
                if pe_dir == gt:
                    pe_correct += 1

                s = votes_to_soft_scores(raw_ego, node, [nbr])
                ego_dir = f"{nbr}->{node}" if s.get(nbr, (0.5, 0.5))[0] > s.get(nbr, (0.5, 0.5))[1] else f"{node}->{nbr}"
                if ego_dir == gt:
                    ego_correct += 1

        # Phase 2
        p2_ego = run_phase2(str(p1_path), use_pe=False)
        p2_pe = run_phase2(str(p1_path), use_pe=True)

        # Phase 3 & 4
        p3_path = results_dir / dirname / "phase3_results.json"
        p4_path = results_dir / dirname / "phase4_results.json"

        p3_acc = None
        if p3_path.exists():
            with open(p3_path) as f:
                p3 = json.load(f)
            p3_acc = p3["evaluation"]["accuracy"] * 100

        p4_acc = None
        if p4_path.exists():
            with open(p4_path) as f:
                p4 = json.load(f)
            p4_acc = p4["evaluation"].get("best_accuracy",
                       p4["evaluation"]["phase4_accuracy"]) * 100

        config = {
            "network": label,
            "n_edges": total,
            "pe_base": pe_correct / max(total, 1) * 100,
            "ego_base": ego_correct / max(total, 1) * 100,
            "pe_p2": p2_pe["summary"]["phase2_accuracy"],
            "ego_p2": p2_ego["summary"]["phase2_accuracy"],
            "p3": p3_acc,
            "p4": p4_acc,
        }
        all_configs.append(config)

    # Print table
    print(f"{'Network':<12} {'N':>4} {'PE':>7} {'Ego':>7} {'PE+P2':>7} {'Ego+P2':>7} {'P3':>7} {'P4':>7}")
    print("-" * 70)
    for c in all_configs:
        p3_str = f"{c['p3']:.1f}%" if c['p3'] else "—"
        p4_str = f"{c['p4']:.1f}%" if c['p4'] else "—"
        print(f"{c['network']:<12} {c['n_edges']:>4} {c['pe_base']:>6.1f}% {c['ego_base']:>6.1f}% "
              f"{c['pe_p2']:>6.1f}% {c['ego_p2']:>6.1f}% {p3_str:>7} {p4_str:>7}")

    # Aggregate
    n_total = sum(c["n_edges"] for c in all_configs)
    agg = {
        "pe": sum(c["pe_base"] * c["n_edges"] for c in all_configs) / n_total,
        "ego": sum(c["ego_base"] * c["n_edges"] for c in all_configs) / n_total,
        "pe_p2": sum(c["pe_p2"] * c["n_edges"] for c in all_configs) / n_total,
        "ego_p2": sum(c["ego_p2"] * c["n_edges"] for c in all_configs) / n_total,
        "p3": sum(c["p3"] * c["n_edges"] for c in all_configs if c["p3"]) / n_total,
        "p4": sum(c["p4"] * c["n_edges"] for c in all_configs if c["p4"]) / n_total,
    }
    print("-" * 70)
    print(f"{'Aggregate':<12} {n_total:>4} {agg['pe']:>6.1f}% {agg['ego']:>6.1f}% "
          f"{agg['pe_p2']:>6.1f}% {agg['ego_p2']:>6.1f}% {agg['p3']:>6.1f}% {agg['p4']:>6.1f}%")

    # Phase contribution
    print("\n  Phase contributions (aggregate):")
    print(f"    PE baseline:              {agg['pe']:.1f}%")
    print(f"    Ego (Phase 1 swap):       {agg['ego']:.1f}% ({agg['ego']-agg['pe']:+.1f}pp)")
    print(f"    + Phase 2 constraints:    {agg['ego_p2']:.1f}% ({agg['ego_p2']-agg['ego']:+.1f}pp)")
    print(f"    + Phase 3 reconciliation: {agg['p3']:.1f}% ({agg['p3']-agg['ego_p2']:+.1f}pp)")
    print(f"    + Phase 4 safety valve:   {agg['p4']:.1f}% ({agg['p4']-agg['p3']:+.1f}pp)")
    print(f"    Total improvement:        {agg['p4']-agg['pe']:+.1f}pp")

    # ── 2. Per-Degree Analysis ──
    print(f"\n\n2. PER-DEGREE ANALYSIS (ego vs PE by node degree)")
    print("-" * 70)

    all_degree = defaultdict(lambda: {"pe_correct": 0, "ego_correct": 0, "total": 0, "n_nodes": 0})

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        degree_data = compute_per_degree(str(p1_path))

        print(f"\n  {label}:")
        for dkey in sorted(degree_data.keys()):
            d = degree_data[dkey]
            pe_a = d["pe_correct"] / max(d["total"], 1) * 100
            ego_a = d["ego_correct"] / max(d["total"], 1) * 100
            delta = ego_a - pe_a
            print(f"    {dkey:>6}: PE {pe_a:5.1f}%  Ego {ego_a:5.1f}%  Delta {delta:+5.1f}pp  (N={d['total']}, {d['n_nodes']} nodes)")
            all_degree[dkey]["pe_correct"] += d["pe_correct"]
            all_degree[dkey]["ego_correct"] += d["ego_correct"]
            all_degree[dkey]["total"] += d["total"]
            all_degree[dkey]["n_nodes"] += d["n_nodes"]

    print(f"\n  Aggregate across networks:")
    for dkey in sorted(all_degree.keys()):
        d = all_degree[dkey]
        pe_a = d["pe_correct"] / max(d["total"], 1) * 100
        ego_a = d["ego_correct"] / max(d["total"], 1) * 100
        delta = ego_a - pe_a
        print(f"    {dkey:>6}: PE {pe_a:5.1f}%  Ego {ego_a:5.1f}%  Delta {delta:+5.1f}pp  (N={d['total']}, {d['n_nodes']} nodes)")

    # ── 3. Bootstrap Confidence Intervals ──
    print(f"\n\n3. BOOTSTRAP CONFIDENCE INTERVALS (from K=5 votes)")
    print("-" * 70)

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        with open(p1_path) as f:
            data = json.load(f)

        per_node = data.get("per_node", {})

        pe_mean, pe_lo, pe_hi = compute_bootstrap_ci(
            data.get("raw_results_a", []), per_node)
        ego_mean, ego_lo, ego_hi = compute_bootstrap_ci(
            data.get("raw_results_b", []), per_node)

        if pe_mean is not None:
            print(f"  {label:<12} PE:  {pe_mean*100:5.1f}% [{pe_lo*100:.1f}%, {pe_hi*100:.1f}%]  "
                  f"Ego: {ego_mean*100:5.1f}% [{ego_lo*100:.1f}%, {ego_hi*100:.1f}%]")

    # ── 4. Query Cost Analysis ──
    print(f"\n\n4. QUERY COST ANALYSIS")
    print("-" * 70)

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        with open(p1_path) as f:
            data = json.load(f)

        per_node = data.get("per_node", {})
        K = 5  # votes per edge

        n_centers = len(per_node)
        total_edges_from_centers = sum(info.get("degree", 0) for info in per_node.values())

        ego_queries = n_centers * K
        pe_queries = total_edges_from_centers * K
        ratio = pe_queries / max(ego_queries, 1)

        print(f"  {label:<12} Centers: {n_centers:>3}  "
              f"Ego queries: {ego_queries:>5}  PE queries: {pe_queries:>5}  "
              f"Ratio: {ratio:.1f}x  Savings: {(1-1/ratio)*100:.0f}%")

    # ── 5. CI Violation Analysis ──
    print(f"\n\n5. CI CONSTRAINT VIOLATION ANALYSIS")
    print("-" * 70)

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        with open(p1_path) as f:
            data = json.load(f)

        # Count CI violations from raw results
        pe_violations = sum(1 for r in data.get("raw_results_a", [])
                           if r.get("ci_violation", False))
        ego_violations = sum(1 for r in data.get("raw_results_b", [])
                            if r.get("ci_violation", False))
        pe_total = len(data.get("raw_results_a", []))
        ego_total = len(data.get("raw_results_b", []))

        pe_rate = pe_violations / max(pe_total, 1) * 100
        ego_rate = ego_violations / max(ego_total, 1) * 100

        print(f"  {label:<12} PE: {pe_violations}/{pe_total} ({pe_rate:.1f}%)  "
              f"Ego: {ego_violations}/{ego_total} ({ego_rate:.1f}%)")


if __name__ == "__main__":
    main()
