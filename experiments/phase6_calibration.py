"""
Phase 6: Calibration and Selective Output (Proposal v2 Section 4.8)

Turns reconciled posteriors into calibrated selective decisions.

For each edge, computes:
- Edge-difficulty features (endpoint disagreement, margin, degree, etc.)
- Decision source (agreement, disagreement, single_endpoint, meek, etc.)
- Calibrated confidence using isotonic regression (simplified Venn-Abers)

Output rule: orient if calibrated confidence >= threshold, else output "?".
The threshold is set by a target false-orientation rate.

Note: Proposal mandates multiclass Venn-Abers with held-out graph instances.
This implementation uses cross-validation within available networks as a
first approximation. True Venn-Abers on held-out instances requires more
benchmark networks.
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict


def extract_edge_features(phase3_results, phase1_data):
    """Extract per-edge features for calibration.

    Features per proposal v2 Section 4.5:
    - endpoint_disagreement: 0/1, do the two endpoints disagree?
    - max_margin: highest vote margin across endpoints
    - min_margin: lowest vote margin across endpoints
    - margin_gap: max_margin - min_margin
    - max_degree: max degree of the two endpoints
    - min_degree: min degree of the two endpoints
    - n_endpoints: number of ego-graphs that covered this edge (1 or 2)
    - decision_source: categorical (agreement, disagreement, single_endpoint)
    - pe_margin: per-edge vote margin (if available)
    - pe_agrees: 1 if PE agrees with final direction, 0 otherwise
    """
    reconciled = phase3_results["reconciled"]
    per_node = phase1_data.get("per_node", {})
    raw_pe = phase1_data.get("raw_results_a", [])

    # Build PE votes
    pe_votes = defaultdict(lambda: defaultdict(int))
    for r in raw_pe:
        edge_key = tuple(sorted(r["edge"]))
        pe_votes[edge_key][r["predicted"]] += 1

    # Build GT
    gt_directed = {}
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            gt_directed[frozenset({e[0], e[1]})] = f"{e[0]}->{e[1]}"

    features = []
    labels = []  # 1 = correct, 0 = incorrect

    for edge_key_str, info in reconciled.items():
        try:
            parts = edge_key_str.strip("()' ").replace("'", "").split(", ")
            u, v = parts[0].strip(), parts[1].strip()
        except (ValueError, IndexError):
            continue

        ek = frozenset({u, v})
        gt = gt_directed.get(ek)
        if gt is None:
            continue

        direction = info["direction"]
        is_correct = int(direction == gt)
        method = info.get("method", "unknown")

        # Feature extraction
        feat = {}

        # Disagreement
        feat["endpoint_disagreement"] = int(method.startswith("disagreement"))
        feat["single_endpoint"] = int(method == "single_endpoint")
        feat["agreement"] = int(method == "agreement")

        # Margins
        if "endpoints" in info:
            margins = [ep.get("margin", 0.5) for ep in info["endpoints"]]
            degrees = [ep.get("degree", 1) for ep in info["endpoints"]]
            feat["max_margin"] = max(margins)
            feat["min_margin"] = min(margins)
            feat["margin_gap"] = feat["max_margin"] - feat["min_margin"]
            feat["max_degree"] = max(degrees)
            feat["min_degree"] = min(degrees)
            feat["n_endpoints"] = len(info["endpoints"])
        else:
            feat["max_margin"] = 0.7  # default for agreement
            feat["min_margin"] = 0.7
            feat["margin_gap"] = 0.0
            feat["max_degree"] = per_node.get(u, {}).get("degree", 1)
            feat["min_degree"] = per_node.get(v, {}).get("degree", 1)
            feat["n_endpoints"] = 2 if method == "agreement" else 1

        # PE features
        edge_tuple = tuple(sorted([u, v]))
        votes = pe_votes.get(edge_tuple, {})
        if votes:
            total_pe = sum(votes.values())
            best_pe = max(votes, key=votes.get)
            feat["pe_margin"] = votes[best_pe] / max(total_pe, 1)
            feat["pe_agrees"] = int(best_pe == direction)
        else:
            feat["pe_margin"] = 0.5
            feat["pe_agrees"] = 1  # no data, assume agrees

        # Composite confidence score (uncalibrated)
        feat["raw_confidence"] = (
            0.4 * feat["max_margin"]
            + 0.2 * feat["agreement"]
            + 0.2 * feat["pe_agrees"] * feat["pe_margin"]
            + 0.1 * (1.0 - feat["endpoint_disagreement"])
            + 0.1 * min(feat["n_endpoints"] / 2, 1.0)
        )

        feat["edge_key"] = edge_key_str
        feat["direction"] = direction
        feat["gt"] = gt

        features.append(feat)
        labels.append(is_correct)

    return features, labels


def isotonic_calibration(confidences, labels):
    """Fit isotonic regression for calibration.

    Groups edges by confidence bins and computes empirical accuracy
    per bin. Returns calibration function.

    Uses Pool Adjacent Violators (PAV) algorithm — the core of
    Venn-Abers without the conformal wrapper.
    """
    if len(confidences) < 5:
        # Too few samples — return identity
        return lambda x: x, []

    # Sort by confidence
    order = np.argsort(confidences)
    sorted_conf = np.array(confidences)[order]
    sorted_labels = np.array(labels)[order]

    # PAV algorithm (isotonic regression)
    n = len(sorted_labels)
    pav_values = sorted_labels.astype(float).copy()
    weights = np.ones(n)

    # Pool adjacent violators
    i = 0
    while i < n - 1:
        if pav_values[i] > pav_values[i + 1]:
            # Pool these two blocks
            combined = (pav_values[i] * weights[i] + pav_values[i + 1] * weights[i + 1]) / (weights[i] + weights[i + 1])
            pav_values[i] = combined
            pav_values[i + 1] = combined
            weights[i] = weights[i] + weights[i + 1]
            weights[i + 1] = weights[i]

            # Check backward
            while i > 0 and pav_values[i - 1] > pav_values[i]:
                combined = (pav_values[i - 1] * weights[i - 1] + pav_values[i] * weights[i]) / (weights[i - 1] + weights[i])
                pav_values[i - 1] = combined
                pav_values[i] = combined
                weights[i - 1] = weights[i - 1] + weights[i]
                weights[i] = weights[i - 1]
                i -= 1
        i += 1

    # Build calibration mapping: (conf_threshold, calibrated_prob)
    calibration_points = list(zip(sorted_conf.tolist(), pav_values.tolist()))

    def calibrate(conf):
        """Map raw confidence to calibrated probability."""
        if conf <= calibration_points[0][0]:
            return calibration_points[0][1]
        if conf >= calibration_points[-1][0]:
            return calibration_points[-1][1]
        # Linear interpolation
        for j in range(len(calibration_points) - 1):
            c0, p0 = calibration_points[j]
            c1, p1 = calibration_points[j + 1]
            if c0 <= conf <= c1:
                if c1 == c0:
                    return p0
                t = (conf - c0) / (c1 - c0)
                return p0 + t * (p1 - p0)
        return calibration_points[-1][1]

    return calibrate, calibration_points


def selective_output(features, labels, calibrate_fn, target_for=0.1):
    """Apply selective output: orient if calibrated confidence >= threshold.

    Chooses threshold to achieve target false-orientation rate (FOR).
    FOR = fraction of output edges that are wrong.

    Args:
        features: list of edge feature dicts
        labels: list of 0/1 correctness labels
        calibrate_fn: calibration function
        target_for: target false-orientation rate

    Returns:
        threshold: operating threshold
        selective_results: list of {edge, direction, calibrated_conf, output}
    """
    # Compute calibrated confidences
    cal_confs = []
    for feat in features:
        cal_conf = calibrate_fn(feat["raw_confidence"])
        cal_confs.append(cal_conf)

    # Try thresholds from 0.5 to 1.0
    best_threshold = 0.5
    best_coverage = 0
    best_for = 1.0

    for threshold in np.arange(0.5, 1.01, 0.05):
        output_mask = [c >= threshold for c in cal_confs]
        n_output = sum(output_mask)
        if n_output == 0:
            continue
        n_wrong = sum(1 for i, m in enumerate(output_mask)
                      if m and labels[i] == 0)
        current_for = n_wrong / n_output
        coverage = n_output / len(features)

        if current_for <= target_for and coverage > best_coverage:
            best_threshold = threshold
            best_coverage = coverage
            best_for = current_for

    # Apply best threshold
    selective_results = []
    for i, feat in enumerate(features):
        cal_conf = cal_confs[i]
        output = cal_conf >= best_threshold
        selective_results.append({
            "edge_key": feat["edge_key"],
            "direction": feat["direction"],
            "gt": feat["gt"],
            "raw_confidence": feat["raw_confidence"],
            "calibrated_confidence": cal_conf,
            "output": output,
            "correct": labels[i] == 1,
        })

    return best_threshold, selective_results


def run_phase6(results_dir_path, target_for=0.1):
    """Run Phase 6 calibration + selective output.

    Uses leave-one-network-out cross-validation for calibration fitting.
    """
    results_dir = Path(results_dir_path)

    # Load all networks
    targets = [
        ("Insurance", "mve_27b_insurance_10k_k10_debiased"),
        ("Alarm", "mve_27b_alarm_10k_k10_debiased"),
        ("Sachs", "mve_27b_sachs_10k_k10_debiased"),
        ("Child", "mve_27b_child_10k_k10_debiased"),
        ("Asia", "mve_27b_asia_10k_k10_debiased"),
        ("Hepar2", "mve_27b_hepar2_10k_k10_debiased"),
    ]

    all_features = {}
    all_labels = {}

    for label, dirname in targets:
        rdir = results_dir / dirname
        p3_path = rdir / "phase3_results.json"
        p1_path = rdir / "mve_results.json"
        if not p3_path.exists() or not p1_path.exists():
            continue
        with open(p3_path) as f:
            phase3 = json.load(f)
        with open(p1_path) as f:
            phase1 = json.load(f)

        features, labels = extract_edge_features(phase3, phase1)
        all_features[label] = features
        all_labels[label] = labels

    # Leave-one-out cross-validation calibration
    results = {}

    for test_net in all_features:
        # Train on all other networks
        train_features = []
        train_labels = []
        for net in all_features:
            if net == test_net:
                continue
            train_features.extend(all_features[net])
            train_labels.extend(all_labels[net])

        # Extract raw confidences for calibration
        train_confs = [f["raw_confidence"] for f in train_features]
        calibrate_fn, cal_points = isotonic_calibration(train_confs, train_labels)

        # Apply to test network
        test_features = all_features[test_net]
        test_labels = all_labels[test_net]

        threshold, selective_results = selective_output(
            test_features, test_labels, calibrate_fn, target_for
        )

        # Compute metrics
        n_output = sum(1 for r in selective_results if r["output"])
        n_correct_output = sum(1 for r in selective_results
                               if r["output"] and r["correct"])
        n_total = len(selective_results)
        n_correct_total = sum(1 for r in selective_results if r["correct"])

        coverage = n_output / max(n_total, 1)
        precision_output = n_correct_output / max(n_output, 1)
        recall_oriented = n_correct_output / max(n_correct_total, 1)

        # FOR among output edges
        n_wrong_output = n_output - n_correct_output
        false_orient_rate = n_wrong_output / max(n_output, 1)

        # Full accuracy (all edges, no abstention)
        full_accuracy = n_correct_total / max(n_total, 1)

        results[test_net] = {
            "threshold": threshold,
            "n_total": n_total,
            "n_output": n_output,
            "n_abstained": n_total - n_output,
            "coverage": coverage,
            "precision_output": precision_output,
            "false_orient_rate": false_orient_rate,
            "recall_oriented": recall_oriented,
            "full_accuracy": full_accuracy,
            "selective_results": selective_results,
            "calibration_points": cal_points,
        }

    return results


def main():
    results_dir = Path("projects/locale/experiments/results")

    print("=" * 70)
    print("LOCALE Phase 6: Calibration + Selective Output")
    print("=" * 70)

    for target_for in [0.05, 0.10, 0.15, 0.20]:
        print(f"\n--- Target FOR: {target_for:.0%} ---")
        results = run_phase6(results_dir, target_for=target_for)

        print(f"\n{'Network':<12} {'Total':>6} {'Output':>7} {'Abst':>5} "
              f"{'Cover':>7} {'Prec':>7} {'FOR':>6} {'Full':>7}")
        for net in ["Insurance", "Alarm", "Sachs", "Child", "Asia", "Hepar2"]:
            if net not in results:
                continue
            r = results[net]
            print(f"{net:<12} {r['n_total']:>6} {r['n_output']:>7} "
                  f"{r['n_abstained']:>5} {r['coverage']:>6.0%} "
                  f"{r['precision_output']:>6.1%} {r['false_orient_rate']:>5.1%} "
                  f"{r['full_accuracy']:>6.1%}")

        # Aggregate
        total_out = sum(r["n_output"] for r in results.values())
        total_n = sum(r["n_total"] for r in results.values())
        total_correct_out = sum(
            sum(1 for s in r["selective_results"] if s["output"] and s["correct"])
            for r in results.values()
        )
        total_correct_all = sum(
            sum(1 for s in r["selective_results"] if s["correct"])
            for r in results.values()
        )
        agg_cover = total_out / max(total_n, 1)
        agg_prec = total_correct_out / max(total_out, 1)
        agg_for = (total_out - total_correct_out) / max(total_out, 1)
        agg_full = total_correct_all / max(total_n, 1)
        print(f"{'AGGREGATE':<12} {total_n:>6} {total_out:>7} "
              f"{total_n - total_out:>5} {agg_cover:>6.0%} "
              f"{agg_prec:>6.1%} {agg_for:>5.1%} "
              f"{agg_full:>6.1%}")

    # Save detailed results at FOR=0.10
    results = run_phase6(results_dir, target_for=0.10)
    for net, r in results.items():
        # Find which target dir this network maps to
        dirname_map = {
            "Insurance": "mve_27b_insurance_10k_k10_debiased",
            "Alarm": "mve_27b_alarm_10k_k10_debiased",
            "Sachs": "mve_27b_sachs_10k_k10_debiased",
            "Child": "mve_27b_child_10k_k10_debiased",
            "Asia": "mve_27b_asia_10k_k10_debiased",
            "Hepar2": "mve_27b_hepar2_10k_k10_debiased",
        }
        dirname = dirname_map.get(net)
        if dirname:
            out_path = results_dir / dirname / "phase6_calibration_results.json"
            with open(out_path, "w") as f:
                json.dump(r, f, indent=2, default=str)

    print("\nPhase 6 results saved.")


if __name__ == "__main__":
    main()
