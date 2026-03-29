"""
Synthetic ER DAG benchmarks for LOCALE vs MosaCD.

Generates random Erdos-Renyi DAGs with configurable node counts and edge
densities, assigns random CPTs, samples observational data, then runs both
LOCALE and MosaCD pipelines and evaluates against the known ground truth.

Usage:
    python experiments/run_synthetic.py --nodes 20 30 50 --densities 1.5 2.0 3.0 --graph-seeds 0 1 2
    python experiments/run_synthetic.py --nodes 20 --densities 2.0 --graph-seeds 0 --summary-only
"""

import argparse
import json
import os
import sys
import time
import random
from copy import deepcopy
from pathlib import Path
from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import networkx as nx
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────

EXPERIMENTS_DIR = Path(__file__).parent
RESULTS_DIR = EXPERIMENTS_DIR / "results"
sys.path.insert(0, str(EXPERIMENTS_DIR))

# ── Synthetic DAG Generation ────────────────────────────────────


def generate_er_dag(n_nodes, avg_degree, seed=0):
    """Generate an Erdos-Renyi DAG.

    Creates a random graph with approximately avg_degree * n_nodes / 2 edges,
    then orients them according to a random topological ordering to ensure
    acyclicity.

    Returns:
        dag: nx.DiGraph (DAG)
        node_names: list of node name strings (X_0, X_1, ...)
    """
    rng = np.random.RandomState(seed)
    # Edge probability for ER graph: p = avg_degree / (n_nodes - 1)
    p = avg_degree / (n_nodes - 1)
    p = min(p, 1.0)

    # Generate random permutation as topological order
    order = rng.permutation(n_nodes)

    dag = nx.DiGraph()
    node_names = [f"X_{i}" for i in range(n_nodes)]
    dag.add_nodes_from(node_names)

    # Add edges respecting topological order
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if rng.random() < p:
                # Edge from order[i] -> order[j] (respects topological order)
                src = node_names[order[i]]
                dst = node_names[order[j]]
                dag.add_edge(src, dst)

    return dag, node_names


def create_bayesian_network(dag, node_names, seed=0):
    """Create a pgmpy BayesianNetwork with random CPTs from a DAG.

    Each node gets 2-4 categorical states. CPTs are random Dirichlet draws.

    Returns:
        model: pgmpy BayesianNetwork
        var_states: dict mapping node name -> list of state labels
    """
    from pgmpy.models import BayesianNetwork
    from pgmpy.factors.discrete import TabularCPD

    rng = np.random.RandomState(seed)

    # Create BN
    model = BayesianNetwork(list(dag.edges()))
    # Add isolated nodes (no parents, no children)
    for node in node_names:
        if node not in model.nodes():
            model.add_node(node)

    # Assign random number of states per node (2-4)
    var_states = {}
    for node in node_names:
        n_states = rng.choice([2, 3, 4])
        var_states[node] = [f"s{k}" for k in range(n_states)]

    # Create CPTs
    topo_order = list(nx.topological_sort(dag))
    for node in topo_order:
        parents = sorted(dag.predecessors(node))
        n_states = len(var_states[node])

        if not parents:
            # Root node: random marginal
            probs = rng.dirichlet(np.ones(n_states))
            cpd = TabularCPD(
                variable=node,
                variable_card=n_states,
                values=probs.reshape(-1, 1).tolist(),
                state_names={node: var_states[node]},
            )
        else:
            # Node with parents: random conditional distribution
            parent_cards = [len(var_states[p]) for p in parents]
            n_parent_configs = int(np.prod(parent_cards))

            # Draw random conditional distributions (one per parent config)
            values = np.zeros((n_states, n_parent_configs))
            for col in range(n_parent_configs):
                values[:, col] = rng.dirichlet(np.ones(n_states))

            state_names = {node: var_states[node]}
            for p in parents:
                state_names[p] = var_states[p]

            cpd = TabularCPD(
                variable=node,
                variable_card=n_states,
                values=values.tolist(),
                evidence=parents,
                evidence_card=parent_cards,
                state_names=state_names,
            )

        model.add_cpds(cpd)

    assert model.check_model(), f"BN model check failed for seed={seed}"
    return model, var_states


