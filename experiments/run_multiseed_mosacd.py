"""
Multi-seed validation runner for MosaCD baseline.

Runs MosaCD's 5-step algorithm with different data seeds, then produces
a summary table with mean ± std for fair multi-seed comparison with LOCALE.

Usage:
    python run_multiseed_mosacd.py --seeds 0 1 2 --networks insurance alarm sachs child asia
    python run_multiseed_mosacd.py --summary-only --include-seed42 --networks insurance alarm sachs child asia
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

NETWORKS = ["insurance", "alarm", "sachs", "child", "asia", "hepar2", "cancer", "water", "mildew", "hailfinder", "win95pts"]


def result_dir_name(network, seed):
    return f"mosacd_{network}_s{seed}"


def results_exist(network, seed):
    d = RESULTS_DIR / result_dir_name(network, seed)
    return (d / "mosacd_results.json").exists()


def run_mosacd(network, seed, alpha=None):
    """Run MosaCD for a single network+seed."""
    out_dir = RESULTS_DIR / result_dir_name(network, seed)
    cmd = [
        sys.executable, str(EXPERIMENTS_DIR / "mosacd_baseline.py"),
        "--network", network,
        "--n-samples", "10000",
        "--no-think",
        "--seed", str(seed),
        "--output-dir", str(out_dir),
    ]
    if alpha is not None:
        cmd.extend(["--alpha", str(alpha)])
    print(f"\n{'='*60}")
    print(f"MosaCD: {network} seed={seed}")
    print(f"{'='*60}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=False, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode}) after {elapsed:.0f}s")
        return False

    print(f"  Completed in {elapsed:.0f}s")
    return True


def compute_f1(network, seed):
    """Extract F1 from MosaCD results."""
    out_dir = RESULTS_DIR / result_dir_name(network, seed)
    path = out_dir / "mosacd_results.json"

    if not path.exists():
        return None

    with open(path) as f:
        d = json.load(f)

    metrics = d.get("metrics", {})
    if not metrics:
        return None

    return {
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "fn": metrics["fn"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "shd": metrics.get("shd", 0),
        "n_directed": metrics.get("n_directed", 0),
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-seed MosaCD validation")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--networks", nargs="+", default=["insurance", "alarm", "sachs", "child", "asia"],
                       choices=NETWORKS)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--include-seed42", action="store_true")
    parser.add_argument("--alpha", type=float, default=None,
                       help="PC skeleton alpha (default: use script default 0.05)")
    args = parser.parse_args()

    all_results = {}

    if not args.summary_only:
        for network in args.networks:
            for seed in args.seeds:
                if results_exist(network, seed):
                    print(f"MosaCD exists for {network} seed={seed}, skipping")
                else:
                    run_mosacd(network, seed, alpha=args.alpha)

    # Collect results
    for network in args.networks:
        all_results[network] = {}
        for seed in args.seeds:
            metrics = compute_f1(network, seed)
            if metrics:
                all_results[network][seed] = metrics

        if args.include_seed42:
            # Original seed=42 results are in mosacd_{network}/
            orig_dir = RESULTS_DIR / f"mosacd_{network}"
            if (orig_dir / "mosacd_results.json").exists():
                s42_dir = RESULTS_DIR / result_dir_name(network, 42)
                if not s42_dir.exists():
                    s42_dir.symlink_to(orig_dir.resolve())
                metrics = compute_f1(network, 42)
                if metrics:
                    all_results[network][42] = metrics

    # Print detail
    print(f"\n{'='*80}")
    print("Per-Seed MosaCD Results")
    print(f"{'='*80}")
    for network in args.networks:
        if network not in all_results:
            continue
        print(f"\n  {network.upper()}:")
        for seed in sorted(all_results[network].keys()):
            m = all_results[network][seed]
            if m:
                print(f"    seed={seed:>2}: F1={m['f1']:.3f}  P={m['precision']:.3f}  R={m['recall']:.3f}  SHD={m['shd']}")

    # Print summary
    print(f"\n{'='*80}")
    print(f"MosaCD Multi-Seed Summary")
    print(f"{'='*80}")
    print(f"{'Network':<12} {'Seeds':>6} {'F1 (mean±std)':>18} {'P':>8} {'R':>8}")
    print("-" * 60)

    for network in args.networks:
        if network not in all_results or not all_results[network]:
            continue
        f1s = [m["f1"] for m in all_results[network].values()]
        ps = [m["precision"] for m in all_results[network].values()]
        rs = [m["recall"] for m in all_results[network].values()]
        n = len(f1s)
        print(f"{network:<12} {n:>6} {np.mean(f1s):>7.3f}±{np.std(f1s):>5.3f}  {np.mean(ps):>7.3f} {np.mean(rs):>7.3f}")

    # Save
    out_path = RESULTS_DIR / "multiseed_mosacd_summary.json"
    serializable = {net: {str(s): v for s, v in seeds.items()} for net, seeds in all_results.items()}
    with open(out_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
