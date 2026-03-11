"""
Comprehensive comparison across all LOCALE experiments.

Generates summary tables comparing accuracy, CI violations, vote unanimity,
and cost metrics across all networks, conditions, and prompt variants.
"""

import json
from collections import Counter
from pathlib import Path


RESULTS_DIR = Path("projects/locale/experiments/results")

# All experiment configurations to check
EXPERIMENTS = {
    # (label, directory)
    "Insurance NT":        "mve_27b_disguised",
    "Insurance Think":     "mve_27b_think_insurance",
    "Insurance v2":        "mve_27b_insurance_v2",
    "Insurance TempLad":   "mve_27b_insurance_templad",
    "Alarm NT":            "mve_27b_alarm_disguised",
    "Alarm Think":         "mve_27b_think_alarm",
    "Alarm v2":            "mve_27b_alarm_v2",
    "Sachs NT":            "mve_27b_sachs_disguised",
    "Child NT":            "mve_27b_child_disguised",
    "Insurance Contr":     "mve_27b_insurance_contrastive",
    "Alarm Contr":         "mve_27b_alarm_contrastive",
    "Alarm Enriched":      "mve_27b_enriched_alarm",
    "Insurance Full":      "mve_27b_insurance_full",
    "Alarm Full":          "mve_27b_alarm_full",
    "Sachs Full":          "mve_27b_sachs_full",
    "Child Full":          "mve_27b_child_full",
}


def load_results(path):
    with open(path) as f:
        return json.load(f)


def majority_vote(votes):
    filtered = [v for v in votes if v not in ("uncertain", "")]
    if not filtered:
        return "uncertain"
    return Counter(filtered).most_common(1)[0][0]


def analyze_experiment(data):
    """Extract all metrics from a single experiment."""
    meta = data.get("metadata", {})
    summary = data.get("summary", {})

    # Recompute majority vote
    pe_votes = {}
    ego_votes = {}
    gt_map = {}
    degrees = {}

    for node, info in data.get("per_node", {}).items():
        degrees[node] = info["degree"]

    for r in data.get("raw_results_a", []):
        key = (r["center_node"], tuple(sorted(r["edge"])))
        pe_votes.setdefault(key, []).append(r["predicted"])
        gt_map[key] = f"{r['edge'][0]}->{r['edge'][1]}"

    for r in data.get("raw_results_b", []):
        key = (r["center_node"], tuple(sorted(r["edge"])))
        ego_votes.setdefault(key, []).append(r["predicted"])
        gt_map[key] = f"{r['edge'][0]}->{r['edge'][1]}"

    all_keys = sorted(set(list(pe_votes.keys()) + list(ego_votes.keys())))
    n_edges = len(all_keys)

    # PE majority
    pe_maj = sum(1 for k in all_keys
                 if k in pe_votes and majority_vote(pe_votes[k]) == gt_map[k])

    # Ego majority
    ego_maj = sum(1 for k in all_keys
                  if k in ego_votes and majority_vote(ego_votes[k]) == gt_map[k])

    # Hybrid (ego d>=3, PE d<3)
    hybrid = 0
    for k in all_keys:
        deg = degrees.get(k[0], 0)
        if deg >= 3 and k in ego_votes:
            pred = majority_vote(ego_votes[k])
        elif k in pe_votes:
            pred = majority_vote(pe_votes[k])
        else:
            pred = "uncertain"
        if pred == gt_map[k]:
            hybrid += 1

    # Oracle
    oracle = 0
    for k in all_keys:
        pe_pred = majority_vote(pe_votes.get(k, []))
        ego_pred = majority_vote(ego_votes.get(k, []))
        if pe_pred == gt_map[k] or ego_pred == gt_map[k]:
            oracle += 1

    # Unanimity
    pe_unan = sum(1 for k in all_keys if k in pe_votes and
                  len(set(v for v in pe_votes[k] if v not in ("uncertain", ""))) <= 1)
    ego_unan = sum(1 for k in all_keys if k in ego_votes and
                   len(set(v for v in ego_votes[k] if v not in ("uncertain", ""))) <= 1)

    # Both-wrong count (systematic errors)
    both_wrong = 0
    for k in all_keys:
        pe_pred = majority_vote(pe_votes.get(k, []))
        ego_pred = majority_vote(ego_votes.get(k, []))
        if pe_pred != gt_map[k] and ego_pred != gt_map[k]:
            both_wrong += 1

    return {
        "network": meta.get("network") or "unknown",
        "thinking": meta.get("enable_thinking", False),
        "n_edges": n_edges,
        "pe_raw": summary.get("acc_per_edge", 0),
        "ego_raw": summary.get("acc_ego_graph", 0),
        "pe_maj": pe_maj / max(n_edges, 1),
        "ego_maj": ego_maj / max(n_edges, 1),
        "hybrid": hybrid / max(n_edges, 1),
        "oracle": oracle / max(n_edges, 1),
        "pe_unan": pe_unan / max(n_edges, 1),
        "ego_unan": ego_unan / max(n_edges, 1),
        "both_wrong": both_wrong,
        "unc_pe": summary.get("uncertain_per_edge", 0),
        "unc_ego": summary.get("uncertain_ego_graph", 0),
    }


