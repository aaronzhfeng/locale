"""
Phase 2 Failure Diagnosis

Investigate WHY Phase 2 CI constraints hurt accuracy on 3/6 networks
(Sachs, Asia, Hepar2). Analyze:
1. CI fact correctness (are the CI constraints from PC algorithm correct?)
2. Hard flip analysis (which flips help vs hurt, and why?)
3. Constraint density vs damage correlation
4. Node-level predictors of Phase 2 success/failure
"""

import json
from pathlib import Path
from collections import defaultdict

from phase2_max2sat import run_phase2, votes_to_soft_scores, extract_hard_constraints


def diagnose_network(results_path):
    """Full Phase 2 diagnosis for a single network."""
    with open(results_path) as f:
        data = json.load(f)

    per_node = data.get("per_node", {})
    raw_ego = data.get("raw_results_b", [])
    meta = data.get("metadata", {})

    # Run Phase 2 to get detailed per-node results
    p2 = run_phase2(results_path, use_pe=False)

    diagnosis = {
        "network": meta.get("network", "unknown"),
        "ci_fact_analysis": {},
        "hard_flip_details": [],
        "per_node_damage": [],
        "constraint_density": {},
    }

    total_ci_facts = 0
    correct_ci_facts = 0
    total_hard_flips = 0
    helpful_flips = 0
    harmful_flips = 0

    for node, info in per_node.items():
        degree = info.get("degree", 0)
        if degree < 2 or degree > 12:
            continue

        ci_facts = info.get("ci_facts", [])
        neighbors = info.get("neighbors", [])
        gt_edges = info.get("gt_edges", [])

        # Build GT map
        gt_map = {}
        for e in gt_edges:
            u, v = e
            gt_map[v if u == node else u] = f"{u}->{v}"

        # --- 1. CI Fact Correctness ---
        # Check if each CI fact (collider/non-collider) is actually correct
        for fact in ci_facts:
            total_ci_facts += 1
            n1, n2 = fact["pair"]

            # Ground truth: are both n1->node and n2->node? (collider)
            gt_n1 = gt_map.get(n1)
            gt_n2 = gt_map.get(n2)

            if gt_n1 and gt_n2:
                gt_n1_toward = gt_n1 == f"{n1}->{node}"
                gt_n2_toward = gt_n2 == f"{n2}->{node}"
                gt_is_collider = gt_n1_toward and gt_n2_toward

                if (fact["type"] == "collider" and gt_is_collider) or \
                   (fact["type"] == "non-collider" and not gt_is_collider):
                    correct_ci_facts += 1
                    fact_correct = True
                else:
                    fact_correct = False

                diagnosis["hard_flip_details"].append({
                    "node": node,
                    "degree": degree,
                    "pair": fact["pair"],
                    "ci_type": fact["type"],
                    "gt_is_collider": gt_is_collider,
                    "fact_correct": fact_correct,
                })

        # --- 2. Per-Node Phase 2 Damage ---
        p2_node = p2["per_node"].get(node, {})
        p1_correct = p2_node.get("p1_correct", 0)
        p2_correct = p2_node.get("p2_correct", 0)
        n_edges = p2_node.get("n_edges", 0)
        n_constraints = len(ci_facts)
        n_feasible = p2_node.get("n_feasible", 0)
        n_total = p2_node.get("n_total", 0)

        if n_edges > 0:
            delta = p2_correct - p1_correct
            diagnosis["per_node_damage"].append({
                "node": node,
                "degree": degree,
                "n_constraints": n_constraints,
                "n_feasible": n_feasible,
                "n_total": n_total,
                "feasibility_ratio": n_feasible / n_total if n_total > 0 else 0,
                "p1_correct": p1_correct,
                "p2_correct": p2_correct,
                "n_edges": n_edges,
                "delta": delta,
                "hard_flips": p2_node.get("hard_flips", []),
            })

        # --- 3. Hard Flip Details ---
        for nbr, from_val, to_val in p2_node.get("hard_flips", []):
            total_hard_flips += 1
            if nbr in gt_map:
                gt_dir = gt_map[nbr]
                directions = p2_node.get("directions", {})
                p2_dir = directions.get(nbr, "")

                soft_scores = votes_to_soft_scores(raw_ego, node, [nbr])
                s_toward, s_away = soft_scores.get(nbr, (0.5, 0.5))
                p1_dir = f"{nbr}->{node}" if s_toward > s_away else f"{node}->{nbr}"

                if p2_dir == gt_dir and p1_dir != gt_dir:
                    helpful_flips += 1
                elif p2_dir != gt_dir and p1_dir == gt_dir:
                    harmful_flips += 1

    diagnosis["ci_fact_analysis"] = {
        "total": total_ci_facts,
        "correct": correct_ci_facts,
        "accuracy": correct_ci_facts / max(total_ci_facts, 1) * 100,
    }

    diagnosis["hard_flip_summary"] = {
        "total": total_hard_flips,
        "helpful": helpful_flips,
        "harmful": harmful_flips,
        "net_effect": helpful_flips - harmful_flips,
    }

    return diagnosis


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance", "mve_27b_insurance_full"),
        ("Alarm", "mve_27b_alarm_full"),
        ("Sachs", "mve_27b_sachs_full"),
        ("Child", "mve_27b_child_full"),
        ("Asia", "mve_27b_asia_full"),
        ("Hepar2", "mve_27b_hepar2_full"),
    ]

    print("=" * 90)
    print("PHASE 2 FAILURE DIAGNOSIS")
    print("=" * 90)

    all_diagnoses = []

    for label, dirname in targets:
        p1_path = results_dir / dirname / "mve_results.json"
        if not p1_path.exists():
            continue

        diag = diagnose_network(str(p1_path))
        diag["label"] = label
        all_diagnoses.append(diag)

        ci = diag["ci_fact_analysis"]
        hf = diag["hard_flip_summary"]

        print(f"\n{'='*70}")
        print(f"{label}")
        print(f"{'='*70}")

        # CI fact correctness
        print(f"\n  CI Fact Correctness: {ci['correct']}/{ci['total']} ({ci['accuracy']:.1f}%)")

        # Hard flip summary
        print(f"  Hard Flips: {hf['total']} total, {hf['helpful']} helpful, {hf['harmful']} harmful "
              f"(net: {hf['net_effect']:+d})")

        # Per-node damage breakdown
        damaged = [n for n in diag["per_node_damage"] if n["delta"] < 0]
        helped = [n for n in diag["per_node_damage"] if n["delta"] > 0]
        unchanged = [n for n in diag["per_node_damage"] if n["delta"] == 0]

        print(f"\n  Per-Node Impact:")
        print(f"    Helped: {len(helped)} nodes ({sum(n['delta'] for n in helped):+d} edges)")
        print(f"    Hurt:   {len(damaged)} nodes ({sum(n['delta'] for n in damaged):+d} edges)")
        print(f"    Same:   {len(unchanged)} nodes")

        # Damaged node details
        if damaged:
            print(f"\n  Damaged Nodes:")
            for n in sorted(damaged, key=lambda x: x["delta"]):
                feas_pct = n["feasibility_ratio"] * 100
                print(f"    {n['node']:>20s} d={n['degree']} constraints={n['n_constraints']} "
                      f"feasible={n['n_feasible']}/{n['n_total']} ({feas_pct:.0f}%) "
                      f"P1={n['p1_correct']}/{n['n_edges']} P2={n['p2_correct']}/{n['n_edges']} "
                      f"delta={n['delta']:+d}")

        # Helped node details
        if helped:
            print(f"\n  Helped Nodes:")
            for n in sorted(helped, key=lambda x: -x["delta"]):
                feas_pct = n["feasibility_ratio"] * 100
                print(f"    {n['node']:>20s} d={n['degree']} constraints={n['n_constraints']} "
                      f"feasible={n['n_feasible']}/{n['n_total']} ({feas_pct:.0f}%) "
                      f"P1={n['p1_correct']}/{n['n_edges']} P2={n['p2_correct']}/{n['n_edges']} "
                      f"delta={n['delta']:+d}")

        # Incorrect CI facts
        wrong_facts = [f for f in diag["hard_flip_details"] if not f["fact_correct"]]
        if wrong_facts:
            print(f"\n  Incorrect CI Facts ({len(wrong_facts)}):")
            for f in wrong_facts:
                print(f"    Node {f['node']} (d={f['degree']}): "
                      f"CI says {f['ci_type']}, GT says "
                      f"{'collider' if f['gt_is_collider'] else 'non-collider'} "
                      f"for pair {f['pair']}")

    # --- Cross-Network Summary ---
    print(f"\n\n{'='*90}")
    print("CROSS-NETWORK SUMMARY")
    print(f"{'='*90}")

    print(f"\n{'Network':<12} {'CI Facts':>10} {'CI Acc':>8} {'Flips':>7} {'Help':>6} {'Hurt':>6} "
          f"{'Net':>5} {'P2 Delta':>10}")
    print("-" * 80)

    for d in all_diagnoses:
        ci = d["ci_fact_analysis"]
        hf = d["hard_flip_summary"]
        # Compute P2 delta from per_node_damage
        total_delta = sum(n["delta"] for n in d["per_node_damage"])
        total_edges = sum(n["n_edges"] for n in d["per_node_damage"])
        delta_pct = total_delta / max(total_edges, 1) * 100

        print(f"{d['label']:<12} {ci['total']:>10} {ci['accuracy']:>7.1f}% "
              f"{hf['total']:>7} {hf['helpful']:>6} {hf['harmful']:>6} "
              f"{hf['net_effect']:>+5d} {delta_pct:>+9.1f}pp")

    # --- Feasibility Analysis ---
    print(f"\n\nFEASIBILITY vs DAMAGE")
    print("-" * 60)
    for d in all_diagnoses:
        low_feas = [n for n in d["per_node_damage"]
                    if n["feasibility_ratio"] < 0.5 and n["n_constraints"] > 0]
        high_feas = [n for n in d["per_node_damage"]
                     if n["feasibility_ratio"] >= 0.5 and n["n_constraints"] > 0]

        if low_feas:
            low_delta = sum(n["delta"] for n in low_feas)
            low_edges = sum(n["n_edges"] for n in low_feas)
            print(f"  {d['label']:<12} Low feasibility (<50%): "
                  f"{len(low_feas)} nodes, delta={low_delta:+d}/{low_edges} edges")
        if high_feas:
            high_delta = sum(n["delta"] for n in high_feas)
            high_edges = sum(n["n_edges"] for n in high_feas)
            print(f"  {d['label']:<12} High feasibility (>=50%): "
                  f"{len(high_feas)} nodes, delta={high_delta:+d}/{high_edges} edges")

    # --- Constraint Density Analysis ---
    print(f"\n\nCONSTRAINT DENSITY vs DAMAGE")
    print("-" * 60)
    for d in all_diagnoses:
        constrained = [n for n in d["per_node_damage"] if n["n_constraints"] > 0]
        unconstrained = [n for n in d["per_node_damage"] if n["n_constraints"] == 0]

        if constrained:
            c_delta = sum(n["delta"] for n in constrained)
            c_edges = sum(n["n_edges"] for n in constrained)
            avg_constraints = sum(n["n_constraints"] for n in constrained) / len(constrained)
            print(f"  {d['label']:<12} With constraints: "
                  f"{len(constrained)} nodes, avg {avg_constraints:.1f} constraints, "
                  f"delta={c_delta:+d}/{c_edges} edges")
        if unconstrained:
            u_delta = sum(n["delta"] for n in unconstrained)
            u_edges = sum(n["n_edges"] for n in unconstrained)
            print(f"  {d['label']:<12} No constraints:   "
                  f"{len(unconstrained)} nodes, delta={u_delta:+d}/{u_edges} edges")


if __name__ == "__main__":
    main()
