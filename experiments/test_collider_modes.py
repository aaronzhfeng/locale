"""
Test collider constraint modes on all 6 networks.

Since 100% of CI fact errors are false colliders, dropping collider
constraints should eliminate damage while keeping non-collider benefits.
"""

import json
from pathlib import Path
from phase2_max2sat import run_phase2


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

    modes = ["hard", "drop", "non-collider-only"]

    print("=" * 90)
    print("COLLIDER MODE COMPARISON")
    print("=" * 90)

    print(f"\n{'Network':<12} {'N':>4} {'P1 Ego':>8} ", end="")
    for mode in modes:
        print(f"{'P2 ' + mode:>18}", end="")
    print()
    print("-" * 80)

    agg = {mode: {"correct": 0, "total": 0} for mode in modes}
    agg["p1"] = {"correct": 0, "total": 0}

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        results = {}
        for mode in modes:
            r = run_phase2(str(p1_path), use_pe=False, collider_mode=mode)
            results[mode] = r

        s = results["hard"]["summary"]
        p1_acc = s["phase1_accuracy"]
        agg["p1"]["correct"] += s["phase1_correct"]
        agg["p1"]["total"] += s["total_edges"]

        print(f"{label:<12} {s['total_edges']:>4} {p1_acc:>7.1f}% ", end="")
        for mode in modes:
            acc = results[mode]["summary"]["phase2_accuracy"]
            delta = acc - p1_acc
            agg[mode]["correct"] += results[mode]["summary"]["phase2_correct"]
            agg[mode]["total"] += results[mode]["summary"]["total_edges"]
            print(f"{acc:>7.1f}% ({delta:+.1f})", end="")
        print()

    # Aggregate
    n = agg["p1"]["total"]
    p1_agg = agg["p1"]["correct"] / n * 100
    print("-" * 80)
    print(f"{'Aggregate':<12} {n:>4} {p1_agg:>7.1f}% ", end="")
    for mode in modes:
        acc = agg[mode]["correct"] / agg[mode]["total"] * 100
        delta = acc - p1_agg
        print(f"{acc:>7.1f}% ({delta:+.1f})", end="")
    print()

    # Hard flip comparison
    print(f"\n\n{'Network':<12} ", end="")
    for mode in modes:
        print(f"{'Flips(' + mode + ')':>18}", end="")
    print()
    print("-" * 70)

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        print(f"{label:<12} ", end="")
        for mode in modes:
            r = run_phase2(str(p1_path), use_pe=False, collider_mode=mode)
            s = r["summary"]
            print(f"  {s['hard_flips']:>2} ({s['hard_flips_helped']:>1}h/{s['hard_flips_hurt']:>1}r)", end="")
        print()


if __name__ == "__main__":
    main()