def main():
    found = {}
    for label, dirname in EXPERIMENTS.items():
        path = RESULTS_DIR / dirname / "mve_results.json"
        if path.exists():
            try:
                data = load_results(str(path))
                metrics = analyze_experiment(data)
                # Infer network from label if not in metadata
                if metrics["network"] == "unknown":
                    for net in ["insurance", "alarm", "sachs", "child"]:
                        if net in label.lower():
                            metrics["network"] = net
                            break
                found[label] = metrics
            except Exception as e:
                print(f"Error loading {label}: {e}")

    if not found:
        print("No results found.")
        return

    # Main comparison table
    print(f"\n{'='*100}")
    print("LOCALE Experiment Comparison — All Networks & Conditions")
    print(f"{'='*100}")
    print(f"{'Experiment':<22} {'N':>3} {'PE raw':>7} {'Ego raw':>8} {'PE maj':>7} {'Ego maj':>8} {'Hybrid':>7} {'Oracle':>7} {'BothWr':>7}")
    print("-" * 100)
    for label, m in sorted(found.items()):
        print(f"{label:<22} {m['n_edges']:>3} {m['pe_raw']:>6.1%} {m['ego_raw']:>7.1%} "
              f"{m['pe_maj']:>6.1%} {m['ego_maj']:>7.1%} {m['hybrid']:>6.1%} {m['oracle']:>6.1%} "
              f"{m['both_wrong']:>5}/{m['n_edges']}")

    # Unanimity table
    print(f"\n{'Experiment':<22} {'PE unan':>8} {'Ego unan':>9} {'Unc PE':>7} {'Unc Ego':>8}")
    print("-" * 60)
    for label, m in sorted(found.items()):
        print(f"{label:<22} {m['pe_unan']:>7.0%} {m['ego_unan']:>8.0%} "
              f"{m['unc_pe']:>6.1%} {m['unc_ego']:>7.1%}")

    # Cross-network summary (group by network)
    networks = {}
    for label, m in found.items():
        net = m["network"]
        networks.setdefault(net, []).append((label, m))

    print(f"\n{'='*60}")
    print("Per-Network Best Results")
    print(f"{'='*60}")
    for net, entries in sorted(networks.items()):
        best_hybrid = max(entries, key=lambda x: x[1]["hybrid"])
        best_ego_maj = max(entries, key=lambda x: x[1]["ego_maj"])
        print(f"\n{net.title()}:")
        print(f"  Best hybrid:   {best_hybrid[0]} ({best_hybrid[1]['hybrid']:.1%})")
        print(f"  Best ego maj:  {best_ego_maj[0]} ({best_ego_maj[1]['ego_maj']:.1%})")
        print(f"  Oracle ceil:   {best_hybrid[1]['oracle']:.1%}")


if __name__ == "__main__":
    main()
