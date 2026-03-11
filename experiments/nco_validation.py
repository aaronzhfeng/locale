"""
NCO Validation: Test the false-collider-only finding across sample sizes.

Key claim: 100% of CI errors from the PC algorithm are false colliders
(PC says "collider" when ground truth says "non-collider").

This is a CPU-only experiment — no LLM queries needed. We run PC at
different sample sizes and analyze the CI fact accuracy breakdown.
"""

import json
import time
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np

from mve_insurance import (
    load_network, sample_data, estimate_skeleton, get_ego_graph_info,
)


def analyze_ci_facts(network_name, n_samples, alpha=0.05, seed=42):
    """Run PC and analyze CI fact correctness at a given sample size.

    Returns dict with:
    - total CI facts, correct, incorrect
    - breakdown: false_colliders, false_non_colliders
    - skeleton quality metrics
    """
    model, gt_edges = load_network(network_name)
    gt_edge_set = set(gt_edges) | {(v, u) for u, v in gt_edges}

    # Sample data with fixed seed for reproducibility
    data = sample_data(model, n=n_samples, seed=seed)

    # Run PC
    skeleton, sep_sets = estimate_skeleton(data, alpha=alpha)

    # Skeleton quality
    skel_edges_undirected = set(frozenset({u, v}) for u, v in skeleton.edges())
    gt_edges_undirected = set(frozenset({u, v}) for u, v in gt_edges)
    tp_skel = len(skel_edges_undirected & gt_edges_undirected)
    fp_skel = len(skel_edges_undirected - gt_edges_undirected)
    fn_skel = len(gt_edges_undirected - skel_edges_undirected)
    skel_coverage = tp_skel / max(len(gt_edges_undirected), 1)
    skel_precision = tp_skel / max(len(skel_edges_undirected), 1)

    # Analyze CI facts for all nodes with degree >= 2
    total_facts = 0
    classifiable_facts = 0
    correct_facts = 0
    false_colliders = 0  # PC says collider, truth is non-collider
    false_non_colliders = 0  # PC says non-collider, truth is collider
    true_colliders = 0
    true_non_colliders = 0
    unclassifiable = 0  # skeleton FP edges — no GT to compare against

    nodes = sorted([n for n in skeleton.nodes()
                    if len(list(skeleton.neighbors(n))) >= 2],
                   key=lambda n: -len(list(skeleton.neighbors(n))))

    for node in nodes:
        neighbors, neighbor_adj, ci_facts, edges_to_orient = get_ego_graph_info(
            node, skeleton, sep_sets, gt_edges
        )

        # Build GT map
        gt_map = {}
        for e in gt_edges:
            u, v = e
            if u == node:
                gt_map[v] = f"{u}->{v}"
            elif v == node:
                gt_map[u] = f"{u}->{v}"

        for fact in ci_facts:
            total_facts += 1
            n1, n2 = fact["pair"]

            gt_n1 = gt_map.get(n1)
            gt_n2 = gt_map.get(n2)

            if gt_n1 and gt_n2:
                classifiable_facts += 1
                gt_n1_toward = gt_n1 == f"{n1}->{node}"
                gt_n2_toward = gt_n2 == f"{n2}->{node}"
                gt_is_collider = gt_n1_toward and gt_n2_toward

                if fact["type"] == "collider":
                    if gt_is_collider:
                        correct_facts += 1
                        true_colliders += 1
                    else:
                        false_colliders += 1
                elif fact["type"] == "non-collider":
                    if not gt_is_collider:
                        correct_facts += 1
                        true_non_colliders += 1
                    else:
                        false_non_colliders += 1
            else:
                unclassifiable += 1

    incorrect = classifiable_facts - correct_facts
    false_collider_rate = false_colliders / max(incorrect, 1) if incorrect > 0 else 0.0

    return {
        "metadata": {
            "network": network_name,
            "n_samples": n_samples,
            "alpha": alpha,
            "seed": seed,
        },
        "skeleton": {
            "n_edges": len(skel_edges_undirected),
            "n_gt_edges": len(gt_edges_undirected),
            "coverage": skel_coverage,
            "precision": skel_precision,
            "false_positives": fp_skel,
            "false_negatives": fn_skel,
        },
        "ci_facts": {
            "total": total_facts,
            "classifiable": classifiable_facts,
            "correct": correct_facts,
            "incorrect": incorrect,
            "unclassifiable": unclassifiable,
            "accuracy": correct_facts / max(classifiable_facts, 1),
            "true_colliders": true_colliders,
            "true_non_colliders": true_non_colliders,
            "false_colliders": false_colliders,
            "false_non_colliders": false_non_colliders,
            "false_collider_rate_of_errors": false_collider_rate,
        },
        "n_nodes_analyzed": len(nodes),
    }


