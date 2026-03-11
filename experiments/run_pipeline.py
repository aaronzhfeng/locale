"""
Full LOCALE Pipeline Runner + Comparison

Runs all pipeline configurations on all networks and produces a comparison table.
No LLM queries — pure post-processing on existing Phase 1 results.

Configurations:
- PE baseline: per-edge majority vote
- Ego baseline: ego-graph majority vote
- PE + Phase 2: per-edge votes + Max-2SAT constraints
- Ego + Phase 2: ego votes + Max-2SAT constraints
- Ego + Phase 2 + Phase 3: + dual-endpoint reconciliation
- Ego + Phase 2 + Phase 3 + Phase 4 (safety valve): + acyclicity + safety valve
"""

import json
from pathlib import Path

from phase2_max2sat import run_phase2
from phase3_reconcile import reconcile_edges, evaluate_reconciled, run_phase3
from phase4_global import run_phase4, safety_valve


def get_baselines(results_path):
    """Extract PE and Ego majority-vote baselines from Phase 1 results."""
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})

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

            # PE majority
            pe_toward = 0
            pe_away = 0
            for r in data.get("raw_results_a", []):
                if r["center_node"] != node:
                    continue
                if set(r["edge"]) != {node, nbr}:
                    continue
                if r["predicted"] == f"{nbr}->{node}":
                    pe_toward += 1
                elif r["predicted"] == f"{node}->{nbr}":
                    pe_away += 1
            pe_dir = f"{nbr}->{node}" if pe_toward > pe_away else f"{node}->{nbr}"
            if pe_dir == gt:
                pe_correct += 1

            # Ego majority
            ego_toward = 0
            ego_away = 0
            for r in data.get("raw_results_b", []):
                if r["center_node"] != node:
                    continue
                if set(r["edge"]) != {node, nbr}:
                    continue
                if r["predicted"] == f"{nbr}->{node}":
                    ego_toward += 1
                elif r["predicted"] == f"{node}->{nbr}":
                    ego_away += 1
            ego_dir = f"{nbr}->{node}" if ego_toward > ego_away else f"{node}->{nbr}"
            if ego_dir == gt:
                ego_correct += 1

    return {
        "total": total,
        "pe_correct": pe_correct,
        "pe_accuracy": pe_correct / max(total, 1) * 100,
        "ego_correct": ego_correct,
        "ego_accuracy": ego_correct / max(total, 1) * 100,
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

    print("=" * 90)
    print("LOCALE Full Pipeline Comparison")
    print("=" * 90)

    rows = []

    for label, dirname in targets:
        result_dir = results_dir / dirname
        p1_path = result_dir / "mve_results.json"

        if not p1_path.exists():
            continue

        # Baselines
        baselines = get_baselines(str(p1_path))

        # Phase 2 (ego)
        p2_ego = run_phase2(str(p1_path), use_pe=False)
        p2_ego_acc = p2_ego["summary"]["phase2_accuracy"]

        # Phase 2 (PE)
        p2_pe = run_phase2(str(p1_path), use_pe=True)
        p2_pe_acc = p2_pe["summary"]["phase2_accuracy"]

        # Phase 3
        p3_path = result_dir / "phase3_results.json"
        p3_acc = None
        if p3_path.exists():
            with open(p3_path) as f:
                p3 = json.load(f)
            p3_acc = p3["evaluation"]["accuracy"] * 100

        # Phase 4
        p4_path = result_dir / "phase4_results.json"
        p4_acc = None
        p4_method = ""
        if p4_path.exists():
            with open(p4_path) as f:
                p4 = json.load(f)
            ev = p4["evaluation"]
            # Use the best between standard and safety-valve-corrected
            p4_acc = ev["phase4_accuracy"] * 100
            if ev.get("best_accuracy"):
                p4_acc = ev["best_accuracy"] * 100
                p4_method = ev.get("best_method", "standard")

        row = {
            "network": label,
            "n_edges": baselines["total"],
            "pe_base": baselines["pe_accuracy"],
            "ego_base": baselines["ego_accuracy"],
            "pe_p2": p2_pe_acc,
            "ego_p2": p2_ego_acc,
            "p3": p3_acc,
            "p4": p4_acc,
            "p4_method": p4_method,
        }
        rows.append(row)

    # Print comparison table
    print(f"\n{'Network':<12} {'N':>4} {'PE':>7} {'Ego':>7} {'PE+P2':>7} {'Ego+P2':>7} {'P3':>7} {'P4':>7} {'Method':>10}")
    print("-" * 90)

    totals = {"n": 0, "pe": 0, "ego": 0, "pe_p2": 0, "ego_p2": 0, "p3": 0, "p4": 0}

    for r in rows:
        p3_str = f"{r['p3']:.1f}%" if r['p3'] is not None else "—"
        p4_str = f"{r['p4']:.1f}%" if r['p4'] is not None else "—"
        print(f"{r['network']:<12} {r['n_edges']:>4} {r['pe_base']:>6.1f}% {r['ego_base']:>6.1f}% "
              f"{r['pe_p2']:>6.1f}% {r['ego_p2']:>6.1f}% {p3_str:>7} {p4_str:>7} {r['p4_method']:>10}")

        totals["n"] += r["n_edges"]
        totals["pe"] += r["pe_base"] * r["n_edges"] / 100
        totals["ego"] += r["ego_base"] * r["n_edges"] / 100
        totals["pe_p2"] += r["pe_p2"] * r["n_edges"] / 100
        totals["ego_p2"] += r["ego_p2"] * r["n_edges"] / 100
        if r["p3"] is not None:
            totals["p3"] += r["p3"] * r["n_edges"] / 100
        if r["p4"] is not None:
            totals["p4"] += r["p4"] * r["n_edges"] / 100

    print("-" * 90)
    n = totals["n"]
    print(f"{'Aggregate':<12} {n:>4} {totals['pe']/n*100:>6.1f}% {totals['ego']/n*100:>6.1f}% "
          f"{totals['pe_p2']/n*100:>6.1f}% {totals['ego_p2']/n*100:>6.1f}% "
          f"{totals['p3']/n*100:>6.1f}% {totals['p4']/n*100:>6.1f}%")

    # Query cost comparison
    print(f"\n{'='*60}")
    print("Query Cost Analysis")
    print(f"{'='*60}")
    for r in rows:
        result_path = results_dir / [t[1] for t in targets if t[0] == r["network"]][0] / "mve_results.json"
        with open(result_path) as f:
            data = json.load(f)
        n_pe = len(data.get("raw_results_a", []))
        n_ego = len(data.get("raw_results_b", []))
        ratio = n_pe / max(n_ego, 1)
        print(f"  {r['network']:<12} PE queries: {n_pe:>5}, Ego queries: {n_ego:>5}, Ratio: {ratio:.1f}x")

    # Best pipeline for each network
    print(f"\n{'='*60}")
    print("Best Pipeline per Network")
    print(f"{'='*60}")
    for r in rows:
        configs = [
            ("PE baseline", r["pe_base"]),
            ("Ego baseline", r["ego_base"]),
            ("PE + Phase 2", r["pe_p2"]),
            ("Ego + Phase 2", r["ego_p2"]),
        ]
        if r["p3"] is not None:
            configs.append(("Ego pipeline (P3)", r["p3"]))
        if r["p4"] is not None:
            configs.append(("Ego pipeline (P4)", r["p4"]))

        configs.sort(key=lambda x: -x[1])
        best = configs[0]
        pe_base = r["pe_base"]
        delta = best[1] - pe_base
        print(f"  {r['network']:<12} Best: {best[0]:25s} ({best[1]:.1f}%, {delta:+.1f}pp vs PE)")


if __name__ == "__main__":
    main()
