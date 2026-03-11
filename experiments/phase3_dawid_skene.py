"""
Phase 3: Dawid-Skene Reconciliation (Proposal v2 Section 4.5)

Replaces simplified confidence-weighted reconciliation with proper
Dawid-Skene EM algorithm treating each ego-graph endpoint as an
annotator with latent error rates.

Label space per edge (u,v): {u->v, v->u, ?}
Annotators: each (endpoint_node, pass_idx) combination.

The proposal mandates:
- Multiclass Dawid-Skene as full-sweep backbone
- EBCC/BCC dependence-aware analysis on confirmatory subset (Phase 3b)
- Edge-difficulty features for downstream calibration
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict


def extract_annotations(data, source="ego", aggregation="per_pass"):
    """Extract per-edge annotations from Phase 1 results.

    For each unique edge, collects all votes from both endpoints.

    Args:
        aggregation: "per_pass" = each (node, pass) is an annotator
                     "per_node" = each node is an annotator, using majority vote of K passes

    Returns:
        edges: list of (u, v) tuples (sorted)
        annotations: dict edge_key -> list of {annotator, label}
        gt_directions: dict edge_key -> ground truth direction string
    """
    raw_key = "raw_results_b" if source == "ego" else "raw_results_a"
    raw = data.get(raw_key, [])
    per_node = data.get("per_node", {})

    # Collect ground truth
    gt_directions = {}
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            edge_key = tuple(sorted([e[0], e[1]]))
            gt_directions[edge_key] = f"{e[0]}->{e[1]}"

    if aggregation == "per_pass":
        # Each (node, pass) is an annotator
        annotations = defaultdict(list)
        for r in raw:
            edge_key = tuple(sorted(r["edge"]))
            center = r["center_node"]
            pass_idx = r.get("pass_idx", 0)
            predicted = r["predicted"]
            annotator_id = f"{center}_k{pass_idx}"

            u, v = edge_key
            if predicted == f"{u}->{v}":
                label = 0
            elif predicted == f"{v}->{u}":
                label = 1
            else:
                parts = predicted.split("->")
                if len(parts) == 2:
                    label = 0 if parts[0] == u else 1
                else:
                    label = 2

            annotations[edge_key].append({
                "annotator": annotator_id,
                "label": label,
                "center": center,
                "pass_idx": pass_idx,
            })
    else:
        # Per-node aggregation: each node votes once per edge (majority of K passes)
        # First collect all votes per (edge, center)
        vote_counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for r in raw:
            edge_key = tuple(sorted(r["edge"]))
            center = r["center_node"]
            predicted = r["predicted"]
            u, v = edge_key
            if predicted == f"{u}->{v}":
                vote_counts[edge_key][center][0] += 1
            elif predicted == f"{v}->{u}":
                vote_counts[edge_key][center][1] += 1
            else:
                parts = predicted.split("->")
                if len(parts) == 2:
                    if parts[0] == u:
                        vote_counts[edge_key][center][0] += 1
                    else:
                        vote_counts[edge_key][center][1] += 1

        annotations = defaultdict(list)
        for edge_key, centers in vote_counts.items():
            for center, counts in centers.items():
                label = 0 if counts[0] >= counts[1] else 1
                margin = abs(counts[0] - counts[1]) / max(sum(counts), 1)
                annotations[edge_key].append({
                    "annotator": center,
                    "label": label,
                    "center": center,
                    "margin": margin,
                    "votes": counts,
                })

    return list(gt_directions.keys()), annotations, gt_directions


def dawid_skene_em(annotations, n_classes=3, n_iter=50, tol=1e-4):
    """Run Dawid-Skene EM to infer true labels from noisy annotations.

    Args:
        annotations: dict edge_key -> list of {annotator, label}
        n_classes: number of label classes (default 3: u->v, v->u, ?)
        n_iter: max EM iterations
        tol: convergence tolerance on label posterior change

    Returns:
        posteriors: dict edge_key -> np.array of shape (n_classes,)
        error_rates: dict annotator -> np.array of shape (n_classes, n_classes)
            error_rates[j][true_class, observed_class] = P(observe c | true t, annotator j)
        class_priors: np.array of shape (n_classes,)
    """
    edges = list(annotations.keys())
    n_items = len(edges)

    # Collect all annotator IDs
    all_annotators = set()
    for edge_key, annots in annotations.items():
        for a in annots:
            all_annotators.add(a["annotator"])
    annotators = sorted(all_annotators)
    ann_idx = {a: i for i, a in enumerate(annotators)}
    n_annotators = len(annotators)

    # Initialize: majority vote posteriors
    posteriors = {}
    for edge_key, annots in annotations.items():
        votes = np.zeros(n_classes)
        for a in annots:
            if a["label"] < n_classes:
                votes[a["label"]] += 1
        total = votes.sum()
        if total > 0:
            posteriors[edge_key] = votes / total
        else:
            posteriors[edge_key] = np.ones(n_classes) / n_classes

    # Initialize class priors
    class_priors = np.ones(n_classes) / n_classes

    # Initialize error rates: slightly better than random
    error_rates = {}
    for ann in annotators:
        # Start with 70% accuracy, 30% spread across other classes
        mat = np.full((n_classes, n_classes), 0.3 / (n_classes - 1))
        np.fill_diagonal(mat, 0.7)
        error_rates[ann] = mat

    for iteration in range(n_iter):
        old_posteriors = {k: v.copy() for k, v in posteriors.items()}

        # M-step: update error rates and class priors
        # Error rates: for each annotator j, compute
        # pi_j[t,c] = sum_i T_i[t] * I(y_ij == c) / sum_i T_i[t]
        for ann in annotators:
            numerator = np.zeros((n_classes, n_classes))
            denominator = np.zeros(n_classes)

            for edge_key, annots in annotations.items():
                T = posteriors[edge_key]
                for a in annots:
                    if a["annotator"] != ann:
                        continue
                    c = a["label"]
                    if c >= n_classes:
                        continue
                    for t in range(n_classes):
                        numerator[t, c] += T[t]
                        denominator[t] += T[t]

            # Normalize with smoothing
            for t in range(n_classes):
                denom = denominator[t] + 1e-10
                for c in range(n_classes):
                    error_rates[ann][t, c] = (numerator[t, c] + 1e-6) / denom

            # Normalize rows to sum to 1
            for t in range(n_classes):
                row_sum = error_rates[ann][t].sum()
                if row_sum > 0:
                    error_rates[ann][t] /= row_sum

        # Update class priors
        prior_sum = np.zeros(n_classes)
        for edge_key in edges:
            prior_sum += posteriors[edge_key]
        class_priors = prior_sum / n_items
        class_priors = np.maximum(class_priors, 1e-10)
        class_priors /= class_priors.sum()

        # E-step: update posteriors
        for edge_key, annots in annotations.items():
            log_post = np.log(class_priors + 1e-30)

            for a in annots:
                c = a["label"]
                if c >= n_classes:
                    continue
                ann = a["annotator"]
                for t in range(n_classes):
                    log_post[t] += np.log(error_rates[ann][t, c] + 1e-30)

            # Normalize in log space
            log_post -= log_post.max()
            post = np.exp(log_post)
            post /= post.sum()
            posteriors[edge_key] = post

        # Check convergence
        max_change = 0
        for edge_key in edges:
            change = np.max(np.abs(posteriors[edge_key] - old_posteriors[edge_key]))
            max_change = max(max_change, change)

        if max_change < tol:
            break

    return posteriors, error_rates, class_priors


def compute_edge_features(edge_key, annotations_for_edge, posteriors,
                          per_node, phase2_results=None):
    """Compute edge-difficulty features for downstream calibration.

    Features from proposal v2 section 4.5:
    - endpoint disagreement
    - local-solver margin
    - node degree / hub status
    - sepset size and instability
    - decision source (hard CI, local solve, propagation, fallback)
    """
    u, v = edge_key

    # Endpoint disagreement: do the two endpoints' majority votes agree?
    endpoint_votes = defaultdict(lambda: np.zeros(2))  # center -> [u->v, v->u]
    for a in annotations_for_edge:
        center = a["center"]
        label = a["label"]
        if label < 2:
            endpoint_votes[center][label] += 1

    endpoint_dirs = {}
    for center, votes in endpoint_votes.items():
        if votes.sum() > 0:
            endpoint_dirs[center] = int(np.argmax(votes))

    disagree = len(set(endpoint_dirs.values())) > 1 if len(endpoint_dirs) > 1 else False

    # Margin: confidence from DS posterior
    post = posteriors[edge_key]
    sorted_post = sorted(post[:2], reverse=True)  # ignore abstain class
    margin = sorted_post[0] - sorted_post[1] if len(sorted_post) > 1 else sorted_post[0]

    # Degree
    u_degree = per_node.get(u, {}).get("degree", 0)
    v_degree = per_node.get(v, {}).get("degree", 0)
    max_degree = max(u_degree, v_degree)
    min_degree = min(u_degree, v_degree)

    # N annotations
    n_annotations = len(annotations_for_edge)

    # DS posterior entropy
    p = post[post > 0]
    entropy = -np.sum(p * np.log2(p))

    return {
        "endpoint_disagreement": disagree,
        "ds_margin": float(margin),
        "ds_entropy": float(entropy),
        "max_degree": max_degree,
        "min_degree": min_degree,
        "n_annotations": n_annotations,
        "ds_posterior": [float(x) for x in post],
    }


def run_phase3_ds(results_path, source="ego", n_classes=2):
    """Run Dawid-Skene Phase 3 on Phase 1 results.

    Args:
        results_path: path to mve_results.json
        source: "ego" or "pe" for which votes to use
        n_classes: 2 (direction only) or 3 (direction + abstain)

    Returns:
        dict with reconciled edges, DS posteriors, error rates, features
    """
    with open(results_path) as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    per_node = data.get("per_node", {})

    # Try both per-pass and per-node aggregation
    edges_pp, annot_pp, gt_directions = extract_annotations(data, source=source, aggregation="per_pass")
    edges_pn, annot_pn, _ = extract_annotations(data, source=source, aggregation="per_node")

    annotations = annot_pn  # Use per-node by default (each node = 1 annotator)
    edges = edges_pn if edges_pn else edges_pp

    if not annotations:
        return None

    # For 2-class mode, filter out abstain annotations
    if n_classes == 2:
        filtered = {}
        for edge_key, annots in annotations.items():
            filtered[edge_key] = [a for a in annots if a["label"] < 2]
        annotations = filtered

    # Run Dawid-Skene EM
    posteriors, error_rates, class_priors = dawid_skene_em(
        annotations, n_classes=n_classes
    )

    # Derive reconciled directions
    reconciled = {}
    for edge_key in edges:
        u, v = edge_key
        default = np.ones(n_classes) / n_classes
        post = posteriors.get(edge_key, default)

        # Direction is the higher-posterior class
        if post[0] >= post[1]:
            direction = f"{u}->{v}"
            confidence = float(post[0])
        else:
            direction = f"{v}->{u}"
            confidence = float(post[1])

        # Edge features
        features = compute_edge_features(
            edge_key, annotations.get(edge_key, []),
            posteriors, per_node
        )

        reconciled[str(edge_key)] = {
            "direction": direction,
            "confidence": confidence,
            "ds_posterior": [float(x) for x in post],
            "method": "dawid_skene",
            "features": features,
        }

    # Evaluate against ground truth
    correct = 0
    total = 0
    by_confidence = {"high": [0, 0], "medium": [0, 0], "low": [0, 0]}

    for edge_key in edges:
        gt = gt_directions.get(edge_key)
        if gt is None:
            continue
        total += 1
        pred = reconciled[str(edge_key)]["direction"]
        conf = reconciled[str(edge_key)]["confidence"]
        is_correct = pred == gt
        if is_correct:
            correct += 1

        # Stratify by confidence
        if conf >= 0.8:
            tier = "high"
        elif conf >= 0.6:
            tier = "medium"
        else:
            tier = "low"
        by_confidence[tier][0] += 1 if is_correct else 0
        by_confidence[tier][1] += 1

    # Compute majority vote baseline using ALL per-pass votes (K passes per endpoint)
    mv_correct = 0
    for edge_key in edges:
        gt = gt_directions.get(edge_key)
        if gt is None:
            continue
        annots = annot_pp.get(edge_key, [])
        votes = np.zeros(2)
        for a in annots:
            if a["label"] < 2:
                votes[a["label"]] += 1
        u, v = edge_key
        if votes[0] >= votes[1]:
            mv_dir = f"{u}->{v}"
        else:
            mv_dir = f"{v}->{u}"
        if mv_dir == gt:
            mv_correct += 1

    # Summarize annotator reliability
    annotator_summary = {}
    for ann, rates in error_rates.items():
        diagonal = [float(rates[i, i]) for i in range(min(rates.shape))]
        annotator_summary[ann] = {
            "accuracy_per_class": diagonal,
            "mean_accuracy": float(np.mean(diagonal[:2])),  # ignore abstain class
        }

    # Sort annotators by reliability
    sorted_anns = sorted(annotator_summary.items(),
                        key=lambda x: x[1]["mean_accuracy"], reverse=True)

    result = {
        "metadata": {
            "phase": 3,
            "method": "dawid_skene",
            "source": source,
            "network": meta.get("network", "unknown"),
            "n_edges": len(edges),
            "n_annotators": len(error_rates),
            "n_em_classes": n_classes,
        },
        "evaluation": {
            "ds_accuracy": correct / max(total, 1),
            "ds_correct": correct,
            "mv_accuracy": mv_correct / max(total, 1),
            "mv_correct": mv_correct,
            "total": total,
            "delta_pp": round((correct - mv_correct) / max(total, 1) * 100, 1),
            "by_confidence": {
                tier: {
                    "correct": counts[0],
                    "total": counts[1],
                    "accuracy": counts[0] / max(counts[1], 1),
                }
                for tier, counts in by_confidence.items()
            },
        },
        "class_priors": [float(x) for x in class_priors],
        "top_annotators": [
            {"annotator": ann, **stats}
            for ann, stats in sorted_anns[:10]
        ],
        "worst_annotators": [
            {"annotator": ann, **stats}
            for ann, stats in sorted_anns[-5:]
        ],
        "reconciled": reconciled,
    }

    return result


def main():
    """Run DS Phase 3 on all available K=10 debiased results."""
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_10k_k10_debiased"),
        ("Alarm", "mve_27b_alarm_10k_k10_debiased"),
        ("Sachs", "mve_27b_sachs_10k_k10_debiased"),
        ("Child", "mve_27b_child_10k_k10_debiased"),
        ("Asia", "mve_27b_asia_10k_k10_debiased"),
        ("Hepar2", "mve_27b_hepar2_10k_k10_debiased"),
    ]

    print("=" * 70)
    print("LOCALE Phase 3: Dawid-Skene Reconciliation")
    print("=" * 70)

    summary_rows = []

    for label, dirname in targets:
        path = results_dir / dirname / "mve_results.json"
        if not path.exists():
            print(f"\n{label}: SKIP (no results)")
            continue

        result = run_phase3_ds(str(path), source="ego", n_classes=2)
        if result is None:
            print(f"\n{label}: SKIP (no annotations)")
            continue

        ev = result["evaluation"]
        print(f"\n{'='*50}")
        print(f"{label}")
        print(f"{'='*50}")
        print(f"  Edges: {result['metadata']['n_edges']}")
        print(f"  Annotators: {result['metadata']['n_annotators']}")
        print(f"  Majority vote:  {ev['mv_correct']}/{ev['total']} ({ev['mv_accuracy']:.1%})")
        print(f"  Dawid-Skene:    {ev['ds_correct']}/{ev['total']} ({ev['ds_accuracy']:.1%})")
        print(f"  Delta: {ev['delta_pp']:+.1f}pp")

        print(f"\n  By confidence tier:")
        for tier in ["high", "medium", "low"]:
            t = ev["by_confidence"][tier]
            if t["total"] > 0:
                print(f"    {tier:8s}: {t['correct']}/{t['total']} ({t['accuracy']:.1%})")

        print(f"\n  Class priors: {result['class_priors']}")

        # Top/worst annotators
        print(f"\n  Most reliable annotators:")
        for a in result["top_annotators"][:3]:
            print(f"    {a['annotator']}: mean_acc={a['mean_accuracy']:.3f}")
        print(f"  Least reliable annotators:")
        for a in result["worst_annotators"][:3]:
            print(f"    {a['annotator']}: mean_acc={a['mean_accuracy']:.3f}")

        summary_rows.append({
            "network": label,
            "mv_acc": ev["mv_accuracy"] * 100,
            "ds_acc": ev["ds_accuracy"] * 100,
            "delta": ev["delta_pp"],
            "n_edges": ev["total"],
        })

        # Save
        out_path = results_dir / dirname / "phase3_ds_results.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n  Saved to {out_path}")

    # Summary
    if summary_rows:
        print(f"\n{'='*70}")
        print("SUMMARY: Dawid-Skene vs Majority Vote")
        print(f"{'='*70}")
        print(f"{'Network':<12} {'Edges':>6} {'MV Acc':>8} {'DS Acc':>8} {'Delta':>8}")
        for r in summary_rows:
            print(f"{r['network']:<12} {r['n_edges']:>6} {r['mv_acc']:>7.1f}% {r['ds_acc']:>7.1f}% {r['delta']:>+7.1f}pp")


if __name__ == "__main__":
    main()