def main():
    parser = argparse.ArgumentParser(description="NCO validation across sample sizes")
    parser.add_argument("--networks", nargs="+",
                        default=["insurance", "alarm", "sachs", "child", "asia", "hepar2"])
    parser.add_argument("--sample-sizes", nargs="+", type=int,
                        default=[500, 1000, 2000, 5000, 10000, 20000, 50000])
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 456],
                        help="Multiple seeds for variance estimation")
    args = parser.parse_args()

    all_results = {}

    for network in args.networks:
        print(f"\n{'='*60}")
        print(f"NETWORK: {network}")
        print(f"{'='*60}")

        network_results = {}

        for n_samples in args.sample_sizes:
            seed_results = []
            for seed in args.seeds:
                t0 = time.time()
                try:
                    r = analyze_ci_facts(network, n_samples, alpha=args.alpha, seed=seed)
                    elapsed = time.time() - t0
                    seed_results.append(r)

                    ci = r["ci_facts"]
                    sk = r["skeleton"]
                    print(f"  n={n_samples:>6} seed={seed}: "
                          f"skel_cov={sk['coverage']:.1%} "
                          f"CI: {ci['classifiable']}/{ci['total']} classifiable, "
                          f"{ci['incorrect']} errors "
                          f"(FC={ci['false_colliders']}, FNC={ci['false_non_colliders']}) "
                          f"FC_rate={ci['false_collider_rate_of_errors']:.1%} "
                          f"unclass={ci['unclassifiable']} "
                          f"({elapsed:.1f}s)")
                except Exception as e:
                    print(f"  n={n_samples:>6} seed={seed}: ERROR {e}")
                    import traceback
                    traceback.print_exc()

            if seed_results:
                # Aggregate across seeds
                fc_rates = [r["ci_facts"]["false_collider_rate_of_errors"] for r in seed_results]
                ci_accs = [r["ci_facts"]["accuracy"] for r in seed_results]
                skel_covs = [r["skeleton"]["coverage"] for r in seed_results]
                total_errors = [r["ci_facts"]["incorrect"] for r in seed_results]
                total_fc = [r["ci_facts"]["false_colliders"] for r in seed_results]
                total_fnc = [r["ci_facts"]["false_non_colliders"] for r in seed_results]

                agg = {
                    "n_seeds": len(seed_results),
                    "fc_rate_mean": float(np.mean(fc_rates)),
                    "fc_rate_std": float(np.std(fc_rates)),
                    "ci_accuracy_mean": float(np.mean(ci_accs)),
                    "skel_coverage_mean": float(np.mean(skel_covs)),
                    "total_errors_mean": float(np.mean(total_errors)),
                    "total_fc_mean": float(np.mean(total_fc)),
                    "total_fnc_mean": float(np.mean(total_fnc)),
                    "per_seed": seed_results,
                }
                network_results[str(n_samples)] = agg

        all_results[network] = network_results

    # Summary table
    print(f"\n{'='*80}")
    print("NCO VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"{'Network':<12} {'n_samples':<10} {'Skel_Cov':<10} {'CI_Errs':<10} "
          f"{'FC':<8} {'FNC':<8} {'FC_Rate':<10}")
    print("-" * 80)

    for network, nr in all_results.items():
        for n_str, agg in sorted(nr.items(), key=lambda x: int(x[0])):
            print(f"{network:<12} {n_str:<10} "
                  f"{agg['skel_coverage_mean']:.1%}      "
                  f"{agg['total_errors_mean']:.1f}       "
                  f"{agg['total_fc_mean']:.1f}     "
                  f"{agg['total_fnc_mean']:.1f}     "
                  f"{agg['fc_rate_mean']:.1%}")

    # Save
    out_dir = Path("projects/locale/experiments/results/nco_validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nco_sample_size_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
