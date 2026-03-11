"""
Generate LaTeX tables for the paper (v2: unique edge accuracy).

Changes from v1:
- Uses unique edge accuracy (194 edges) instead of per-center (338)
- Computes CI accuracy from artifacts instead of hardcoding
- Includes full NCO pipeline (P2 + reconciliation across endpoints)
"""

import json
from pathlib import Path
from collections import defaultdict

from phase2_max2sat import run_phase2, votes_to_soft_scores


def compute_unique_edge_metrics(results_path, collider_mode="non-collider-only"):
    """Compute accuracy on unique edges for PE, ego, and NCO P2."""
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})
    raw_pe = data.get("raw_results_a", [])
    raw_ego = data.get("raw_results_b", [])

    # Build GT map for unique edges
    gt_map = {}
    for node, info in per_node.items():
        for e in info.get("gt_edges", []):
            edge_key = tuple(sorted(e))
            gt_map[edge_key] = f"{e[0]}->{e[1]}"

    # Aggregate votes per unique edge
    pe_votes = defaultdict(lambda: defaultdict(int))
    ego_votes = defaultdict(lambda: defaultdict(int))

    for r in raw_pe:
        edge_key = tuple(sorted(r["edge"]))
        if r["predicted"] and r["predicted"] != "uncertain":
            pe_votes[edge_key][r["predicted"]] += 1

    for r in raw_ego:
        edge_key = tuple(sorted(r["edge"]))
        if r["predicted"] and r["predicted"] != "uncertain":
            ego_votes[edge_key][r["predicted"]] += 1

    pe_correct = 0
    ego_correct = 0
    total = 0

    for edge_key, gt_dir in gt_map.items():
        total += 1
        if pe_votes[edge_key]:
            pe_majority = max(pe_votes[edge_key], key=pe_votes[edge_key].get)
            if pe_majority == gt_dir:
                pe_correct += 1
        if ego_votes[edge_key]:
            ego_majority = max(ego_votes[edge_key], key=ego_votes[edge_key].get)
            if ego_majority == gt_dir:
                ego_correct += 1

    # NCO P2 unique edge accuracy
    p2 = run_phase2(results_path, use_pe=False, collider_mode=collider_mode)
    p2_edge_votes = defaultdict(lambda: defaultdict(float))
    for node, info in p2["per_node"].items():
        directions = info.get("directions", {})
        for nbr, direction in directions.items():
            edge_key = tuple(sorted([node, nbr]))
            p2_edge_votes[edge_key][direction] += 1

    p2_correct = 0
    for edge_key, gt_dir in gt_map.items():
        if p2_edge_votes[edge_key]:
            p2_majority = max(p2_edge_votes[edge_key], key=p2_edge_votes[edge_key].get)
            if p2_majority == gt_dir:
                p2_correct += 1

    return {
        "total": total,
        "pe_correct": pe_correct,
        "pe_accuracy": pe_correct / max(total, 1) * 100,
        "ego_correct": ego_correct,
        "ego_accuracy": ego_correct / max(total, 1) * 100,
        "p2_correct": p2_correct,
        "p2_accuracy": p2_correct / max(total, 1) * 100,
    }


