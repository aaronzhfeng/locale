"""
Skeleton Analysis: Systematic evaluation of skeleton quality across configurations.

Tests:
1. PC-stable at different alpha values (0.01, 0.05, 0.10, 0.20, 0.50)
2. Different sample sizes (1k, 5k, 10k, 50k)
3. Skeleton union (combine multiple alphas)
4. Conservative PC (CPC) if available in pgmpy

Goal: Understand the coverage-precision tradeoff and find configurations
that maximize directed-edge F1 potential (coverage × orientation ceiling).

CPU-only — no LLM queries.
"""

import json
import time
import argparse
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np

from mve_insurance import (
    load_network, sample_data, estimate_skeleton,
    NETWORK_CONFIGS,
)


NETWORKS = ["insurance", "alarm", "sachs", "child", "asia", "hepar2"]
ALPHAS = [0.001, 0.01, 0.05, 0.10, 0.20, 0.50]
SAMPLE_SIZES = [1000, 5000, 10000]  # Skip 50k — too slow for Hepar2 PC
SEEDS = [0, 1, 2, 42]


def skeleton_quality(skeleton, gt_edges):
    """Compute skeleton coverage (recall) and precision."""
    skel_edges = set(frozenset({u, v}) for u, v in skeleton.edges())
    gt_undirected = set(frozenset({u, v}) for u, v in gt_edges)

    tp = len(skel_edges & gt_undirected)
    fp = len(skel_edges - gt_undirected)
    fn = len(gt_undirected - skel_edges)

    coverage = tp / max(len(gt_undirected), 1)
    precision = tp / max(len(skel_edges), 1)
    f1 = 2 * precision * coverage / max(precision + coverage, 1e-10)

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "n_skel": len(skel_edges), "n_gt": len(gt_undirected),
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "f1": round(f1, 4),
    }


def f1_ceiling(coverage, orient_acc=1.0):
    """Compute the directed-edge F1 ceiling given skeleton coverage and orientation accuracy.

    Assumes: precision of oriented skeleton edges = orient_acc (no FP orientation errors).
    F1 ceiling = 2 * (orient_acc * coverage) / (orient_acc + coverage)
    With perfect orientation (1.0), F1 = 2*coverage/(1+coverage).
    """
    p = orient_acc
    r = coverage
    if p + r == 0:
        return 0
    return round(2 * p * r / (p + r), 4)


def union_skeletons(skeletons_list):
    """Combine multiple skeletons into their union (maximize coverage)."""
    import networkx as nx
    union = nx.Graph()
    for skel in skeletons_list:
        union.add_edges_from(skel.edges())
        union.add_nodes_from(skel.nodes())
    return union


def intersection_skeletons(skeletons_list):
    """Combine multiple skeletons into their intersection (maximize precision)."""
    import networkx as nx
    if not skeletons_list:
        return nx.Graph()
    # Start with all edges from first skeleton
    edge_sets = [set(frozenset({u, v}) for u, v in s.edges()) for s in skeletons_list]
    common = edge_sets[0]
    for es in edge_sets[1:]:
        common &= es
    inter = nx.Graph()
    for s in skeletons_list:
        inter.add_nodes_from(s.nodes())
    for e in common:
        u, v = tuple(e)
        inter.add_edge(u, v)
    return inter


def run_alpha_sweep(network, n_samples, seed):
    """Run PC at multiple alphas and compute skeleton quality for each."""
    model, gt_edges = load_network(NETWORK_CONFIGS[network]["pgmpy_name"])
    data = sample_data(model, n=n_samples, seed=seed)

    results = {}
    skeletons = {}
    for alpha in ALPHAS:
        t0 = time.time()
        skeleton, sep_sets = estimate_skeleton(data, alpha=alpha)
        elapsed = time.time() - t0
        q = skeleton_quality(skeleton, gt_edges)
        q["alpha"] = alpha
        q["time_s"] = round(elapsed, 2)
        q["f1_ceiling_perfect"] = f1_ceiling(q["coverage"], 1.0)
        q["f1_ceiling_90"] = f1_ceiling(q["coverage"], 0.90)
        results[f"alpha_{alpha}"] = q
        skeletons[alpha] = skeleton

    # Union of all alphas
    union = union_skeletons(list(skeletons.values()))
    q_union = skeleton_quality(union, gt_edges)
    q_union["f1_ceiling_perfect"] = f1_ceiling(q_union["coverage"], 1.0)
    q_union["f1_ceiling_90"] = f1_ceiling(q_union["coverage"], 0.90)
    results["union_all"] = q_union

    # Union of conservative alphas (0.05, 0.10, 0.20)
    conservative_keys = [a for a in [0.05, 0.10, 0.20] if a in skeletons]
    if len(conservative_keys) > 1:
        union_cons = union_skeletons([skeletons[a] for a in conservative_keys])
        q_cons = skeleton_quality(union_cons, gt_edges)
        q_cons["f1_ceiling_perfect"] = f1_ceiling(q_cons["coverage"], 1.0)
        q_cons["f1_ceiling_90"] = f1_ceiling(q_cons["coverage"], 0.90)
        results["union_0.05_0.10_0.20"] = q_cons

    return results, skeletons


