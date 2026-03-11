"""
End-to-end comparison: Hard vs NCO (non-collider-only) through all phases.

Saves NCO Phase 2 results to disk, then runs Phase 3 and Phase 4 on them.
"""

import json
import shutil
from pathlib import Path

from phase2_max2sat import run_phase2
from phase3_reconcile import run_phase3
from phase4_global import run_phase4


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
    print("FULL PIPELINE: Hard vs NCO (Non-Collider-Only)")
    print("=" * 90)

    all_results = []

    for label, dirname in targets:
        result_dir = results_dir / dirname
        p1_path = result_dir / "mve_results.json"
        if not p1_path.exists():
            continue

        # --- NCO Pipeline ---
        # 1. Run NCO Phase 2 and save
        p2_nco = run_phase2(str(p1_path), use_pe=False, collider_mode="non-collider-only")
        nco_p2_path = result_dir / "phase2_results_nco.json"
        with open(nco_p2_path, "w") as f:
            json.dump(p2_nco, f, indent=2)

        # 2. Temporarily swap phase2_results.json to run Phase 3 on NCO
        orig_p2_path = result_dir / "phase2_results.json"
        backup_p2_path = result_dir / "phase2_results_hard.json"

        # Backup original
        if orig_p2_path.exists():
            shutil.copy2(orig_p2_path, backup_p2_path)

        # Swap in NCO
        shutil.copy2(nco_p2_path, orig_p2_path)

        # Run Phase 3 on NCO
        p3_nco = run_phase3(str(result_dir))
        p3_nco_acc = p3_nco["evaluation"]["accuracy"] * 100 if p3_nco else None

        # Save NCO Phase 3
        if p3_nco:
            with open(result_dir / "phase3_results_nco.json", "w") as f:
                json.dump(p3_nco, f, indent=2)
            # Swap Phase 3 results for Phase 4
            orig_p3_path = result_dir / "phase3_results.json"
            backup_p3_path = result_dir / "phase3_results_hard.json"
            if orig_p3_path.exists():
                shutil.copy2(orig_p3_path, backup_p3_path)
            shutil.copy2(result_dir / "phase3_results_nco.json", orig_p3_path)

        # Run Phase 4 on NCO
        p4_nco = run_phase4(str(result_dir))
        p4_nco_acc = None
        if p4_nco:
            ev = p4_nco["evaluation"]
            p4_nco_acc = ev.get("best_accuracy", ev["phase4_accuracy"]) * 100
            with open(result_dir / "phase4_results_nco.json", "w") as f:
                json.dump(p4_nco, f, indent=2)

        # Restore originals
        if backup_p2_path.exists():
            shutil.copy2(backup_p2_path, orig_p2_path)
        if (result_dir / "phase3_results_hard.json").exists():
            shutil.copy2(result_dir / "phase3_results_hard.json",
                        result_dir / "phase3_results.json")

        # --- Hard Pipeline (read from saved files) ---
        p4_hard_path = result_dir / "phase4_results.json"
        p4_hard_acc = None
        if backup_p2_path.exists():
            # Re-read original Phase 4 results
            orig_p4_path = result_dir / "phase4_results.json"
            # We already ran Phase 4 on NCO, which overwrote the file
            # Read from the backup we might have, or from stored results
            pass

        # Just re-read stored hard results
        p2_hard = run_phase2(str(p1_path), use_pe=False, collider_mode="hard")
        p2_pe = run_phase2(str(p1_path), use_pe=True, collider_mode="hard")

        # Read original Phase 4 hard results
        if (result_dir / "phase4_results.json").exists():
            with open(result_dir / "phase4_results.json") as f:
                p4_data = json.load(f)
            ev = p4_data["evaluation"]
            p4_hard_acc = ev.get("best_accuracy", ev["phase4_accuracy"]) * 100
        else:
            p4_hard_acc = None

        row = {
            "network": label,
            "n": p2_hard["summary"]["total_edges"],
            "pe": p2_pe["summary"]["phase1_accuracy"],
            "ego": p2_hard["summary"]["phase1_accuracy"],
            "p2_hard": p2_hard["summary"]["phase2_accuracy"],
            "p2_nco": p2_nco["summary"]["phase2_accuracy"],
            "p3_nco": p3_nco_acc,
            "p4_hard": p4_hard_acc,
            "p4_nco": p4_nco_acc,
        }
        all_results.append(row)

    # Print table
    print(f"\n{'Network':<12} {'N':>4} {'PE':>7} {'Ego':>7} "
          f"{'P2hard':>8} {'P2nco':>8} {'P3nco':>8} {'P4hard':>8} {'P4nco':>8}")
    print("-" * 90)

    totals = {k: 0 for k in ["n", "pe", "ego", "p2_hard", "p2_nco", "p3_nco", "p4_hard", "p4_nco"]}

    for r in all_results:
        n = r["n"]
        p3_str = f"{r['p3_nco']:.1f}%" if r['p3_nco'] else "—"
        p4h_str = f"{r['p4_hard']:.1f}%" if r['p4_hard'] else "—"
        p4n_str = f"{r['p4_nco']:.1f}%" if r['p4_nco'] else "—"

        print(f"{r['network']:<12} {n:>4} {r['pe']:>6.1f}% {r['ego']:>6.1f}% "
              f"{r['p2_hard']:>7.1f}% {r['p2_nco']:>7.1f}% {p3_str:>8} {p4h_str:>8} {p4n_str:>8}")

        totals["n"] += n
        totals["pe"] += r["pe"] * n / 100
        totals["ego"] += r["ego"] * n / 100
        totals["p2_hard"] += r["p2_hard"] * n / 100
        totals["p2_nco"] += r["p2_nco"] * n / 100
        if r["p3_nco"]:
            totals["p3_nco"] += r["p3_nco"] * n / 100
        if r["p4_hard"]:
            totals["p4_hard"] += r["p4_hard"] * n / 100
        if r["p4_nco"]:
            totals["p4_nco"] += r["p4_nco"] * n / 100

    n = totals["n"]
    print("-" * 90)
    print(f"{'Aggregate':<12} {n:>4} "
          f"{totals['pe']/n*100:>6.1f}% {totals['ego']/n*100:>6.1f}% "
          f"{totals['p2_hard']/n*100:>7.1f}% {totals['p2_nco']/n*100:>7.1f}% "
          f"{totals['p3_nco']/n*100:>7.1f}% "
          f"{totals['p4_hard']/n*100:>7.1f}% {totals['p4_nco']/n*100:>7.1f}%")

    pe_agg = totals["pe"] / n * 100
    nco_p4 = totals["p4_nco"] / n * 100
    hard_p4 = totals["p4_hard"] / n * 100
    print(f"\n  NCO Pipeline (P4): {nco_p4:.1f}% ({nco_p4-pe_agg:+.1f}pp vs PE)")
    print(f"  Hard Pipeline (P4): {hard_p4:.1f}% ({hard_p4-pe_agg:+.1f}pp vs PE)")
    print(f"  NCO advantage: {nco_p4-hard_p4:+.1f}pp")


if __name__ == "__main__":
    main()
