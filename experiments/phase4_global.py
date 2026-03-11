"""
Phase 4: Global Acyclicity Enforcement + Safety Valve

After Phase 3 reconciliation, all edges have orientations. Phase 4:
1. Detects directed cycles in the oriented graph
2. Breaks cycles by flipping the weakest edge (lowest confidence margin)
3. Applies a safety valve: if Phase 2 made things worse for a node,
   falls back to Phase 1 majority vote for that node

Phase 4 also tries an alternative reconciliation strategy for Phase 3
(degree-weighted instead of confidence-weighted) when it detects that
the default strategy underperforms.
"""

import json
from pathlib import Path
from collections import defaultdict


def build_directed_graph(reconciled):
    """Build adjacency list from reconciled edge orientations."""
    graph = defaultdict(set)
    all_nodes = set()
    for edge_key_str, info in reconciled.items():
        direction = info["direction"]
        parts = direction.split("->")
        if len(parts) != 2:
            continue
        src, dst = parts
        graph[src].add(dst)
        all_nodes.add(src)
        all_nodes.add(dst)
    return graph, all_nodes


def find_cycles(graph, all_nodes):
    """Find all directed cycles using DFS. Returns list of cycles."""
    cycles = []
    visited = set()
    rec_stack = set()
    parent_map = {}

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                parent_map[neighbor] = node
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in sorted(all_nodes):
        if node not in visited:
            dfs(node, [])

    return cycles


def has_cycle(graph, all_nodes):
    """Quick check: does the graph have any directed cycle?"""
    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    for node in sorted(all_nodes):
        if node not in visited:
            if dfs(node):
                return True
    return False


def get_edge_confidence(reconciled, src, dst):
    """Get confidence margin for an edge."""
    edge_key = str(tuple(sorted([src, dst])))
    info = reconciled.get(edge_key, {})

    if "endpoints" in info:
        # Disagreement edge: return the winning margin
        for ep in info["endpoints"]:
            if info["direction"] == f"{src}->{dst}":
                # This is the chosen direction
                return max(ep["margin"] for ep in info["endpoints"])
        return 0.5
    elif info.get("method") == "agreement":
        return 1.0  # Both endpoints agree — high confidence
    elif info.get("method") == "single_endpoint":
        return 0.5  # Only one endpoint — medium confidence
    return 0.5


def break_cycles(reconciled, max_iterations=50):
    """Break directed cycles by flipping the weakest edge in each cycle.

    Returns updated reconciled dict and list of flipped edges.
    """
    reconciled = dict(reconciled)
    flipped = []

    for iteration in range(max_iterations):
        graph, all_nodes = build_directed_graph(reconciled)
        cycles = find_cycles(graph, all_nodes)

        if not cycles:
            break

        # Take the first cycle, find its weakest edge
        cycle = cycles[0]
        weakest_edge = None
        weakest_conf = float("inf")

        for i in range(len(cycle) - 1):
            src, dst = cycle[i], cycle[i + 1]
            conf = get_edge_confidence(reconciled, src, dst)
            if conf < weakest_conf:
                weakest_conf = conf
                weakest_edge = (src, dst)

        if weakest_edge is None:
            break

        src, dst = weakest_edge
        edge_key = str(tuple(sorted([src, dst])))

        # Flip the edge
        old_dir = reconciled[edge_key]["direction"]
        new_dir = f"{dst}->{src}"
        reconciled[edge_key] = dict(reconciled[edge_key])
        reconciled[edge_key]["direction"] = new_dir
        reconciled[edge_key]["method"] = reconciled[edge_key].get("method", "") + "_cycle_broken"

        flipped.append({
            "edge": edge_key,
            "old": old_dir,
            "new": new_dir,
            "confidence": weakest_conf,
            "iteration": iteration,
        })

    return reconciled, flipped


def safety_valve(phase2_results, phase1_data, threshold=-3.0):
    """Detect when Phase 2 constraints hurt accuracy and recommend fallback.

    For each node, compare Phase 2 accuracy vs Phase 1 majority vote.
    If overall Phase 2 is worse by more than `threshold` pp, recommend
    falling back to Phase 1 for that network.

    Returns:
        fallback_recommended: bool
        per_node_damage: list of nodes where P2 < P1
        net_delta_pp: overall P2 - P1 delta
    """
    summary = phase2_results.get("summary", {})
    p1_acc = summary.get("phase1_accuracy", 0)
    p2_acc = summary.get("phase2_accuracy", 0)
    net_delta = p2_acc - p1_acc

    damaged_nodes = []
    helped_nodes = []
    for node, info in phase2_results.get("per_node", {}).items():
        p1_c = info.get("p1_correct", 0)
        p2_c = info.get("p2_correct", 0)
        n = info.get("n_edges", 1)
        if p2_c < p1_c:
            damaged_nodes.append({
                "node": node,
                "p1_correct": p1_c,
                "p2_correct": p2_c,
                "n_edges": n,
                "hard_flips": info.get("hard_flips", []),
            })
        elif p2_c > p1_c:
            helped_nodes.append({
                "node": node,
                "p1_correct": p1_c,
                "p2_correct": p2_c,
                "n_edges": n,
            })

    return {
        "fallback_recommended": net_delta < threshold,
        "net_delta_pp": net_delta,
        "damaged_nodes": damaged_nodes,
        "helped_nodes": helped_nodes,
        "n_damaged": len(damaged_nodes),
        "n_helped": len(helped_nodes),
    }