def run_sample_size_sweep(network, alpha=0.05, seed=42):
    """Run PC at different sample sizes with fixed alpha."""
    model, gt_edges = load_network(NETWORK_CONFIGS[network]["pgmpy_name"])

    results = {}
    for n in SAMPLE_SIZES:
        data = sample_data(model, n=n, seed=seed)
        t0 = time.time()
        skeleton, sep_sets = estimate_skeleton(data, alpha=alpha)
        elapsed = time.time() - t0
        q = skeleton_quality(skeleton, gt_edges)
        q["n_samples"] = n
        q["time_s"] = round(elapsed, 2)
        q["f1_ceiling_perfect"] = f1_ceiling(q["coverage"], 1.0)
        results[f"n_{n}"] = q

    return results


def run_multi_seed_alpha(network, n_samples=10000):
    """Run alpha sweep across multiple seeds for robustness."""
    all_results = defaultdict(list)

    for seed in SEEDS:
        results, _ = run_alpha_sweep(network, n_samples, seed)
        for key, metrics in results.items():
            all_results[key].append(metrics)

    # Aggregate: mean ± std for each metric
    summary = {}
    for key, runs in all_results.items():
        summary[key] = {}
        for metric in ["coverage", "precision", "f1", "tp", "fp", "fn", "n_skel",
                        "f1_ceiling_perfect", "f1_ceiling_90"]:
            if metric in runs[0]:
                values = [r[metric] for r in runs]
                summary[key][metric] = {
                    "mean": round(np.mean(values), 4),
                    "std": round(np.std(values), 4),
                    "min": round(np.min(values), 4),
                    "max": round(np.max(values), 4),
                }

    return summary


def print_alpha_table(results, network):
    """Pretty-print alpha sweep results."""
    print(f"\n{'='*80}")
    print(f"  {network.upper()} — Alpha Sweep (n=10k, 4 seeds)")
    print(f"{'='*80}")
    print(f"{'Config':<25} {'Coverage':>12} {'Precision':>12} {'F1(skel)':>12} {'F1 ceil':>12}")
    print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

    for key in sorted(results.keys()):
        r = results[key]
        cov = r.get("coverage", {})
        prec = r.get("precision", {})
        f1 = r.get("f1", {})
        ceil = r.get("f1_ceiling_perfect", {})

        cov_str = f"{cov.get('mean', 0):.1%}±{cov.get('std', 0):.1%}"
        prec_str = f"{prec.get('mean', 0):.1%}±{prec.get('std', 0):.1%}"
        f1_str = f"{f1.get('mean', 0):.1%}±{f1.get('std', 0):.1%}"
        ceil_str = f"{ceil.get('mean', 0):.3f}±{ceil.get('std', 0):.3f}"

        print(f"{key:<25} {cov_str:>12} {prec_str:>12} {f1_str:>12} {ceil_str:>12}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default="all", help="Network name or 'all'")
    parser.add_argument("--n-samples", type=int, default=10000)
    parser.add_argument("--mode", choices=["alpha", "sample_size", "full"], default="full")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    networks = NETWORKS if args.network == "all" else [args.network]
    out_dir = Path("results/skeleton_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_data = {}

    for network in networks:
        print(f"\n{'#'*60}")
        print(f"  Processing: {network}")
        print(f"{'#'*60}")

        net_data = {}

        if args.mode in ("alpha", "full"):
            print(f"\n  [Alpha sweep] n={args.n_samples}, seeds={SEEDS}")
            summary = run_multi_seed_alpha(network, args.n_samples)
            print_alpha_table(summary, network)
            net_data["alpha_sweep"] = summary

        if args.mode in ("sample_size", "full"):
            print(f"\n  [Sample size sweep] alpha=0.05, seed={args.seed}")
            ss_results = run_sample_size_sweep(network, alpha=0.05, seed=args.seed)
            for key, r in sorted(ss_results.items()):
                print(f"    {key}: coverage={r['coverage']:.1%}, precision={r['precision']:.1%}, "
                      f"f1={r['f1']:.1%}, edges={r['n_skel']}")
            net_data["sample_size_sweep"] = ss_results

        all_data[network] = net_data

    # Save
    outfile = out_dir / "skeleton_analysis.json"
    with open(outfile, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"\nResults saved to {outfile}")

    # Print summary comparison: current (alpha=0.05) vs best config per network
    print(f"\n{'='*80}")
    print(f"  SUMMARY: Current vs Best Skeleton Config")
    print(f"{'='*80}")
    print(f"{'Network':<12} {'Current cov':>12} {'Best cov':>12} {'Best config':>20} {'F1 ceiling':>12}")
    for network in networks:
        if "alpha_sweep" in all_data[network]:
            sweep = all_data[network]["alpha_sweep"]
            current = sweep.get("alpha_0.05", {}).get("coverage", {}).get("mean", 0)
            best_cov = 0
            best_key = ""
            for key, metrics in sweep.items():
                cov = metrics.get("coverage", {}).get("mean", 0)
                if cov > best_cov:
                    best_cov = cov
                    best_key = key
            best_ceil = sweep[best_key].get("f1_ceiling_perfect", {}).get("mean", 0)
            print(f"{network:<12} {current:>11.1%} {best_cov:>11.1%} {best_key:>20} {best_ceil:>12.3f}")


if __name__ == "__main__":
    main()