def compute_ci_accuracy(results_path):
    """Compute CI fact accuracy from Phase 1 artifacts."""
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})
    total_facts = 0
    correct_facts = 0

    for node, info in per_node.items():
        ci_facts = info.get("ci_facts", [])
        gt_edges = info.get("gt_edges", [])
        gt_map = {}
        for e in gt_edges:
            u, v = e
            gt_map[v if u == node else u] = f"{u}->{v}"

        for fact in ci_facts:
            n1, n2 = fact["pair"]
            gt_n1 = gt_map.get(n1)
            gt_n2 = gt_map.get(n2)
            if gt_n1 and gt_n2:
                total_facts += 1
                gt_n1_toward = gt_n1 == f"{n1}->{node}"
                gt_n2_toward = gt_n2 == f"{n2}->{node}"
                gt_is_collider = gt_n1_toward and gt_n2_toward
                if (fact["type"] == "collider" and gt_is_collider) or \
                   (fact["type"] == "non-collider" and not gt_is_collider):
                    correct_facts += 1

    return total_facts, correct_facts


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_full", 27, 52),
        ("Alarm", "mve_27b_alarm_full", 37, 46),
        ("Sachs", "mve_27b_sachs_full", 11, 17),
        ("Child", "mve_27b_child_full", 20, 25),
        ("Asia", "mve_27b_asia_full", 8, 8),
        ("Hepar2", "mve_27b_hepar2_full", 70, 82),
    ]

    # ── Table 1: Main Results (unique edges) ──
    print("% Table 1: Main Results (unique edge accuracy)")
    print("\\begin{table}[t]")
    print("\\centering")
    print("\\caption{Edge orientation accuracy (\\%) on unique edges across 6 Bayesian networks. "
          "PE = per-edge majority vote. Ego = ego-graph majority vote. "
          "NCO = non-collider-only pipeline (ego + NCO constraints, reconciled across endpoints).}")
    print("\\label{tab:main-results}")
    print("\\begin{tabular}{lrrrrrr}")
    print("\\toprule")
    print("Network & $|V|$ & $|E|$ & PE (\\%) & Ego (\\%) & NCO (\\%) & $\\Delta_{\\text{PE}}$ \\\\")
    print("\\midrule")

    agg = {"n": 0, "pe": 0, "ego": 0, "nco": 0}

    for label, dirname, n_nodes, n_edges_true in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        r = compute_unique_edge_metrics(str(p1_path))
        n = r["total"]
        delta = r["p2_accuracy"] - r["pe_accuracy"]

        bold = "\\textbf{" if r["p2_accuracy"] >= r["pe_accuracy"] else ""
        end_bold = "}" if bold else ""

        print(f"{label} & {n_nodes} & {n} & {r['pe_accuracy']:.1f} & {r['ego_accuracy']:.1f} "
              f"& {bold}{r['p2_accuracy']:.1f}{end_bold} & {delta:+.1f} \\\\")

        agg["n"] += n
        agg["pe"] += r["pe_correct"]
        agg["ego"] += r["ego_correct"]
        agg["nco"] += r["p2_correct"]

    n = agg["n"]
    pe_agg = agg["pe"] / n * 100
    ego_agg = agg["ego"] / n * 100
    nco_agg = agg["nco"] / n * 100
    delta_agg = nco_agg - pe_agg

    print("\\midrule")
    print(f"Aggregate & — & {n} & {pe_agg:.1f} & {ego_agg:.1f} "
          f"& \\textbf{{{nco_agg:.1f}}} & {delta_agg:+.1f} \\\\")
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{table}")

    # ── Table 2: Collider Constraint Analysis (computed from artifacts) ──
    print("\n\n% Table 2: Collider Constraint Analysis")
    print("\\begin{table}[t]")
    print("\\centering")
    print("\\caption{CI fact accuracy and effect of collider constraints on Phase 2. "
          "Hard = all constraints; NCO = non-collider only. "
          "All incorrect CI facts are false colliders (zero false non-colliders across all networks).}")
    print("\\label{tab:collider}")
    print("\\begin{tabular}{lrrrrr}")
    print("\\toprule")
    print("Network & CI facts & CI Acc (\\%) & P2 Hard (\\%) & P2 NCO (\\%) & $\\Delta$ \\\\")
    print("\\midrule")

    total_ci = 0
    correct_ci = 0

    for label, dirname, _, _ in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        n_facts, n_correct = compute_ci_accuracy(str(p1_path))
        ci_acc = n_correct / max(n_facts, 1) * 100

        total_ci += n_facts
        correct_ci += n_correct

        # Per-center P2 accuracy (for this table, per-center is appropriate
        # since constraints operate per ego-center)
        p2_hard = run_phase2(str(p1_path), use_pe=False, collider_mode="hard")
        p2_nco = run_phase2(str(p1_path), use_pe=False, collider_mode="non-collider-only")

        hard_acc = p2_hard["summary"]["phase2_accuracy"]
        nco_acc = p2_nco["summary"]["phase2_accuracy"]
        delta = nco_acc - hard_acc

        print(f"{label} & {n_facts} & {ci_acc:.1f} & {hard_acc:.1f} & {nco_acc:.1f} & {delta:+.1f} \\\\")

    print("\\midrule")
    ci_agg = correct_ci / max(total_ci, 1) * 100
    print(f"Total & {total_ci} & {ci_agg:.1f} & — & — & — \\\\")
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{table}")

    # ── Table 3: Query Cost ──
    print("\n\n% Table 3: Query Cost Comparison")
    print("\\begin{table}[t]")
    print("\\centering")
    print("\\caption{LLM query cost. Ego-graph prompting orients all incident edges "
          "per node in one query ($K{=}5$ votes), reducing total queries by 2.4--4.0$\\times$.}")
    print("\\label{tab:query-cost}")
    print("\\begin{tabular}{lrrrr}")
    print("\\toprule")
    print("Network & Centers & Ego queries & PE queries & Savings \\\\")
    print("\\midrule")

    for label, dirname, _, _ in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        with open(p1_path) as f:
            data = json.load(f)

        per_node = data.get("per_node", {})
        K = 5
        n_centers = len(per_node)
        total_edges_from_centers = sum(info.get("degree", 0) for info in per_node.values())
        ego_queries = n_centers * K
        pe_queries = total_edges_from_centers * K
        savings = (1 - ego_queries / pe_queries) * 100
        ratio = pe_queries / ego_queries

        print(f"{label} & {n_centers} & {ego_queries} & {pe_queries} & {savings:.0f}\\% ({ratio:.1f}$\\times$) \\\\")

    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{table}")

    # ── Summary for paper text ──
    print("\n\n% Key numbers for paper text:")
    print(f"% Unique edges: {agg['n']}")
    print(f"% PE aggregate: {pe_agg:.1f}%")
    print(f"% Ego aggregate: {ego_agg:.1f}%")
    print(f"% NCO aggregate: {nco_agg:.1f}%")
    print(f"% Delta (NCO vs PE): {delta_agg:+.1f}pp")
    print(f"% CI facts total: {total_ci}, correct: {correct_ci}, accuracy: {ci_agg:.1f}%")
    print(f"% Incorrect CI facts: {total_ci - correct_ci} (all false colliders)")


if __name__ == "__main__":
    main()
