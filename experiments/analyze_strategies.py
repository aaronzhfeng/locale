"""
Post-hoc analysis of orientation strategies using existing MVE results.

Computes accuracy of different voting/ensemble strategies without requiring
new LLM queries. Works on saved JSON results from mve_insurance.py.
"""

import json
import sys
from collections import Counter
from pathlib import Path


def load_results(path):
    """Load results from a JSON file."""
    with open(path) as f:
        return json.load(f)


def get_ground_truth(raw_results):
    """Extract ground truth directions from raw results."""
    gt = {}
    for r in raw_results:
        key = (r['center_node'], tuple(sorted(r['edge'])))
        gt[key] = f"{r['edge'][0]}->{r['edge'][1]}"
    return gt


def majority_vote(votes):
    """Return majority vote prediction."""
    if not votes:
        return "uncertain"
    filtered = [v for v in votes if v != "uncertain" and v != ""]
    if not filtered:
        return "uncertain"
    return Counter(filtered).most_common(1)[0][0]


def analyze_file(path, label=""):
    """Analyze a single results file with multiple strategies."""
    d = load_results(path)

    # Group votes by (center_node, edge_key)
    pe_votes = {}   # key -> [predictions]
    ego_votes = {}  # key -> [predictions]
    gt_map = {}     # key -> ground_truth

    for r in d['raw_results_a']:
        key = (r['center_node'], tuple(sorted(r['edge'])))
        pe_votes.setdefault(key, []).append(r['predicted'])
        gt_map[key] = f"{r['edge'][0]}->{r['edge'][1]}"

    for r in d['raw_results_b']:
        key = (r['center_node'], tuple(sorted(r['edge'])))
        ego_votes.setdefault(key, []).append(r['predicted'])
        gt_map[key] = f"{r['edge'][0]}->{r['edge'][1]}"

    # Get degree info
    degrees = {}
    for node, info in d['per_node'].items():
        degrees[node] = info['degree']

    all_keys = sorted(set(list(pe_votes.keys()) + list(ego_votes.keys())))
    n_edges = len(all_keys)

    strategies = {}

    # 1. Pure PE majority vote
    pe_correct = sum(1 for k in all_keys
                     if k in pe_votes and majority_vote(pe_votes[k]) == gt_map[k])
    strategies['PE majority'] = pe_correct

    # 2. Pure Ego majority vote
    ego_correct = sum(1 for k in all_keys
                      if k in ego_votes and majority_vote(ego_votes[k]) == gt_map[k])
    strategies['Ego majority'] = ego_correct

    # 3. Hybrid (ego d>=3, PE d<3)
    hybrid_correct = 0
    for k in all_keys:
        node = k[0]
        deg = degrees[node]
        if deg >= 3 and k in ego_votes:
            pred = majority_vote(ego_votes[k])
        elif k in pe_votes:
            pred = majority_vote(pe_votes[k])
        else:
            pred = "uncertain"
        if pred == gt_map[k]:
            hybrid_correct += 1
    strategies['Hybrid (ego d>=3)'] = hybrid_correct

    # 4. Union ensemble (all 10 votes)
    union_correct = 0
    for k in all_keys:
        all_v = pe_votes.get(k, []) + ego_votes.get(k, [])
        if majority_vote(all_v) == gt_map[k]:
            union_correct += 1
    strategies['Union (10 votes)'] = union_correct

    # 5. Weighted ensemble (ego 2x for d>=3, PE 2x for d<3)
    weighted_correct = 0
    for k in all_keys:
        node = k[0]
        deg = degrees[node]
        pe_v = pe_votes.get(k, [])
        ego_v = ego_votes.get(k, [])
        if deg >= 3:
            weighted = pe_v + ego_v * 2
        else:
            weighted = pe_v * 2 + ego_v
        if majority_vote(weighted) == gt_map[k]:
            weighted_correct += 1
    strategies['Weighted (2x ego d>=3)'] = weighted_correct

    # 6. Confidence-filtered: use ego if unanimous, else PE
    conf_correct = 0
    for k in all_keys:
        node = k[0]
        deg = degrees[node]
        ego_v = ego_votes.get(k, [])
        pe_v = pe_votes.get(k, [])

        if ego_v and deg >= 3:
            counts = Counter(v for v in ego_v if v not in ("uncertain", ""))
            if counts and counts.most_common(1)[0][1] >= 4:  # 4/5 or 5/5
                pred = counts.most_common(1)[0][0]
            elif pe_v:
                pred = majority_vote(pe_v)
            else:
                pred = majority_vote(ego_v)
        elif pe_v:
            pred = majority_vote(pe_v)
        else:
            pred = "uncertain"
        if pred == gt_map[k]:
            conf_correct += 1
    strategies['Conf-filtered (ego if 4+/5)'] = conf_correct

    # 7. Agreement-based: use ego when PE agrees (high confidence), else PE
    agree_correct = 0
    agree_total = 0
    disagree_edges = []
    for k in all_keys:
        pe_pred = majority_vote(pe_votes.get(k, []))
        ego_pred = majority_vote(ego_votes.get(k, []))
        gt = gt_map[k]
        if pe_pred == ego_pred and pe_pred != "uncertain":
            # Both agree — high confidence
            pred = pe_pred
        elif ego_pred != "uncertain" and k[0] in degrees and degrees[k[0]] >= 3:
            # Disagree: trust ego for high-degree
            pred = ego_pred
        else:
            pred = pe_pred
        if pred == gt:
            agree_correct += 1
        else:
            disagree_edges.append((k, pe_pred, ego_pred, gt))
    strategies['Agreement-based'] = agree_correct

    # 9. Oracle best per-edge (upper bound)
    oracle_correct = 0
    for k in all_keys:
        pe_pred = majority_vote(pe_votes.get(k, []))
        ego_pred = majority_vote(ego_votes.get(k, []))
        if pe_pred == gt_map[k] or ego_pred == gt_map[k]:
            oracle_correct += 1
    strategies['Oracle (best per edge)'] = oracle_correct

    # Print results
    net = d.get('metadata', {}).get('network', label or path)
    print(f"\n{'='*60}")
    print(f"Strategy Analysis: {net} ({n_edges} edges)")
    print(f"{'='*60}")
    print(f"{'Strategy':<30} {'Correct':>8} {'Accuracy':>10}")
    print("-" * 50)
    for name, correct in strategies.items():
        print(f"{name:<30} {correct:>5}/{n_edges}   {correct/n_edges:>8.1%}")

    # Disagreement analysis
    if disagree_edges:
        print(f"\nDisagreement analysis ({len(disagree_edges)} edges where agreement-based gets wrong):")
        for (node, edge_key), pe_p, ego_p, gt in disagree_edges[:10]:
            edge_str = f"{edge_key[0]}-{edge_key[1]}"
            agree = "AGREE" if pe_p == ego_p else "DISAGREE"
            print(f"  {node}/{edge_str}: PE={pe_p}, Ego={ego_p}, GT={gt} [{agree}]")

    # Per-edge detailed comparison (PE vs Ego majority)
    pe_only = 0  # PE right, ego wrong
    ego_only = 0  # Ego right, PE wrong
    both_right = 0
    both_wrong = 0
    for k in all_keys:
        pe_pred = majority_vote(pe_votes.get(k, []))
        ego_pred = majority_vote(ego_votes.get(k, []))
        gt = gt_map[k]
        pe_ok = pe_pred == gt
        ego_ok = ego_pred == gt
        if pe_ok and ego_ok:
            both_right += 1
        elif pe_ok and not ego_ok:
            pe_only += 1
        elif not pe_ok and ego_ok:
            ego_only += 1
        else:
            both_wrong += 1

    print(f"\nPE vs Ego (majority vote):")
    print(f"  Both right: {both_right}/{n_edges}")
    print(f"  PE only:    {pe_only}/{n_edges}")
    print(f"  Ego only:   {ego_only}/{n_edges}")
    print(f"  Both wrong: {both_wrong}/{n_edges}")

    # Vote distribution analysis — how unanimous are the votes?
    print(f"\nVote unanimity (5/5 agree):")
    for label_cond, votes_dict in [("PE", pe_votes), ("Ego", ego_votes)]:
        unanimous = 0
        total_edges = 0
        for k in all_keys:
            if k in votes_dict:
                total_edges += 1
                v = [x for x in votes_dict[k] if x not in ("uncertain", "")]
                if v and len(set(v)) == 1:
                    unanimous += 1
        print(f"  {label_cond}: {unanimous}/{total_edges} edges unanimous ({100*unanimous/max(total_edges,1):.0f}%)")

    return strategies, n_edges


if __name__ == "__main__":
    results_dir = Path("projects/locale/experiments/results")

    files = {
        "Insurance (27B, disguised)": results_dir / "mve_27b_disguised" / "mve_results.json",
        "Alarm (27B, disguised)": results_dir / "mve_27b_alarm_disguised" / "mve_results.json",
    }

    # Check for thinking mode results
    think_ins = results_dir / "mve_27b_think_insurance" / "mve_results.json"
    if think_ins.exists():
        files["Insurance (27B, thinking)"] = think_ins

    think_alarm = results_dir / "mve_27b_think_alarm" / "mve_results.json"
    if think_alarm.exists():
        files["Alarm (27B, thinking)"] = think_alarm

    for label, path in files.items():
        if path.exists():
            analyze_file(str(path), label)
        else:
            print(f"\nSkipping {label}: {path} not found")

    print()