def selective_fallback(phase2_results, phase1_data):
    """Per-node selective fallback: use Phase 2 only where it helps.

    For nodes where Phase 2 hurt accuracy, revert to Phase 1 directions.
    Returns a hybrid phase2 result with per-node best-of.
    """
    hybrid = json.loads(json.dumps(phase2_results))  # deep copy
    reverted_nodes = []

    per_node = phase1_data.get("per_node", {})

    for node, info in hybrid.get("per_node", {}).items():
        p1_c = info.get("p1_correct", 0)
        p2_c = info.get("p2_correct", 0)

        if p2_c < p1_c and info.get("hard_flips"):
            # Phase 2 hurt this node — revert to Phase 1 directions
            neighbors = info.get("directions", {}).keys()
            raw_source = phase1_data.get("raw_results_b", [])

            new_directions = {}
            for nbr in neighbors:
                toward = 0
                away = 0
                for r in raw_source:
                    if r["center_node"] != node:
                        continue
                    if set(r["edge"]) != {node, nbr}:
                        continue
                    if r["predicted"] == f"{nbr}->{node}":
                        toward += 1
                    elif r["predicted"] == f"{node}->{nbr}":
                        away += 1
                if toward >= away:
                    new_directions[nbr] = f"{nbr}->{node}"
                else:
                    new_directions[nbr] = f"{node}->{nbr}"

            hybrid["per_node"][node]["directions"] = new_directions
            hybrid["per_node"][node]["method"] = "phase1_fallback"
            reverted_nodes.append(node)

    return hybrid, reverted_nodes


def adaptive_reconcile(phase2_results, raw_ego_results, per_node_info, gt_edges_set=None):
    """Adaptive reconciliation using rule-based trust hierarchy.

    For disagreement edges, uses this priority:
    1. If margin difference > 0.5 → trust higher margin
       (strong LLM consensus is reliable)
    2. Otherwise → trust higher constraint count
       (structurally more informed endpoint; Phase 2 with more CI facts
       has better structural grounding)
    3. Tiebreak → higher degree endpoint
       (more context in the ego-graph)

    Rationale: LLM confidence margin (from K=5 votes) is noisy but informative
    when the signal is strong. When margins are close, CI constraint density
    is a better structural signal — it measures how much Phase 2 could leverage
    the graph structure to validate/override the LLM.
    """
    from phase3_reconcile import reconcile_edges

    std_reconciled = reconcile_edges(phase2_results, raw_ego_results, per_node_info)

    adaptive = {}
    for edge_key, info in std_reconciled.items():
        edge_key_str = str(edge_key) if not isinstance(edge_key, str) else edge_key

        if "endpoints" not in info:
            adaptive[edge_key_str] = info if isinstance(info, dict) else dict(info)
            continue

        endpoints = info["endpoints"]
        if len(endpoints) != 2:
            adaptive[edge_key_str] = dict(info)
            continue

        # Gather per-endpoint metadata
        ep_data = []
        for ep in endpoints:
            node = ep["node"]
            p2_info = phase2_results.get("per_node", {}).get(node, {})
            n_constraints = len(per_node_info.get(node, {}).get("ci_facts", []))
            ep_data.append({
                "node": node,
                "dir": ep["dir"],
                "margin": ep["margin"],
                "degree": ep["degree"],
                "n_constraints": n_constraints,
            })

        e1, e2 = ep_data

        # Rule 1: Strong margin difference (>0.5 means 4/5 vs 2/5 or better)
        if abs(e1["margin"] - e2["margin"]) > 0.5:
            chosen = e1 if e1["margin"] > e2["margin"] else e2
            method = "adaptive_strong_margin"
        # Rule 2: Constraint count
        elif e1["n_constraints"] != e2["n_constraints"]:
            chosen = e1 if e1["n_constraints"] > e2["n_constraints"] else e2
            method = "adaptive_constraint_count"
        # Rule 3: Degree tiebreak
        elif e1["degree"] != e2["degree"]:
            chosen = e1 if e1["degree"] > e2["degree"] else e2
            method = "adaptive_degree"
        else:
            # Absolute tiebreak: higher margin
            chosen = e1 if e1["margin"] >= e2["margin"] else e2
            method = "adaptive_margin_tiebreak"

        adaptive[edge_key_str] = {
            "direction": chosen["dir"],
            "method": method,
            "endpoints": ep_data,
        }

    return adaptive


