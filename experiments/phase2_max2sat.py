"""
Phase 2: Max-2SAT Local Constraint Compilation

Takes Phase 1 LLM orientation votes + CI-derived hard constraints,
solves locally optimal orientations per node via exact enumeration.

For each node v with degree d:
  - Binary variable b[u] = 1 means u -> v (neighbor u points toward v)
  - Hard clauses from CI: collider (both must point in), non-collider (not both point in)
  - Soft objective: maximize sum of LLM vote fractions for chosen directions
  - Exact enumeration for d <= 8 (2^8 = 256 assignments)
"""

import json
import itertools
from collections import Counter
from pathlib import Path


def votes_to_soft_scores(raw_results, node, neighbors):
    """Convert K vote predictions into soft scores s_{u->v} for each edge.

    Returns dict: neighbor -> (score_toward_node, score_away_from_node)
    where score_toward = fraction of votes saying nbr -> node
    """
    scores = {}
    for nbr in neighbors:
        toward = 0  # nbr -> node
        away = 0    # node -> nbr
        total = 0
        for r in raw_results:
            if r["center_node"] != node:
                continue
            edge_set = set(r["edge"])
            if edge_set != {node, nbr}:
                continue
            pred = r["predicted"]
            if pred == f"{nbr}->{node}":
                toward += 1
                total += 1
            elif pred == f"{node}->{nbr}":
                away += 1
                total += 1
            # "uncertain" counts as abstention
        if total > 0:
            scores[nbr] = (toward / total, away / total)
        else:
            scores[nbr] = (0.5, 0.5)  # no information
    return scores


def extract_hard_constraints(ci_facts, node):
    """Extract hard clauses from CI facts for a given center node.

    Returns list of constraints, each is a dict:
      - type: "collider" or "non-collider"
      - pair: (n1, n2) — the two non-adjacent neighbors
      - clauses: list of (variable_assignments) that must hold

    For collider at node v with pair (n1, n2):
      b[n1] = 1 AND b[n2] = 1  (both point toward v)

    For non-collider at node v with pair (n1, n2):
      NOT (b[n1] = 1 AND b[n2] = 1)  (at most one points toward v)
    """
    constraints = []
    for fact in ci_facts:
        n1, n2 = fact["pair"]
        if fact["type"] == "collider":
            # Both must point toward node: b[n1]=1 AND b[n2]=1
            constraints.append({
                "type": "collider",
                "pair": (n1, n2),
                "forced": {n1: 1, n2: 1},  # both toward
            })
        elif fact["type"] == "non-collider":
            # Cannot both point toward node: NOT (b[n1]=1 AND b[n2]=1)
            constraints.append({
                "type": "non-collider",
                "pair": (n1, n2),
                "forbidden": {n1: 1, n2: 1},  # this combo is forbidden
            })
    return constraints


def check_feasibility(assignment, constraints):
    """Check if a binary assignment satisfies all hard constraints.

    assignment: dict neighbor -> 0 or 1 (1 = points toward center)
    Returns: (feasible: bool, n_violations: int)
    """
    violations = 0
    for c in constraints:
        if c["type"] == "collider":
            # Both must be 1
            for nbr, required_val in c["forced"].items():
                if nbr in assignment and assignment[nbr] != required_val:
                    violations += 1
        elif c["type"] == "non-collider":
            # The forbidden combo must not occur
            forbidden = c["forbidden"]
            all_match = all(
                assignment.get(nbr, 0) == val
                for nbr, val in forbidden.items()
            )
            if all_match:
                violations += 1
    return violations == 0, violations


def soft_score(assignment, scores):
    """Compute soft objective for an assignment.

    assignment: dict neighbor -> 0 or 1 (1 = toward center)
    scores: dict neighbor -> (score_toward, score_away)
    """
    total = 0.0
    for nbr, b in assignment.items():
        s_toward, s_away = scores.get(nbr, (0.5, 0.5))
        if b == 1:
            total += s_toward
        else:
            total += s_away
    return total