def sample_data(model, n=10000, seed=0):
    """Sample observational data from a BayesianNetwork."""
    from pgmpy.sampling import BayesianModelSampling

    np.random.seed(seed)
    sampler = BayesianModelSampling(model)
    data = sampler.forward_sample(size=n, seed=seed)
    return data


def make_descriptions(node_names, var_states):
    """Create generic variable descriptions (no domain knowledge)."""
    descriptions = {}
    for node in node_names:
        states = var_states[node]
        state_str = ", ".join(states)
        descriptions[node] = f"Categorical variable with states {{{state_str}}}"
    return descriptions


# ── LOCALE Pipeline ─────────────────────────────────────────────


def run_locale_on_synthetic(
    model, gt_edges, data, descriptions, node_names, out_dir,
    k_passes=10, pc_alpha=0.05, data_seed=0,
):
    """Run the full LOCALE pipeline on a synthetic graph.

    Phase 1: ego-graph LLM orientation (mve_insurance.run_mve)
    Phase 2: Max-2SAT reconciliation (phase2_max2sat.run_phase2)
    Phase 3: dual-endpoint reconciliation (phase3_reconcile.run_phase3)

    Returns metrics dict or None on failure.
    """
    import mve_insurance
    from phase2_max2sat import run_phase2 as _run_p2
    from phase3_reconcile import run_phase3 as _run_p3

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Set up globals in mve_insurance module for synthetic data
    mve_insurance.VAR_DESCRIPTIONS = descriptions
    mve_insurance.DISGUISED_NAMES = {
        name: f"V{i+1:02d}" for i, name in enumerate(sorted(descriptions.keys()))
    }
    mve_insurance._domain_text = "synthetic observational dataset domain"
    mve_insurance._use_disguised = True
    mve_insurance.N_SAMPLES = len(data)
    mve_insurance.K_PASSES = k_passes
    mve_insurance.SEED_DATA = data_seed

    # Build args namespace matching what run_mve expects
    args = SimpleNamespace(
        output_dir=str(out_dir),
        no_think=True,
        disguise=True,
        network="insurance",  # placeholder, won't be used for loading
        enriched=False,
        ego_v2=False,
        ego_v3=False,
        temp_ladder=False,
        hybrid=False,
        contrastive=False,
        all_nodes=True,
        n_samples=len(data),
        k_passes=k_passes,
        alpha=pc_alpha,
        debiased=True,
        seed=data_seed,
    )

    # Monkey-patch load_network to return our synthetic model
    original_load = mve_insurance.load_network
    mve_insurance.load_network = lambda name="insurance": (model, gt_edges)

    # Monkey-patch sample_data to return our pre-sampled data
    original_sample = mve_insurance.sample_data
    mve_insurance.sample_data = lambda model, n=10000, seed=42: data

    # Monkey-patch NETWORK_CONFIGS to include a synthetic entry
    original_configs = mve_insurance.NETWORK_CONFIGS
    mve_insurance.NETWORK_CONFIGS["insurance"] = {
        "pgmpy_name": "insurance",
        "descriptions": descriptions,
        "test_nodes": [],  # --all-nodes overrides this
        "domain": "synthetic observational dataset",
    }

    try:
        print(f"\n  [LOCALE Phase 1] Running ego-graph LLM orientation...")
        mve_insurance.run_mve(args)
    except Exception as e:
        print(f"  [LOCALE Phase 1] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Restore originals
        mve_insurance.load_network = original_load
        mve_insurance.sample_data = original_sample
        mve_insurance.NETWORK_CONFIGS = original_configs

    # Phase 2
    p1_path = out_dir / "mve_results.json"
    if not p1_path.exists():
        print(f"  [LOCALE Phase 2] Phase 1 results not found, skipping")
        return None

    print(f"  [LOCALE Phase 2] Running Max-2SAT reconciliation...")
    try:
        p2_results = _run_p2(str(p1_path), collider_mode="non-collider-only")
        p2_path = out_dir / "phase2_results.json"
        with open(p2_path, "w") as f:
            json.dump(p2_results, f, indent=2, default=str)
        acc = p2_results["summary"]["phase2_accuracy"]
        print(f"  [LOCALE Phase 2] Accuracy: {acc:.1f}%")
    except Exception as e:
        print(f"  [LOCALE Phase 2] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Phase 3
    print(f"  [LOCALE Phase 3] Running dual-endpoint reconciliation...")
    try:
        p3_results = _run_p3(str(out_dir))
        if p3_results is None:
            print(f"  [LOCALE Phase 3] FAILED (returned None)")
            return None
        p3_path = out_dir / "phase3_results.json"
        with open(p3_path, "w") as f:
            json.dump(p3_results, f, indent=2, default=str)
        ev = p3_results["evaluation"]
        print(f"  [LOCALE Phase 3] Accuracy: {ev['correct']}/{ev['total']} = {ev['accuracy']:.1%}")
    except Exception as e:
        print(f"  [LOCALE Phase 3] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Compute F1 against full ground truth
    tp = ev["correct"]
    total = ev["total"]
    fp = total - tp
    fn = len(gt_edges) - tp
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-10)

    return {
        "method": "locale",
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "n_gt_edges": len(gt_edges),
        "n_oriented": total,
        "phase2_accuracy": acc,
        "phase3_accuracy": ev["accuracy"],
    }


# ── MosaCD Pipeline ─────────────────────────────────────────────


def run_mosacd_on_synthetic(
    model, gt_edges, data, descriptions, node_names, out_dir,
    n_repeats=5, pc_alpha=0.05, data_seed=0,
):
    """Run the MosaCD pipeline on a synthetic graph.

    Returns metrics dict or None on failure.
    """
    import mve_insurance
    import mosacd_baseline

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Set up globals
    mve_insurance.VAR_DESCRIPTIONS = descriptions
    mve_insurance.DISGUISED_NAMES = {
        name: f"V{i+1:02d}" for i, name in enumerate(sorted(descriptions.keys()))
    }
    mve_insurance._domain_text = "synthetic observational dataset domain"
    mve_insurance._use_disguised = False  # MosaCD uses real names

    # Monkey-patch load_network (must patch BOTH modules — mosacd imports directly)
    original_load = mve_insurance.load_network
    original_load_mosacd = mosacd_baseline.load_network
    mve_insurance.load_network = lambda name="insurance": (model, gt_edges)
    mosacd_baseline.load_network = lambda name="insurance": (model, gt_edges)

    # Monkey-patch sample_data (must patch BOTH modules)
    original_sample = mve_insurance.sample_data
    original_sample_mosacd = mosacd_baseline.sample_data
    mve_insurance.sample_data = lambda model, n=10000, seed=42: data
    mosacd_baseline.sample_data = lambda model, n=10000, seed=42: data

    # Set up MosaCD descriptions and domain
    original_descriptions = mosacd_baseline.DESCRIPTIONS
    original_domain = mosacd_baseline.DOMAIN_DESCRIPTIONS
    original_configs = mve_insurance.NETWORK_CONFIGS

    mosacd_baseline.DESCRIPTIONS["synthetic"] = descriptions
    mosacd_baseline.DOMAIN_DESCRIPTIONS["synthetic"] = (
        "a synthetic observational dataset. Variables are abstract categorical "
        "variables with no domain semantics. Use only the statistical evidence "
        "(conditional independence tests, p-values) to determine causal directions."
    )
    mve_insurance.NETWORK_CONFIGS["synthetic"] = {
        "pgmpy_name": "synthetic",
        "descriptions": descriptions,
        "test_nodes": [],
        "domain": "synthetic observational dataset",
    }

    # Build args namespace
    args = SimpleNamespace(
        network="synthetic",
        n_samples=len(data),
        alpha=pc_alpha,
        no_think=True,
        n_repeats=n_repeats,
        seed=data_seed,
        output_dir=str(out_dir),
    )

    try:
        print(f"\n  [MosaCD] Running 5-step pipeline...")
        results = mosacd_baseline.run_mosacd(args)
    except Exception as e:
        print(f"  [MosaCD] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Restore originals
        mve_insurance.load_network = original_load
        mve_insurance.sample_data = original_sample
        mosacd_baseline.load_network = original_load_mosacd
        mosacd_baseline.sample_data = original_sample_mosacd
        mve_insurance.NETWORK_CONFIGS = original_configs
        mosacd_baseline.DESCRIPTIONS = original_descriptions
        mosacd_baseline.DOMAIN_DESCRIPTIONS = original_domain

    if results is None:
        return None

    metrics = results.get("metrics", {})
    if not metrics:
        return None

    return {
        "method": "mosacd",
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "fn": metrics["fn"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "shd": metrics.get("shd", 0),
        "n_gt_edges": len(gt_edges),
        "n_directed": metrics.get("n_directed", 0),
    }


# ── Summary ─────────────────────────────────────────────────────


def compute_summary(all_results):
    """Aggregate results across all configurations into a summary."""
    summary = {
        "configurations": [],
        "locale_overall": {"f1s": [], "precisions": [], "recalls": []},
        "mosacd_overall": {"f1s": [], "precisions": [], "recalls": []},
    }

    # Group by (nodes, density)
    groups = defaultdict(list)
    for r in all_results:
        key = (r["n_nodes"], r["avg_degree"])
        groups[key].append(r)

    for (n_nodes, avg_degree), runs in sorted(groups.items()):
        locale_f1s = [r["locale"]["f1"] for r in runs if r.get("locale")]
        mosacd_f1s = [r["mosacd"]["f1"] for r in runs if r.get("mosacd")]

        config_summary = {
            "n_nodes": n_nodes,
            "avg_degree": avg_degree,
            "n_graphs": len(runs),
            "n_gt_edges_mean": np.mean([r["n_gt_edges"] for r in runs]),
        }

        if locale_f1s:
            config_summary["locale_f1_mean"] = float(np.mean(locale_f1s))
            config_summary["locale_f1_std"] = float(np.std(locale_f1s))
            summary["locale_overall"]["f1s"].extend(locale_f1s)
            lp = [r["locale"]["precision"] for r in runs if r.get("locale")]
            lr = [r["locale"]["recall"] for r in runs if r.get("locale")]
            config_summary["locale_precision_mean"] = float(np.mean(lp))
            config_summary["locale_recall_mean"] = float(np.mean(lr))
            summary["locale_overall"]["precisions"].extend(lp)
            summary["locale_overall"]["recalls"].extend(lr)

        if mosacd_f1s:
            config_summary["mosacd_f1_mean"] = float(np.mean(mosacd_f1s))
            config_summary["mosacd_f1_std"] = float(np.std(mosacd_f1s))
            summary["mosacd_overall"]["f1s"].extend(mosacd_f1s)
            mp = [r["mosacd"]["precision"] for r in runs if r.get("mosacd")]
            mr = [r["mosacd"]["recall"] for r in runs if r.get("mosacd")]
            config_summary["mosacd_precision_mean"] = float(np.mean(mp))
            config_summary["mosacd_recall_mean"] = float(np.mean(mr))
            summary["mosacd_overall"]["precisions"].extend(mp)
            summary["mosacd_overall"]["recalls"].extend(mr)

        summary["configurations"].append(config_summary)

    # Overall means
    for method in ["locale_overall", "mosacd_overall"]:
        d = summary[method]
        if d["f1s"]:
            d["f1_mean"] = float(np.mean(d["f1s"]))
            d["f1_std"] = float(np.std(d["f1s"]))
            d["precision_mean"] = float(np.mean(d["precisions"]))
            d["recall_mean"] = float(np.mean(d["recalls"]))
        # Remove raw lists from final output
        del d["f1s"]
        del d["precisions"]
        del d["recalls"]

    return summary


def print_summary_table(summary):
    """Print a formatted summary table."""
    print(f"\n{'='*90}")
    print("Synthetic ER DAG Benchmark Summary")
    print(f"{'='*90}")

    header = f"{'Config':<20} {'#Edges':>7} {'LOCALE F1':>14} {'MosaCD F1':>14} {'Delta':>10}"
    print(header)
    print("-" * 90)

    for cfg in summary["configurations"]:
        label = f"{cfg['n_nodes']}n, d={cfg['avg_degree']}"
        edges = f"{cfg['n_gt_edges_mean']:.0f}"

        locale_str = "N/A"
        mosacd_str = "N/A"
        delta_str = "N/A"

        if "locale_f1_mean" in cfg:
            locale_str = f"{cfg['locale_f1_mean']:.3f}+/-{cfg['locale_f1_std']:.3f}"
        if "mosacd_f1_mean" in cfg:
            mosacd_str = f"{cfg['mosacd_f1_mean']:.3f}+/-{cfg['mosacd_f1_std']:.3f}"
        if "locale_f1_mean" in cfg and "mosacd_f1_mean" in cfg:
            delta = cfg["locale_f1_mean"] - cfg["mosacd_f1_mean"]
            delta_str = f"{delta:+.3f}"

        print(f"{label:<20} {edges:>7} {locale_str:>14} {mosacd_str:>14} {delta_str:>10}")

    print("-" * 90)

    # Overall
    lo = summary.get("locale_overall", {})
    mo = summary.get("mosacd_overall", {})
    if "f1_mean" in lo and "f1_mean" in mo:
        overall_delta = lo["f1_mean"] - mo["f1_mean"]
        print(f"{'OVERALL':<20} {'':>7} "
              f"{lo['f1_mean']:.3f}+/-{lo['f1_std']:.3f}{'':>1} "
              f"{mo['f1_mean']:.3f}+/-{mo['f1_std']:.3f}{'':>1} "
              f"{overall_delta:+.3f}")
    print(f"{'='*90}")


# ── Main ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Synthetic ER DAG benchmarks: LOCALE vs MosaCD"
    )
    parser.add_argument(
        "--nodes", type=int, nargs="+", default=[20, 30, 50],
        help="Node counts to test (default: 20 30 50)"
    )
    parser.add_argument(
        "--densities", type=float, nargs="+", default=[1.5, 2.0, 3.0],
        help="Average degrees to test (default: 1.5 2.0 3.0)"
    )
    parser.add_argument(
        "--graph-seeds", type=int, nargs="+", default=[0, 1, 2],
        help="Graph generation seeds (default: 0 1 2)"
    )
    parser.add_argument(
        "--data-seed", type=int, default=0,
        help="Data sampling seed (default: 0)"
    )
    parser.add_argument(
        "--n-samples", type=int, default=10000,
        help="Number of observational samples (default: 10000)"
    )
    parser.add_argument(
        "--k-passes", type=int, default=10,
        help="LOCALE K passes (default: 10)"
    )
    parser.add_argument(
        "--n-repeats", type=int, default=5,
        help="MosaCD repeats per ordering (default: 5)"
    )
    parser.add_argument(
        "--pc-alpha", type=float, default=0.05,
        help="PC skeleton significance level (default: 0.05)"
    )
    parser.add_argument(
        "--skip-locale", action="store_true",
        help="Skip LOCALE runs (only run MosaCD)"
    )
    parser.add_argument(
        "--skip-mosacd", action="store_true",
        help="Skip MosaCD runs (only run LOCALE)"
    )
    parser.add_argument(
        "--summary-only", action="store_true",
        help="Only compute summary from existing results"
    )
    args = parser.parse_args()

    all_results = []
    total_configs = len(args.nodes) * len(args.densities) * len(args.graph_seeds)
    config_idx = 0

    for n_nodes in args.nodes:
        for avg_degree in args.densities:
            for graph_seed in args.graph_seeds:
                config_idx += 1
                density_label = f"{avg_degree:.1f}".replace(".", "")
                config_label = f"{n_nodes}n_{density_label}d_g{graph_seed}"

                locale_dir = RESULTS_DIR / f"synthetic_er_{config_label}"
                mosacd_dir = RESULTS_DIR / f"synthetic_er_mosacd_{config_label}"

                print(f"\n{'#'*70}")
                print(f"# Config {config_idx}/{total_configs}: "
                      f"n={n_nodes}, avg_degree={avg_degree}, graph_seed={graph_seed}")
                print(f"{'#'*70}")

                # Check for existing results if summary-only
                if args.summary_only:
                    result = _load_existing_result(
                        n_nodes, avg_degree, graph_seed, locale_dir, mosacd_dir
                    )
                    if result:
                        all_results.append(result)
                    continue

                # Generate DAG
                print(f"\n  Generating ER DAG (n={n_nodes}, d={avg_degree}, seed={graph_seed})...")
                dag, node_names = generate_er_dag(n_nodes, avg_degree, seed=graph_seed)
                gt_edges = set(dag.edges())
                print(f"  DAG: {len(dag.nodes())} nodes, {len(gt_edges)} edges")

                if len(gt_edges) == 0:
                    print(f"  WARNING: DAG has no edges, skipping")
                    continue

                # Create BN
                print(f"  Creating Bayesian network with random CPTs...")
                model, var_states = create_bayesian_network(dag, node_names, seed=graph_seed)
                descriptions = make_descriptions(node_names, var_states)

                # Sample data
                print(f"  Sampling {args.n_samples} observations (data_seed={args.data_seed})...")
                data = sample_data(model, n=args.n_samples, seed=args.data_seed)
                print(f"  Data shape: {data.shape}")

                result = {
                    "n_nodes": n_nodes,
                    "avg_degree": avg_degree,
                    "graph_seed": graph_seed,
                    "data_seed": args.data_seed,
                    "n_gt_edges": len(gt_edges),
                    "n_samples": args.n_samples,
                    "locale": None,
                    "mosacd": None,
                }

                # Save DAG info
                dag_info = {
                    "n_nodes": n_nodes,
                    "avg_degree": avg_degree,
                    "graph_seed": graph_seed,
                    "n_edges": len(gt_edges),
                    "edges": [list(e) for e in gt_edges],
                    "nodes": node_names,
                    "var_states": var_states,
                    "descriptions": descriptions,
                }

                # Run LOCALE
                if not args.skip_locale:
                    locale_dir.mkdir(parents=True, exist_ok=True)
                    with open(locale_dir / "dag_info.json", "w") as f:
                        json.dump(dag_info, f, indent=2)

                    t0 = time.time()
                    locale_metrics = run_locale_on_synthetic(
                        model, gt_edges, data, descriptions, node_names,
                        out_dir=str(locale_dir),
                        k_passes=args.k_passes,
                        pc_alpha=args.pc_alpha,
                        data_seed=args.data_seed,
                    )
                    locale_elapsed = time.time() - t0

                    if locale_metrics:
                        locale_metrics["elapsed_seconds"] = locale_elapsed
                        result["locale"] = locale_metrics
                        print(f"\n  LOCALE: F1={locale_metrics['f1']:.3f}, "
                              f"P={locale_metrics['precision']:.3f}, "
                              f"R={locale_metrics['recall']:.3f} "
                              f"({locale_elapsed:.0f}s)")
                    else:
                        print(f"\n  LOCALE: FAILED")

                # Run MosaCD
                if not args.skip_mosacd:
                    mosacd_dir.mkdir(parents=True, exist_ok=True)
                    with open(mosacd_dir / "dag_info.json", "w") as f:
                        json.dump(dag_info, f, indent=2)

                    t0 = time.time()
                    mosacd_metrics = run_mosacd_on_synthetic(
                        model, gt_edges, data, descriptions, node_names,
                        out_dir=str(mosacd_dir),
                        n_repeats=args.n_repeats,
                        pc_alpha=args.pc_alpha,
                        data_seed=args.data_seed,
                    )
                    mosacd_elapsed = time.time() - t0

                    if mosacd_metrics:
                        mosacd_metrics["elapsed_seconds"] = mosacd_elapsed
                        result["mosacd"] = mosacd_metrics
                        print(f"\n  MosaCD: F1={mosacd_metrics['f1']:.3f}, "
                              f"P={mosacd_metrics['precision']:.3f}, "
                              f"R={mosacd_metrics['recall']:.3f} "
                              f"({mosacd_elapsed:.0f}s)")
                    else:
                        print(f"\n  MosaCD: FAILED")

                all_results.append(result)

                # Save per-config result
                _save_config_result(result, locale_dir, mosacd_dir)

    # Summary
    if all_results:
        summary = compute_summary(all_results)
        print_summary_table(summary)

        # Save full summary JSON
        summary_path = RESULTS_DIR / "synthetic_er_summary.json"
        full_output = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "args": {
                "nodes": args.nodes,
                "densities": args.densities,
                "graph_seeds": args.graph_seeds,
                "data_seed": args.data_seed,
                "n_samples": args.n_samples,
                "k_passes": args.k_passes,
                "n_repeats": args.n_repeats,
                "pc_alpha": args.pc_alpha,
            },
            "summary": summary,
            "per_graph": all_results,
        }
        with open(summary_path, "w") as f:
            json.dump(full_output, f, indent=2, default=str)
        print(f"\nFull summary saved to {summary_path}")
    else:
        print("\nNo results to summarize.")


def _load_existing_result(n_nodes, avg_degree, graph_seed, locale_dir, mosacd_dir):
    """Load existing results for a configuration."""
    result = {
        "n_nodes": n_nodes,
        "avg_degree": avg_degree,
        "graph_seed": graph_seed,
        "locale": None,
        "mosacd": None,
    }
    found = False

    # Load DAG info
    dag_info_path = locale_dir / "dag_info.json"
    if not dag_info_path.exists():
        dag_info_path = mosacd_dir / "dag_info.json"
    if dag_info_path.exists():
        with open(dag_info_path) as f:
            dag_info = json.load(f)
        result["n_gt_edges"] = dag_info["n_edges"]

    # LOCALE results
    p3_path = locale_dir / "phase3_results.json"
    p1_path = locale_dir / "mve_results.json"
    if p3_path.exists() and p1_path.exists():
        with open(p3_path) as f:
            p3 = json.load(f)
        ev = p3["evaluation"]
        tp = ev["correct"]
        total = ev["total"]
        fp = total - tp

        gt_edges_count = result.get("n_gt_edges", 0)
        fn = gt_edges_count - tp if gt_edges_count else 0

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-10)

        result["locale"] = {
            "method": "locale",
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "n_gt_edges": gt_edges_count,
            "n_oriented": total,
        }
        found = True

    # MosaCD results
    mosacd_path = mosacd_dir / "mosacd_results.json"
    if mosacd_path.exists():
        with open(mosacd_path) as f:
            mosacd_res = json.load(f)
        metrics = mosacd_res.get("metrics", {})
        if metrics:
            result["mosacd"] = {
                "method": "mosacd",
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "shd": metrics.get("shd", 0),
            }
            found = True

    return result if found else None


def _save_config_result(result, locale_dir, mosacd_dir):
    """Save a per-configuration result summary."""
    summary = {
        "n_nodes": result["n_nodes"],
        "avg_degree": result["avg_degree"],
        "graph_seed": result["graph_seed"],
        "n_gt_edges": result.get("n_gt_edges", 0),
    }
    if result.get("locale"):
        summary["locale_f1"] = result["locale"]["f1"]
        summary["locale_precision"] = result["locale"]["precision"]
        summary["locale_recall"] = result["locale"]["recall"]
    if result.get("mosacd"):
        summary["mosacd_f1"] = result["mosacd"]["f1"]
        summary["mosacd_precision"] = result["mosacd"]["precision"]
        summary["mosacd_recall"] = result["mosacd"]["recall"]

    for d in [locale_dir, mosacd_dir]:
        if d.exists():
            with open(d / "config_summary.json", "w") as f:
                json.dump(summary, f, indent=2)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