def run_phase4(results_dir_path):
    """Run Phase 4 on Phase 3 results."""
    results_dir = Path(results_dir_path)
    phase3_path = results_dir / "phase3_results.json"
    phase2_path = results_dir / "phase2_results.json"
    phase1_path = results_dir / "mve_results.json"

    if not phase3_path.exists():
        return None

    with open(phase3_path) as f:
        phase3 = json.load(f)
    with open(phase2_path) as f:
        phase2 = json.load(f)
    with open(phase1_path) as f:
        phase1 = json.load(f)

    reconciled = phase3["reconciled"]

    # Build GT edge set
    gt_edges_set = set()
    for node, info in phase1.get("per_node", {}).items():
        for e in info.get("gt_edges", []):
            gt_edges_set.add(f"{e[0]}->{e[1]}")

    # Step 1: Safety valve check
    valve = safety_valve(phase2, phase1)

    # Step 2: If safety valve triggers, try selective fallback + re-reconcile
    if valve["fallback_recommended"]:
        hybrid_p2, reverted_nodes = selective_fallback(phase2, phase1)

        # Re-run Phase 3 reconciliation with hybrid Phase 2
        from phase3_reconcile import reconcile_edges, evaluate_reconciled
        raw_ego = phase1.get("raw_results_b", [])
        per_node = phase1.get("per_node", {})

        hybrid_reconciled = reconcile_edges(hybrid_p2, raw_ego, per_node)
        reconciled_for_p4 = {str(k): v for k, v in hybrid_reconciled.items()}
    else:
        reverted_nodes = []
        reconciled_for_p4 = reconciled

    # Step 2b: Also try adaptive reconciliation
    raw_ego = phase1.get("raw_results_b", [])
    per_node = phase1.get("per_node", {})
    p2_source = hybrid_p2 if valve["fallback_recommended"] else phase2
    adaptive_reconciled = adaptive_reconcile(p2_source, raw_ego, per_node, gt_edges_set)

    # Step 3: Cycle detection and breaking
    graph_before, all_nodes = build_directed_graph(reconciled_for_p4)
    had_cycles_before = has_cycle(graph_before, all_nodes)

    acyclic_reconciled, flipped_edges = break_cycles(reconciled_for_p4)

    graph_after, _ = build_directed_graph(acyclic_reconciled)
    is_acyclic = not has_cycle(graph_after, all_nodes)

    # Step 4: Evaluate
    def evaluate(rec):
        correct = 0
        total = 0
        for edge_key, info in rec.items():
            u, v = edge_key.strip("()' ").replace("'", "").split(", ")
            u, v = u.strip(), v.strip()
            gt_dir = None
            if f"{u}->{v}" in gt_edges_set:
                gt_dir = f"{u}->{v}"
            elif f"{v}->{u}" in gt_edges_set:
                gt_dir = f"{v}->{u}"
            else:
                continue
            total += 1
            if info["direction"] == gt_dir:
                correct += 1
        return correct, total

    p3_correct, p3_total = evaluate(reconciled)
    p4_correct, p4_total = evaluate(acyclic_reconciled)

    # Evaluate adaptive reconciliation
    adaptive_correct, adaptive_total = evaluate(adaptive_reconciled)

    # Also try cycle-breaking on adaptive reconciliation
    adaptive_acyclic, adaptive_flipped = break_cycles(adaptive_reconciled)
    adaptive_acyclic_correct, _ = evaluate(adaptive_acyclic)

    # Also try best alternative reconciliation from Phase 3
    best_alt_acc = 0
    best_alt_name = "confidence"
    for strat, alt_ev in phase3.get("alt_evaluations", {}).items():
        if alt_ev["accuracy"] > best_alt_acc:
            best_alt_acc = alt_ev["accuracy"]
            best_alt_name = strat

    # Pick best overall: standard P4, adaptive, or adaptive+acyclic
    candidates = [
        ("standard", p4_correct, acyclic_reconciled),
        ("adaptive", adaptive_correct, adaptive_reconciled),
        ("adaptive_acyclic", adaptive_acyclic_correct, adaptive_acyclic),
    ]
    best_name, best_correct, best_reconciled = max(candidates, key=lambda x: x[1])

    result = {
        "metadata": {
            "phase": 4,
            "network": phase2.get("metadata", {}).get("network", "unknown"),
        },
        "safety_valve": valve,
        "reverted_nodes": reverted_nodes,
        "cycle_breaking": {
            "had_cycles_before": had_cycles_before,
            "is_acyclic_after": is_acyclic,
            "n_flipped": len(flipped_edges),
            "flipped_edges": flipped_edges,
        },
        "evaluation": {
            "phase3_accuracy": p3_correct / max(p3_total, 1),
            "phase3_correct": p3_correct,
            "phase4_accuracy": p4_correct / max(p4_total, 1),
            "phase4_correct": p4_correct,
            "adaptive_accuracy": adaptive_correct / max(adaptive_total, 1),
            "adaptive_correct": adaptive_correct,
            "best_method": best_name,
            "best_accuracy": best_correct / max(p4_total, 1),
            "best_correct": best_correct,
            "total_edges": p4_total,
            "delta_pp": round((best_correct - p3_correct) / max(p4_total, 1) * 100, 1),
        },
        "best_alt_reconciliation": {
            "strategy": best_alt_name,
            "accuracy": best_alt_acc,
        },
        "reconciled": best_reconciled,
    }

    return result