def solve_local(node, neighbors, ci_facts, soft_scores):
    """Solve the local Max-2SAT problem for a single node.

    Exact enumeration over 2^d assignments (d = len(neighbors)).

    Returns:
        best_assignment: dict neighbor -> 0 or 1
        best_score: float
        feasible_count: int (how many assignments were feasible)
        total_count: int (2^d)
        hard_flips: list of (neighbor, from_val, to_val) where hard constraints
                    changed the LLM's preferred direction
    """
    d = len(neighbors)
    constraints = extract_hard_constraints(ci_facts, node)

    best_assignment = None
    best_score = -float("inf")
    feasible_count = 0
    total_count = 2 ** d

    for bits in range(total_count):
        assignment = {}
        for i, nbr in enumerate(neighbors):
            assignment[nbr] = (bits >> i) & 1

        feasible, _ = check_feasibility(assignment, constraints)
        if not feasible:
            continue

        feasible_count += 1
        score = soft_score(assignment, soft_scores)
        if score > best_score:
            best_score = score
            best_assignment = dict(assignment)

    if best_assignment is None:
        # Infeasible: no assignment satisfies all hard constraints
        # Fallback: use LLM-preferred directions (ignore constraints)
        best_assignment = {}
        for nbr in neighbors:
            s_toward, s_away = soft_scores.get(nbr, (0.5, 0.5))
            best_assignment[nbr] = 1 if s_toward >= s_away else 0
        best_score = soft_score(best_assignment, soft_scores)
        feasible_count = 0  # signal infeasibility

    # Detect hard flips: where constraints changed the LLM's preferred direction
    hard_flips = []
    for nbr in neighbors:
        s_toward, s_away = soft_scores.get(nbr, (0.5, 0.5))
        llm_preferred = 1 if s_toward >= s_away else 0
        if best_assignment[nbr] != llm_preferred:
            hard_flips.append((nbr, llm_preferred, best_assignment[nbr]))

    return best_assignment, best_score, feasible_count, total_count, hard_flips


def assignment_to_directions(node, assignment):
    """Convert binary assignment to direction strings."""
    directions = {}
    for nbr, b in assignment.items():
        if b == 1:
            directions[nbr] = f"{nbr}->{node}"
        else:
            directions[nbr] = f"{node}->{nbr}"
    return directions


def run_phase2(results_path, skeleton_info=None, use_pe=False, collider_mode="hard"):
    """Run Phase 2 on Phase 1 results.

    Args:
        results_path: path to mve_results.json from Phase 1
        skeleton_info: optional pre-computed skeleton info dict
        use_pe: if True, use PE votes instead of ego votes as soft scores
        collider_mode: "hard" (default), "drop" (ignore collider constraints),
                       or "non-collider-only" (keep only non-collider constraints)

    Returns:
        phase2_results: dict with per-node solutions and comparison metrics
    """
    with open(results_path) as f:
        data = json.load(f)

    raw_ego = data.get("raw_results_b", [])
    raw_pe = data.get("raw_results_a", [])
    per_node = data.get("per_node", {})
    meta = data.get("metadata", {})

    source_label = "pe" if use_pe else "ego"
    results = {
        "metadata": {
            "phase": 2,
            "source": str(results_path),
            "network": meta.get("network", "unknown"),
            "soft_score_source": source_label,
            "collider_mode": collider_mode,
        },
        "per_node": {},
        "summary": {},
    }

    total_edges = 0
    phase1_correct = 0
    phase2_correct = 0
    hard_flip_count = 0
    hard_flip_helped = 0
    hard_flip_hurt = 0
    infeasible_nodes = 0

    for node, info in per_node.items():
        neighbors = info["neighbors"]
        degree = info["degree"]
        ci_facts = info.get("ci_facts", [])

        # Filter CI facts based on collider_mode
        if collider_mode == "drop":
            ci_facts = [f for f in ci_facts if f["type"] != "collider"]
        elif collider_mode == "non-collider-only":
            ci_facts = [f for f in ci_facts if f["type"] == "non-collider"]

        if degree > 12:
            continue

        # Get soft scores
        raw_source = raw_pe if use_pe else raw_ego
        soft_scores = votes_to_soft_scores(raw_source, node, neighbors)

        # Solve local Max-2SAT
        assignment, score, n_feasible, n_total, hard_flips = solve_local(
            node, neighbors, ci_facts, soft_scores
        )

        directions = assignment_to_directions(node, assignment)

        # Evaluate against ground truth
        gt_edges = info.get("gt_edges", [])
        gt_map = {}
        for e in gt_edges:
            u, v = e
            gt_map[v if u == node else u] = f"{u}->{v}"

        node_correct_p1 = 0
        node_correct_p2 = 0
        node_total = 0

        for nbr in neighbors:
            if nbr not in gt_map:
                continue
            gt_dir = gt_map[nbr]
            node_total += 1

            # Phase 1: majority vote from source (ego or PE)
            s_toward, s_away = soft_scores.get(nbr, (0.5, 0.5))
            p1_dir = f"{nbr}->{node}" if s_toward > s_away else f"{node}->{nbr}"
            if s_toward == s_away:
                p1_dir = "uncertain"
            if p1_dir == gt_dir:
                node_correct_p1 += 1

            # Phase 2: after constraint satisfaction
            p2_dir = directions.get(nbr, "uncertain")
            if p2_dir == gt_dir:
                node_correct_p2 += 1

        total_edges += node_total
        phase1_correct += node_correct_p1
        phase2_correct += node_correct_p2

        if n_feasible == 0:
            infeasible_nodes += 1

        # Track hard flips
        for nbr, from_val, to_val in hard_flips:
            hard_flip_count += 1
            if nbr in gt_map:
                gt_dir = gt_map[nbr]
                p2_dir = directions[nbr]
                s_toward, s_away = soft_scores.get(nbr, (0.5, 0.5))
                p1_dir = f"{nbr}->{node}" if s_toward > s_away else f"{node}->{nbr}"
                if p2_dir == gt_dir and p1_dir != gt_dir:
                    hard_flip_helped += 1
                elif p2_dir != gt_dir and p1_dir == gt_dir:
                    hard_flip_hurt += 1

        results["per_node"][node] = {
            "degree": degree,
            "n_feasible": n_feasible,
            "n_total": n_total,
            "hard_flips": [(nbr, fv, tv) for nbr, fv, tv in hard_flips],
            "p1_correct": node_correct_p1,
            "p2_correct": node_correct_p2,
            "n_edges": node_total,
            "directions": directions,
        }

    p1_acc = phase1_correct / max(total_edges, 1)
    p2_acc = phase2_correct / max(total_edges, 1)
    delta = p2_acc - p1_acc

    results["summary"] = {
        "total_edges": total_edges,
        "phase1_correct": phase1_correct,
        "phase2_correct": phase2_correct,
        "phase1_accuracy": round(p1_acc * 100, 1),
        "phase2_accuracy": round(p2_acc * 100, 1),
        "delta_pp": round(delta * 100, 1),
        "hard_flips": hard_flip_count,
        "hard_flips_helped": hard_flip_helped,
        "hard_flips_hurt": hard_flip_hurt,
        "infeasible_nodes": infeasible_nodes,
    }

    return results


