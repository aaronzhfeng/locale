"""
Multi-seed validation runner for LOCALE pipeline.

Runs Phase 1 (ego-graph LLM orientation) + Phase 2 (NCO Max-2SAT) across multiple
seeds and networks, then produces a summary table with mean ± std.

Usage:
    python run_multiseed.py --seeds 0 1 2 --networks insurance alarm sachs child asia
    python run_multiseed.py --seeds 0 --networks insurance  # single quick test
    python run_multiseed.py --phase2-only --seeds 0 1 2 --networks insurance alarm  # skip Phase 1
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


EXPERIMENTS_DIR = Path(__file__).parent
RESULTS_DIR = EXPERIMENTS_DIR / "results"

# Networks and their config
NETWORKS = ["insurance", "alarm", "sachs", "child", "asia", "hepar2", "cancer", "water", "mildew", "hailfinder", "win95pts"]


def result_dir_name(network, seed):
    """Get result directory name for a network+seed combo."""
    return f"mve_27b_{network}_10k_k10_debiased_s{seed}"


def phase1_exists(network, seed):
    """Check if Phase 1 results exist for this seed."""
    d = RESULTS_DIR / result_dir_name(network, seed)
    return (d / "mve_results.json").exists()


def phase2_exists(network, seed):
    """Check if Phase 2 results exist for this seed."""
    d = RESULTS_DIR / result_dir_name(network, seed)
    return (d / "phase2_results.json").exists()


def phase3_exists(network, seed):
    """Check if Phase 3 results exist for this seed."""
    d = RESULTS_DIR / result_dir_name(network, seed)
    return (d / "phase3_results.json").exists()


def run_phase1(network, seed, alpha=None):
    """Run Phase 1 for a single network+seed."""
    out_dir = RESULTS_DIR / result_dir_name(network, seed)
    cmd = [
        sys.executable, str(EXPERIMENTS_DIR / "mve_insurance.py"),
        "--network", network,
        "--n-samples", "10000",
        "--k-passes", "10",
        "--debiased",
        "--all-nodes",
        "--no-think",
        "--seed", str(seed),
        "--output-dir", str(out_dir),
    ]
    if alpha is not None:
        cmd.extend(["--alpha", str(alpha)])
    print(f"\n{'='*60}")
    print(f"Phase 1: {network} seed={seed}")
    print(f"{'='*60}")
    print(f"  Command: {' '.join(cmd)}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=False, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode}) after {elapsed:.0f}s")
        return False

    print(f"  Completed in {elapsed:.0f}s")
    return True


def run_phase2(network, seed):
    """Run Phase 2 (NCO) on existing Phase 1 results."""
    out_dir = RESULTS_DIR / result_dir_name(network, seed)
    p1_path = out_dir / "mve_results.json"

    if not p1_path.exists():
        print(f"  Phase 1 not found for {network} seed={seed}, skipping Phase 2")
        return False

    # Import phase2 module
    sys.path.insert(0, str(EXPERIMENTS_DIR))
    from phase2_max2sat import run_phase2 as _run_p2

    print(f"\n  Phase 2 (NCO): {network} seed={seed}...")
    start = time.time()
    p2_results = _run_p2(str(p1_path), collider_mode="non-collider-only")
    elapsed = time.time() - start

    # Save
    p2_path = out_dir / "phase2_results.json"
    with open(p2_path, "w") as f:
        json.dump(p2_results, f, indent=2, default=str)

    acc = p2_results["summary"]["phase2_accuracy"]
    print(f"  Phase 2 accuracy: {acc:.1f}% ({elapsed:.1f}s)")
    return True


def run_phase3(network, seed):
    """Run Phase 3 (confidence-weighted reconciliation) on Phase 2 results."""
    out_dir = RESULTS_DIR / result_dir_name(network, seed)

    sys.path.insert(0, str(EXPERIMENTS_DIR))
    from phase3_reconcile import run_phase3 as _run_p3

    print(f"  Phase 3 (reconciliation): {network} seed={seed}...")
    start = time.time()
    p3_results = _run_p3(str(out_dir))
    elapsed = time.time() - start

    if p3_results is None:
        print(f"  Phase 3 FAILED for {network} seed={seed}")
        return False

    # Save
    p3_path = out_dir / "phase3_results.json"
    with open(p3_path, "w") as f:
        json.dump(p3_results, f, indent=2, default=str)

    ev = p3_results["evaluation"]
    print(f"  Phase 3 accuracy: {ev['correct']}/{ev['total']} = {ev['accuracy']:.1%} ({elapsed:.1f}s)")
    return True


def compute_f1(network, seed):
    """Compute MosaCD-style directed edge F1 from Phase 3 reconciled results.

    Phase 3 = confidence-weighted reconciliation across both endpoints.
    F1 is computed against the FULL GT DAG (all edges, including those
    not in the skeleton). This means recall is penalized by skeleton coverage.
    """
    import pgmpy.utils

    out_dir = RESULTS_DIR / result_dir_name(network, seed)
    p3_path = out_dir / "phase3_results.json"

    if not p3_path.exists():
        return None

    with open(p3_path) as f:
        p3 = json.load(f)

    # Get FULL ground truth DAG from pgmpy
    model = pgmpy.utils.get_example_model(network)
    gt_edges = set(model.edges())

    ev = p3["evaluation"]
    tp = ev["correct"]
    total = ev["total"]
    fp = total - tp
    fn = len(gt_edges) - tp
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-10)

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "accuracy": ev["accuracy"] * 100,
        "n_gt_edges": len(gt_edges),
        "n_oriented": total,
    }


def load_seed42_results():
    """Load existing seed=42 results from the original result dirs."""
    results = {}
    for network in NETWORKS:
        # The original results are in mve_27b_{network}_10k_k10_debiased (no _s42 suffix)
        orig_dir = RESULTS_DIR / f"mve_27b_{network}_10k_k10_debiased"
        p2_path = orig_dir / "phase2_results.json"
        p1_path = orig_dir / "mve_results.json"

        if not p2_path.exists() or not p1_path.exists():
            continue

        # Compute F1 from original
        with open(p2_path) as f:
            p2 = json.load(f)
        with open(p1_path) as f:
            p1 = json.load(f)

        gt_edges = set()
        per_node = p1.get("per_node", {})
        for node, info in per_node.items():
            for e in info.get("gt_edges", []):
                gt_edges.add(tuple(e))

        results[network] = {
            "accuracy": p2["summary"]["phase2_accuracy"],
            "n_gt_edges": len(gt_edges),
        }
    return results


def print_summary(all_results, seeds):
    """Print summary table with mean ± std across seeds."""
    print(f"\n{'='*80}")
    print(f"Multi-Seed Summary (seeds: {seeds})")
    print(f"{'='*80}")

    header = f"{'Network':<12} {'Seeds':>6} {'Acc (mean±std)':>18} {'F1 (mean±std)':>18} {'P':>8} {'R':>8}"
    print(header)
    print("-" * 80)

    for network in NETWORKS:
        if network not in all_results:
            continue

        net_results = all_results[network]
        accs = [r["accuracy"] for r in net_results.values() if r is not None]
        f1s = [r["f1"] for r in net_results.values() if r is not None]
        ps = [r["precision"] for r in net_results.values() if r is not None]
        rs = [r["recall"] for r in net_results.values() if r is not None]

        if not accs:
            continue

        n = len(accs)
        acc_mean, acc_std = np.mean(accs), np.std(accs)
        f1_mean, f1_std = np.mean(f1s), np.std(f1s)
        p_mean = np.mean(ps)
        r_mean = np.mean(rs)

        print(f"{network:<12} {n:>6} {acc_mean:>8.1f}±{acc_std:>5.1f}%   {f1_mean:>7.3f}±{f1_std:>5.3f}  {p_mean:>7.3f} {r_mean:>7.3f}")

    print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Multi-seed LOCALE validation")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2],
                       help="Seeds to run (default: 0 1 2)")
    parser.add_argument("--networks", nargs="+", default=["insurance", "alarm", "sachs", "child", "asia"],
                       choices=NETWORKS, help="Networks to test")
    parser.add_argument("--phase2-only", action="store_true",
                       help="Skip Phase 1 (assume results exist)")
    parser.add_argument("--summary-only", action="store_true",
                       help="Only print summary from existing results")
    parser.add_argument("--include-seed42", action="store_true",
                       help="Include original seed=42 results in summary")
    parser.add_argument("--alpha", type=float, default=None,
                       help="PC skeleton alpha (default: use script default 0.05)")
    args = parser.parse_args()

    all_results = {}  # {network: {seed: metrics_dict}}

    if not args.summary_only:
        for network in args.networks:
            for seed in args.seeds:
                # Phase 1
                if not args.phase2_only:
                    if phase1_exists(network, seed):
                        print(f"Phase 1 exists for {network} seed={seed}, skipping")
                    else:
                        success = run_phase1(network, seed, alpha=args.alpha)
                        if not success:
                            print(f"Phase 1 FAILED for {network} seed={seed}")
                            continue

                # Phase 2
                if not phase2_exists(network, seed):
                    run_phase2(network, seed)

                # Phase 3
                if not phase3_exists(network, seed):
                    run_phase3(network, seed)

    # Collect results
    for network in args.networks:
        all_results[network] = {}
        for seed in args.seeds:
            metrics = compute_f1(network, seed)
            if metrics:
                all_results[network][seed] = metrics

        # Optionally include seed=42
        if args.include_seed42:
            # Check original dir
            orig_dir = RESULTS_DIR / f"mve_27b_{network}_10k_k10_debiased"
            if (orig_dir / "phase2_results.json").exists():
                # Symlink or copy to s42 dir for uniform access
                s42_dir = RESULTS_DIR / result_dir_name(network, 42)
                if not s42_dir.exists():
                    s42_dir.symlink_to(orig_dir.resolve())
                metrics = compute_f1(network, 42)
                if metrics:
                    all_results[network][42] = metrics

    # Print per-seed detail
    print(f"\n{'='*80}")
    print("Per-Seed Results")
    print(f"{'='*80}")
    for network in args.networks:
        if network not in all_results:
            continue
        print(f"\n  {network.upper()}:")
        for seed in sorted(all_results[network].keys()):
            m = all_results[network][seed]
            if m:
                print(f"    seed={seed:>2}: Acc={m['accuracy']:>5.1f}%  F1={m['f1']:.3f}  P={m['precision']:.3f}  R={m['recall']:.3f}  ({m['tp']}/{m['n_gt_edges']} GT)")

    # Print summary
    effective_seeds = args.seeds + ([42] if args.include_seed42 else [])
    print_summary(all_results, effective_seeds)

    # Save JSON
    out_path = RESULTS_DIR / "multiseed_summary.json"
    serializable = {}
    for net, seeds_dict in all_results.items():
        serializable[net] = {str(s): v for s, v in seeds_dict.items()}
    with open(out_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