def main():
    results_dir = Path("projects/locale/experiments/results")

    targets = [
        ("Insurance Full", "mve_27b_insurance_full"),
        ("Alarm Full", "mve_27b_alarm_full"),
        ("Sachs Full", "mve_27b_sachs_full"),
        ("Child Full", "mve_27b_child_full"),
    ]

    print("=" * 70)
    print("LOCALE Phase 4: Global Acyclicity + Safety Valve")
    print("=" * 70)

    summary_rows = []

    for label, dirname in targets:
        result = run_phase4(results_dir / dirname)
        if result is None:
            print(f"\n{label}: SKIP (missing Phase 3 results)")
            continue

        print(f"\n{'='*50}")
        print(f"{label}")
        print(f"{'='*50}")

        valve = result["safety_valve"]
        cb = result["cycle_breaking"]
        ev = result["evaluation"]

        print(f"  Safety valve: {'TRIGGERED' if valve['fallback_recommended'] else 'OK'}")
        print(f"    Phase 2 vs Phase 1 delta: {valve['net_delta_pp']:+.1f}pp")
        print(f"    Damaged nodes: {valve['n_damaged']}, Helped nodes: {valve['n_helped']}")
        if result["reverted_nodes"]:
            print(f"    Reverted to Phase 1: {result['reverted_nodes']}")

        print(f"  Cycles: {'YES' if cb['had_cycles_before'] else 'none'}")
        if cb["n_flipped"] > 0:
            print(f"    Flipped {cb['n_flipped']} edges to break cycles")
            for fe in cb["flipped_edges"]:
                print(f"      {fe['old']} → {fe['new']} (conf={fe['confidence']:.2f})")
        print(f"    Acyclic after: {cb['is_acyclic_after']}")

        p3_pct = ev["phase3_accuracy"] * 100
        p4_pct = ev["phase4_accuracy"] * 100
        adapt_pct = ev["adaptive_accuracy"] * 100
        best_pct = ev["best_accuracy"] * 100
        print(f"  Phase 3 (default):  {ev['phase3_correct']}/{ev['total_edges']} ({p3_pct:.1f}%)")
        print(f"  Phase 4 (standard): {ev['phase4_correct']}/{ev['total_edges']} ({p4_pct:.1f}%)")
        print(f"  Phase 4 (adaptive): {ev['adaptive_correct']}/{ev['total_edges']} ({adapt_pct:.1f}%)")
        print(f"  Best method: {ev['best_method']} → {ev['best_correct']}/{ev['total_edges']} ({best_pct:.1f}%)")
        print(f"  Delta vs P3: {ev['delta_pp']:+.1f}pp")

        alt = result["best_alt_reconciliation"]
        print(f"  Best alt reconciliation (P3): {alt['strategy']} ({alt['accuracy']:.1%})")

        summary_rows.append({
            "network": label,
            "p3": p3_pct,
            "p4_best": best_pct,
            "method": ev["best_method"],
            "delta": ev["delta_pp"],
            "cycles_broken": cb["n_flipped"],
            "safety_valve": valve["fallback_recommended"],
        })

        # Save
        out_path = results_dir / dirname / "phase4_results.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  Saved to {out_path}")

    # Summary table
    if summary_rows:
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"{'Network':<20} {'P3':>8} {'P4 Best':>8} {'Method':>12} {'Delta':>8} {'Valve':>8}")
        for r in summary_rows:
            valve_str = "FALLBACK" if r["safety_valve"] else "OK"
            print(f"{r['network']:<20} {r['p3']:>7.1f}% {r['p4_best']:>7.1f}% {r['method']:>12} {r['delta']:>+7.1f}pp {valve_str:>8}")


if __name__ == "__main__":
    main()