def main():
    """Run Phase 2 on all available Phase 1 results."""
    import sys

    results_dir = Path("projects/locale/experiments/results")

    # Find all full-coverage results (primary) and standard results
    targets = [
        ("Insurance Full", "mve_27b_insurance_full"),
        ("Alarm Full", "mve_27b_alarm_full"),
        ("Sachs Full", "mve_27b_sachs_full"),
        ("Child Full", "mve_27b_child_full"),
        ("Insurance NT", "mve_27b_disguised"),
        ("Alarm NT", "mve_27b_alarm_disguised"),
    ]

    print("=" * 70)
    print("LOCALE Phase 2: Max-2SAT Local Constraint Compilation")
    print("=" * 70)

    for label, dirname in targets:
        path = results_dir / dirname / "mve_results.json"
        if not path.exists():
            continue

        # Check if per_node has ci_facts
        with open(path) as f:
            data = json.load(f)
        has_ci = any(
            "ci_facts" in info
            for info in data.get("per_node", {}).values()
        )
        if not has_ci:
            print(f"\n{label}: SKIP (no CI facts in results — need to re-run Phase 1 with CI storage)")
            continue

        print(f"\n{'='*50}")
        print(f"{label}")
        print(f"{'='*50}")

        # Run both ego and PE pipelines
        for source, use_pe in [("Ego", False), ("PE", True)]:
            r = run_phase2(str(path), use_pe=use_pe)
            s = r["summary"]

            print(f"\n  [{source}] Edges: {s['total_edges']}")
            print(f"  [{source}] Phase 1 ({source.lower()} majority): {s['phase1_accuracy']}%")
            print(f"  [{source}] Phase 2 (+ constraints): {s['phase2_accuracy']}%")
            print(f"  [{source}] Delta: {s['delta_pp']:+.1f}pp")
            print(f"  [{source}] Hard flips: {s['hard_flips']} (helped={s['hard_flips_helped']}, hurt={s['hard_flips_hurt']})")

            # Save results
            suffix = "_pe" if use_pe else ""
            out_path = results_dir / dirname / f"phase2_results{suffix}.json"
            with open(out_path, "w") as f:
                json.dump(r, f, indent=2)


if __name__ == "__main__":
    main()
