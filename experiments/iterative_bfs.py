"""
Iterative BFS Ego-Graph Expansion — Survey Propagation-style Decimation

Implements the original LOCALE design: multi-round ego-graph querying where
established orientations from earlier rounds feed as context into later rounds.

Round 1: Query seed nodes (highest degree/centrality) with standard ego prompts.
          Solve Max-2SAT per node. Decimate high-confidence edges.
Round 2+: Query frontier nodes with enriched prompts that include established
          orientations. Solve Max-2SAT with additional hard constraints from
          established edges. Decimate. Repeat.

This is the SP-style decimation loop:
  compute marginals → fix most biased → simplify → repeat

Factor graph mapping:
  Variable nodes: x_e ∈ {+1, -1} per undirected edge (orientation)
  Factor nodes: one per ego-graph f_v(x_{e1},...,x_{ed}) = LLM_oracle(EG(v))
  Decimation: fix edges where reconciliation precision > tau

Usage:
  python iterative_bfs.py --network insurance --n-samples 10000
  python iterative_bfs.py --network alarm --n-samples 10000 --max-rounds 5
"""

import argparse
import json
import os
import re
import time
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import networkx as nx
from openai import OpenAI

from mve_insurance import (
    load_network, sample_data, estimate_skeleton,
    get_ego_graph_info, query_llm, parse_ego_graph_response,
    strip_think_blocks, build_ego_graph_prompt_v2,
    BASE_URL, MODEL, API_KEY, MAX_CONCURRENCY,
    NETWORK_CONFIGS, SEED_DATA, N_SAMPLES,
    VAR_DESCRIPTIONS, ALARM_DESCRIPTIONS, SACHS_DESCRIPTIONS,
    CHILD_DESCRIPTIONS, ASIA_DESCRIPTIONS, HEPAR2_DESCRIPTIONS,
    HAILFINDER_DESCRIPTIONS, TEMP_LADDER,
)
from phase2_max2sat import (
    votes_to_soft_scores, extract_hard_constraints,
    check_feasibility, soft_score, solve_local, assignment_to_directions,
)


# ── Configuration ─────────────────────────────────────────────────

K_PASSES = 5
DECIMATION_THRESHOLD = 0.7   # Minimum majority fraction to decimate an edge
CONFIDENCE_DECAY = 0.9       # Round k confidence = raw_conf * decay^(k-1)
MAX_ROUNDS = 10
TEMPERATURE = 0.7


# ── Data Structures ──────────────────────────────────────────────

@dataclass
class EstablishedEdge:
    """An edge that has been decimated (committed) in a previous round."""
    src: str
    dst: str
    confidence: float
    round_num: int
    source_node: str     # Which ego-graph produced this
    n_votes_for: int     # How many votes supported this direction
    n_votes_total: int

    @property
    def direction(self):
        return f"{self.src}->{self.dst}"

    @property
    def edge_key(self):
        return frozenset({self.src, self.dst})


@dataclass
class RoundResult:
    """Results from a single round of BFS expansion."""
    round_num: int
    nodes_queried: list
    edges_oriented: int       # New edges oriented this round
    edges_decimated: int      # New edges committed (passed threshold)
    total_established: int    # Cumulative established edges
    total_unresolved: int     # Edges still undirected
    accuracy_established: float  # Accuracy of established edges vs GT
    accuracy_all: float       # Accuracy of all oriented edges (including low-conf)
    elapsed_seconds: float
    queries_this_round: int


# ── BFS Round Scheduler ─────────────────────────────────────────

def select_seed_nodes(skeleton, established_edges, min_degree=2):
    """Select seed nodes for Round 1: highest degree nodes first.

    For later rounds, select frontier nodes: nodes adjacent to established
    edges that haven't been queried yet.
    """
    degrees = {n: len(list(skeleton.neighbors(n))) for n in skeleton.nodes()}
    eligible = [n for n, d in degrees.items() if d >= min_degree]
    # Sort by degree descending
    return sorted(eligible, key=lambda n: -degrees[n])


def select_frontier_nodes(skeleton, established_edges, queried_nodes, min_degree=2):
    """Select frontier nodes for expansion rounds.

    Frontier = nodes adjacent to at least one established edge that
    haven't been queried yet, sorted by number of established neighbor edges
    (more context = query first).
    """
    established_nodes = set()
    for e in established_edges.values():
        established_nodes.add(e.src)
        established_nodes.add(e.dst)

    frontier = []
    for node in skeleton.nodes():
        if node in queried_nodes:
            continue
        if len(list(skeleton.neighbors(node))) < min_degree:
            continue
        # Count how many of this node's edges are already established
        n_established = 0
        for nbr in skeleton.neighbors(node):
            if frozenset({node, nbr}) in established_edges:
                n_established += 1
        if n_established > 0:
            frontier.append((node, n_established))

    # Sort by most established context first
    frontier.sort(key=lambda x: (-x[1], -len(list(skeleton.neighbors(x[0])))))
    return [n for n, _ in frontier]


# ── Context-Enriched Ego Prompt ──────────────────────────────────

def build_iterative_ego_prompt(node, neighbors, neighbor_adj, ci_facts,
                                established_edges, var_descriptions, round_num):
    """Build an ego prompt enriched with established orientations from prior rounds.

    This is the core innovation of the iterative approach: the LLM sees
    not just the local structure, but also orientations established by
    neighboring ego-graphs in previous rounds.
    """
    dn = node
    node_desc = var_descriptions.get(node, node)

    # Partition neighbors into established and unresolved
    established_nbrs = []
    unresolved_nbrs = []
    for nbr in neighbors:
        ekey = frozenset({node, nbr})
        if ekey in established_edges:
            established_nbrs.append(nbr)
        else:
            unresolved_nbrs.append(nbr)

    # Build neighbor list
    nbr_lines = []
    for i, nbr in enumerate(neighbors, 1):
        nbr_desc = var_descriptions.get(nbr, nbr)
        nbr_lines.append(f"  {i}. {nbr} — {nbr_desc}")
    nbr_block = "\n".join(nbr_lines)

    # Build established orientations block
    est_lines = []
    for nbr in established_nbrs:
        ekey = frozenset({node, nbr})
        e = established_edges[ekey]
        conf_pct = f"{e.confidence:.0%}"
        est_lines.append(
            f"  ESTABLISHED (round {e.round_num}, conf={conf_pct}): {e.direction}"
        )
    est_block = "\n".join(est_lines) if est_lines else "  (none — this is the first round)"

    # Build CI constraints as explicit rules (same as ego v2)
    rule_lines = []
    rule_idx = 1
    for (n1, n2), is_adj in neighbor_adj.items():
        if is_adj:
            rule_lines.append(f"  R{rule_idx}. {n1} and {n2} are adjacent.")
        else:
            for cf in ci_facts:
                if cf["pair"] == (n1, n2) or cf["pair"] == (n2, n1):
                    sep_names = cf["separated_by"] if cf["separated_by"] != "empty set" else "the empty set"
                    if cf["type"] == "non-collider":
                        rule_lines.append(
                            f"  R{rule_idx}. {n1} ⊥ {n2} | {{{sep_names}}} — {dn} is a NON-COLLIDER. "
                            f"{n1} and {n2} must NOT both point into {dn}."
                        )
                    else:
                        rule_lines.append(
                            f"  R{rule_idx}. {n1} ⊥ {n2} | {{{sep_names}}} — {dn} is a COLLIDER. "
                            f"{n1} and {n2} should both point into {dn}."
                        )
                    break
            else:
                rule_lines.append(f"  R{rule_idx}. {n1} and {n2} are not adjacent.")
        rule_idx += 1
    rules_block = "\n".join(rule_lines) if rule_lines else "  (no structural constraints)"

    # Build edges to orient list (only unresolved edges)
    edge_lines = []
    for nbr in neighbors:
        ekey = frozenset({node, nbr})
        if ekey in established_edges:
            e = established_edges[ekey]
            edge_lines.append(f"  - {e.direction}  [ESTABLISHED — do not change]")
        else:
            edge_lines.append(f"  - {dn} -- {nbr}: orient this")
    edge_block = "\n".join(edge_lines)

    # Different prompt framing depending on round
    if round_num == 1:
        round_context = "This is the initial analysis. Orient all edges using structural constraints and domain knowledge."
    else:
        n_est = len(established_nbrs)
        n_unres = len(unresolved_nbrs)
        round_context = (
            f"This is round {round_num} of iterative analysis. "
            f"{n_est} edges have already been oriented by analyzing neighboring nodes. "
            f"These established orientations are reliable — treat them as given facts. "
            f"Orient the remaining {n_unres} edge(s) consistently with the established ones."
        )

    prompt = f"""You are a causal structure learning expert. Given a variable and its neighborhood in a causal skeleton, orient each edge using structural constraints, established orientations, and domain knowledge.

IMPORTANT: Statistical constraints from CI tests are most reliable. Established orientations from prior analysis rounds are also reliable — do not contradict them. Use domain knowledge for remaining ambiguity.

{round_context}

CENTER NODE: {dn} — {node_desc}

NEIGHBORS ({len(neighbors)} variables):
{nbr_block}

ESTABLISHED ORIENTATIONS (from prior rounds):
{est_block}

STATISTICAL CONSTRAINTS (from conditional independence tests):
{rules_block}

EDGES TO ORIENT:
{edge_block}

Apply established orientations as fixed facts, then structural constraints, then domain knowledge. Be concise.

For EACH unresolved edge, give ONLY the direction. One per line, no explanation:
{dn} -> [neighbor] OR [neighbor] -> {dn} OR uncertain

Answer:"""
    return prompt


# ── Max-2SAT with Established Constraints ────────────────────────

def solve_local_with_established(node, neighbors, ci_facts, soft_scores,
                                  established_edges, nco_mode=True):
    """Solve Max-2SAT with additional hard constraints from established edges.

    Established edges become unary hard constraints: the orientation is fixed.
    NCO mode: only use non-collider constraints (drop collider constraints).
    """
    d = len(neighbors)
    constraints = extract_hard_constraints(ci_facts, node)

    if nco_mode:
        # Filter: keep only non-collider constraints
        constraints = [c for c in constraints if c["type"] == "non-collider"]

    # Add established edge constraints (unary hard constraints)
    established_constraints = []
    for nbr in neighbors:
        ekey = frozenset({node, nbr})
        if ekey in established_edges:
            e = established_edges[ekey]
            if e.src == nbr and e.dst == node:
                # nbr -> node: b[nbr] = 1 (toward)
                established_constraints.append({"nbr": nbr, "value": 1})
            elif e.src == node and e.dst == nbr:
                # node -> nbr: b[nbr] = 0 (away)
                established_constraints.append({"nbr": nbr, "value": 0})

    best_assignment = None
    best_score = -float("inf")
    feasible_count = 0
    total_count = 2 ** d

    for bits in range(total_count):
        assignment = {}
        for i, nbr in enumerate(neighbors):
            assignment[nbr] = (bits >> i) & 1

        # Check established constraints (hard)
        est_ok = True
        for ec in established_constraints:
            if assignment[ec["nbr"]] != ec["value"]:
                est_ok = False
                break
        if not est_ok:
            continue

        # Check CI constraints
        feasible, _ = check_feasibility(assignment, constraints)
        if not feasible:
            continue

        feasible_count += 1
        score = soft_score(assignment, soft_scores)
        if score > best_score:
            best_score = score
            best_assignment = dict(assignment)

    if best_assignment is None:
        # Infeasible: try relaxing CI constraints but keeping established
        for bits in range(total_count):
            assignment = {}
            for i, nbr in enumerate(neighbors):
                assignment[nbr] = (bits >> i) & 1

            est_ok = True
            for ec in established_constraints:
                if assignment[ec["nbr"]] != ec["value"]:
                    est_ok = False
                    break
            if not est_ok:
                continue

            score = soft_score(assignment, soft_scores)
            if score > best_score:
                best_score = score
                best_assignment = dict(assignment)
                feasible_count = -1  # signal relaxed

    if best_assignment is None:
        # Total fallback: just use soft scores
        best_assignment = {}
        for nbr in neighbors:
            s_toward, s_away = soft_scores.get(nbr, (0.5, 0.5))
            best_assignment[nbr] = 1 if s_toward >= s_away else 0
        best_score = soft_score(best_assignment, soft_scores)

    return best_assignment, best_score, feasible_count, total_count


# ── Decimation Logic ─────────────────────────────────────────────

def decimate_edges(node, assignment, raw_results, neighbors, round_num,
                   established_edges, threshold=DECIMATION_THRESHOLD):
    """Decimate (commit) high-confidence edges from this node's solution.

    An edge is decimated if:
    1. It's not already established
    2. The majority vote fraction exceeds the threshold

    Returns list of new EstablishedEdge objects.
    """
    new_established = []

    for nbr in neighbors:
        ekey = frozenset({node, nbr})
        if ekey in established_edges:
            continue  # Already committed

        # Count votes for each direction
        toward = 0  # nbr -> node
        away = 0    # node -> nbr
        total = 0
        for r in raw_results:
            if r["center_node"] != node:
                continue
            if set(r["edge"]) != {node, nbr}:
                continue
            pred = r["predicted"]
            if pred == f"{nbr}->{node}":
                toward += 1
                total += 1
            elif pred == f"{node}->{nbr}":
                away += 1
                total += 1

        if total == 0:
            continue

        # Check Max-2SAT assignment direction
        b = assignment.get(nbr, None)
        if b is None:
            continue

        if b == 1:
            src, dst = nbr, node
            n_for = toward
        else:
            src, dst = node, nbr
            n_for = away

        # Majority fraction (combining Max-2SAT direction with vote count)
        majority_frac = n_for / total if total > 0 else 0

        if majority_frac >= threshold:
            confidence = majority_frac * (CONFIDENCE_DECAY ** (round_num - 1))
            new_established.append(EstablishedEdge(
                src=src, dst=dst,
                confidence=confidence,
                round_num=round_num,
                source_node=node,
                n_votes_for=n_for,
                n_votes_total=total,
            ))

    return new_established


# ── Main BFS Loop ────────────────────────────────────────────────

def run_iterative_bfs(args):
    """Run the iterative BFS ego-graph expansion."""

    network = args.network
    n_samples = args.n_samples
    max_rounds = args.max_rounds
    enable_thinking = not args.no_think
    threshold = args.threshold

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Network setup ──
    net_cfg = NETWORK_CONFIGS[network]
    var_descriptions = net_cfg["descriptions"] or VAR_DESCRIPTIONS
    domain_text = net_cfg["domain"]

    # Make var_descriptions available globally for parse functions
    import mve_insurance
    mve_insurance.VAR_DESCRIPTIONS = var_descriptions
    mve_insurance._domain_text = f"{domain_text} domain"
    mve_insurance._use_disguised = False

    print("=" * 60)
    print(f"Iterative BFS Ego-Graph Expansion: {network.title()}")
    print(f"Rounds: max {max_rounds}, threshold: {threshold}")
    print("=" * 60)

    # ── Step 0: Data + Skeleton ──
    model, gt_edges = load_network(net_cfg["pgmpy_name"])
    gt_set = set(gt_edges)
    print(f"\n[Setup] GT: {len(model.nodes())} nodes, {len(gt_edges)} directed edges")

    data = sample_data(model, n=n_samples, seed=SEED_DATA)
    skeleton, sep_sets = estimate_skeleton(data, alpha=args.alpha)
    n_skel = len(skeleton.edges())
    print(f"[Setup] Skeleton: {len(skeleton.nodes())} nodes, {n_skel} undirected edges")

    # Skeleton quality
    skel_set = {frozenset(e) for e in skeleton.edges()}
    gt_skel = {frozenset(e) for e in gt_edges}
    skel_tp = len(skel_set & gt_skel)
    print(f"[Setup] Skeleton coverage: {skel_tp}/{len(gt_edges)} = {skel_tp/len(gt_edges):.1%}")

    # Pre-compute ego info for all eligible nodes
    all_nodes = sorted(
        [n for n in skeleton.nodes() if len(list(skeleton.neighbors(n))) >= 2],
        key=lambda n: -len(list(skeleton.neighbors(n)))
    )
    print(f"[Setup] Eligible nodes (d>=2): {len(all_nodes)}")

    node_info = {}
    for node in all_nodes:
        nbrs, nbr_adj, ci_facts, edges_to_orient = get_ego_graph_info(
            node, skeleton, sep_sets, gt_edges
        )
        node_info[node] = {
            "neighbors": nbrs,
            "neighbor_adj": nbr_adj,
            "ci_facts": ci_facts,
            "edges_to_orient": edges_to_orient,
        }

    # Total unique edges across all eligible nodes
    all_edges = set()
    for node in all_nodes:
        for nbr in node_info[node]["neighbors"]:
            all_edges.add(frozenset({node, nbr}))
    print(f"[Setup] Total skeleton edges: {len(all_edges)}")

    # LLM client
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=600.0)
    try:
        test = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'ready'"}],
            max_tokens=10,
            **({"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}} if not enable_thinking else {}),
        )
        print(f"[Setup] Endpoint verified: {test.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"[Setup] ERROR: {e}")
        return

    if enable_thinking:
        concurrency = 1
    else:
        concurrency = 4  # ego prompts are verbose, keep concurrency moderate

    # ── BFS Loop ──
    established_edges = {}  # frozenset -> EstablishedEdge
    queried_nodes = set()
    round_results = []
    all_raw_results = []  # All LLM responses across all rounds
    t_global_start = time.time()

    for round_num in range(1, max_rounds + 1):
        t_round = time.time()
        print(f"\n{'='*60}")
        print(f"ROUND {round_num}")
        print(f"{'='*60}")

        # Select nodes for this round
        if round_num == 1:
            # Round 1: all eligible nodes (BFS wave 1 = full coverage)
            # But we can also do incremental: just seeds first
            if args.incremental:
                # Start with top-N highest degree nodes
                round_nodes = select_seed_nodes(skeleton, established_edges)[:args.seeds_per_round]
            else:
                # Full coverage round 1 (matches current LOCALE behavior)
                round_nodes = all_nodes
        else:
            # Frontier expansion: nodes with established neighbors not yet queried
            round_nodes = select_frontier_nodes(skeleton, established_edges, queried_nodes)
            if not round_nodes:
                # No frontier: re-query all nodes with new context
                if args.requery:
                    round_nodes = all_nodes
                else:
                    print(f"  No frontier nodes available. Stopping.")
                    break

        if not round_nodes:
            print(f"  No nodes to query. Stopping.")
            break

        n_unresolved = len(all_edges) - len(established_edges)
        print(f"  Nodes to query: {len(round_nodes)}")
        print(f"  Established edges: {len(established_edges)}/{len(all_edges)}")
        print(f"  Unresolved edges: {n_unresolved}")

        if n_unresolved == 0:
            print(f"  All edges resolved. Stopping.")
            break

        # ── Build and fire ego queries ──
        jobs = []
        for node in round_nodes:
            info = node_info[node]
            for k in range(K_PASSES):
                shuffled = info["neighbors"].copy()
                random.seed(SEED_DATA + round_num * 1000 + k * 100 + all_nodes.index(node))
                random.shuffle(shuffled)

                prompt = build_iterative_ego_prompt(
                    node, shuffled, info["neighbor_adj"], info["ci_facts"],
                    established_edges, var_descriptions, round_num
                )
                temp = TEMP_LADDER[k % len(TEMP_LADDER)]
                jobs.append((node, k, info["neighbors"], prompt, temp))

        total_queries = len(jobs)
        print(f"  Queries: {total_queries} ({len(round_nodes)} nodes × {K_PASSES} passes)")

        completed = 0
        round_raw = []

        def run_job(job):
            node, k, nbrs, prompt, temp = job
            resp = query_llm(client, prompt, temperature=temp, enable_thinking=enable_thinking)
            return node, k, nbrs, resp

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(run_job, j): j for j in jobs}
            for future in as_completed(futures):
                node, k, nbrs, resp = future.result()
                preds = parse_ego_graph_response(resp, node, nbrs)

                # Store raw results
                info = node_info[node]
                for gt_edge in info["edges_to_orient"]:
                    u, v = gt_edge
                    nbr = v if u == node else u
                    predicted = preds.get(nbr, "uncertain")
                    gt_dir = f"{u}->{v}"
                    round_raw.append({
                        "center_node": node,
                        "edge": (u, v),
                        "predicted": predicted,
                        "correct": predicted == gt_dir,
                        "pass_idx": k,
                        "round": round_num,
                    })

                completed += 1
                if completed % 10 == 0 or completed == total_queries:
                    elapsed = time.time() - t_round
                    print(f"    {completed}/{total_queries} ({elapsed:.1f}s)")

        all_raw_results.extend(round_raw)

        # ── Solve Max-2SAT per node with established constraints ──
        print(f"\n  Solving Max-2SAT per node (NCO mode)...")
        round_assignments = {}
        for node in round_nodes:
            info = node_info[node]
            # Build soft scores from this round's results
            scores = votes_to_soft_scores(round_raw, node, info["neighbors"])
            # Solve with established constraints
            assignment, score, feasible, total, = solve_local_with_established(
                node, info["neighbors"], info["ci_facts"], scores,
                established_edges, nco_mode=True
            )
            round_assignments[node] = assignment

        # ── Decimate: commit high-confidence edges ──
        new_established = []
        for node in round_nodes:
            info = node_info[node]
            new = decimate_edges(
                node, round_assignments[node], round_raw,
                info["neighbors"], round_num, established_edges, threshold
            )
            new_established.extend(new)
            queried_nodes.add(node)

        # Dedup: if two nodes both want to commit the same edge, keep higher confidence
        for e in new_established:
            if e.edge_key in established_edges:
                existing = established_edges[e.edge_key]
                if e.confidence > existing.confidence:
                    established_edges[e.edge_key] = e
            else:
                established_edges[e.edge_key] = e

        # ── Evaluate this round ──
        n_correct_est = sum(
            1 for e in established_edges.values()
            if (e.src, e.dst) in gt_set
        )
        acc_est = n_correct_est / max(len(established_edges), 1)

        # All oriented edges (not just established)
        all_oriented = {}
        for node in queried_nodes:
            if node not in round_assignments:
                continue
            for nbr, b in round_assignments[node].items():
                ekey = frozenset({node, nbr})
                if ekey in established_edges:
                    continue  # Use established version
                if b == 1:
                    all_oriented[ekey] = (nbr, node)
                else:
                    all_oriented[ekey] = (node, nbr)
        for ekey, e in established_edges.items():
            all_oriented[ekey] = (e.src, e.dst)

        n_correct_all = sum(
            1 for (src, dst) in all_oriented.values()
            if (src, dst) in gt_set
        )
        acc_all = n_correct_all / max(len(all_oriented), 1)

        elapsed_round = time.time() - t_round
        rr = RoundResult(
            round_num=round_num,
            nodes_queried=round_nodes,
            edges_oriented=len(all_oriented),
            edges_decimated=len([e for e in new_established if e.edge_key not in established_edges or established_edges[e.edge_key].round_num == round_num]),
            total_established=len(established_edges),
            total_unresolved=len(all_edges) - len(established_edges),
            accuracy_established=acc_est,
            accuracy_all=acc_all,
            elapsed_seconds=elapsed_round,
            queries_this_round=total_queries,
        )
        round_results.append(rr)

        print(f"\n  Round {round_num} summary:")
        print(f"    New decimated: {len(new_established)}")
        print(f"    Total established: {len(established_edges)}/{len(all_edges)} ({len(established_edges)/len(all_edges):.1%})")
        print(f"    Established accuracy: {acc_est:.1%} ({n_correct_est}/{len(established_edges)})")
        print(f"    All oriented accuracy: {acc_all:.1%} ({n_correct_all}/{len(all_oriented)})")
        print(f"    Unresolved: {len(all_edges) - len(established_edges)}")
        print(f"    Time: {elapsed_round:.1f}s")

        # Check convergence: no new edges decimated
        if len(new_established) == 0 and round_num > 1:
            print(f"\n  No new edges decimated. Converged.")
            break

    # ── Final Summary ──
    total_elapsed = time.time() - t_global_start
    total_queries_all = sum(r.queries_this_round for r in round_results)

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS ({len(round_results)} rounds)")
    print(f"{'='*60}")

    # Compute F1
    pred_set = {(e.src, e.dst) for e in established_edges.values()}
    tp = len(pred_set & gt_set)
    fp = len(pred_set - gt_set)
    fn = len(gt_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"  Established edges: {len(established_edges)}/{len(all_edges)} ({len(established_edges)/len(all_edges):.1%})")
    print(f"  Established accuracy: {tp}/{len(established_edges)} = {tp/max(len(established_edges),1):.1%}")
    print(f"  Directed F1: {f1:.3f} (P={precision:.3f}, R={recall:.3f})")
    print(f"  Total queries: {total_queries_all}")
    print(f"  Total time: {total_elapsed:.1f}s")

    # Round-by-round table
    print(f"\n  Round-by-round:")
    print(f"  {'Round':>5} {'Nodes':>6} {'Queries':>8} {'New Dec':>8} {'Established':>12} {'Est Acc':>8} {'All Acc':>8} {'Time':>6}")
    for rr in round_results:
        print(f"  {rr.round_num:>5} {len(rr.nodes_queried):>6} {rr.queries_this_round:>8} "
              f"{rr.edges_decimated:>8} {rr.total_established:>12} "
              f"{rr.accuracy_established:>7.1%} {rr.accuracy_all:>7.1%} {rr.elapsed_seconds:>5.1f}s")

    # Per-round established edge details
    for rr in round_results:
        round_edges = [e for e in established_edges.values() if e.round_num == rr.round_num]
        if round_edges:
            correct = sum(1 for e in round_edges if (e.src, e.dst) in gt_set)
            print(f"\n  Round {rr.round_num} edges ({len(round_edges)}):")
            for e in sorted(round_edges, key=lambda x: -x.confidence)[:10]:
                gt_match = "✓" if (e.src, e.dst) in gt_set else "✗"
                print(f"    {gt_match} {e.direction} (conf={e.confidence:.2f}, from={e.source_node}, votes={e.n_votes_for}/{e.n_votes_total})")
            if len(round_edges) > 10:
                print(f"    ... and {len(round_edges) - 10} more")

    # ── Save results ──
    results = {
        "method": "iterative_bfs",
        "network": network,
        "n_samples": n_samples,
        "model": MODEL,
        "enable_thinking": enable_thinking,
        "max_rounds": max_rounds,
        "threshold": threshold,
        "k_passes": K_PASSES,
        "n_rounds_completed": len(round_results),
        "skeleton": {
            "n_nodes": len(skeleton.nodes()),
            "n_edges": n_skel,
            "coverage": skel_tp / len(gt_edges),
        },
        "final_metrics": {
            "n_established": len(established_edges),
            "n_total_edges": len(all_edges),
            "coverage": len(established_edges) / len(all_edges),
            "accuracy": tp / max(len(established_edges), 1),
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "tp": tp, "fp": fp, "fn": fn,
        },
        "rounds": [
            {
                "round": rr.round_num,
                "nodes_queried": len(rr.nodes_queried),
                "queries": rr.queries_this_round,
                "edges_decimated": rr.edges_decimated,
                "total_established": rr.total_established,
                "accuracy_established": rr.accuracy_established,
                "accuracy_all": rr.accuracy_all,
                "elapsed": rr.elapsed_seconds,
            }
            for rr in round_results
        ],
        "total_queries": total_queries_all,
        "total_elapsed": total_elapsed,
        "established_edges": {
            f"{e.src}->{e.dst}": {
                "confidence": e.confidence,
                "round": e.round_num,
                "source_node": e.source_node,
                "votes": f"{e.n_votes_for}/{e.n_votes_total}",
                "correct": (e.src, e.dst) in gt_set,
            }
            for e in established_edges.values()
        },
    }

    results_file = out_dir / "iterative_bfs_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {results_file}")

    return results


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iterative BFS ego-graph expansion")
    parser.add_argument("--network", default="insurance", choices=list(NETWORK_CONFIGS.keys()))
    parser.add_argument("--n-samples", type=int, default=10000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--no-think", action="store_true", help="Disable thinking mode")
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    parser.add_argument("--threshold", type=float, default=DECIMATION_THRESHOLD,
                        help="Decimation confidence threshold (default: 0.7)")
    parser.add_argument("--incremental", action="store_true",
                        help="Start with seed nodes only (not full coverage)")
    parser.add_argument("--seeds-per-round", type=int, default=5,
                        help="Number of seed nodes per round in incremental mode")
    parser.add_argument("--requery", action="store_true",
                        help="Re-query all nodes on subsequent rounds (with new context)")
    parser.add_argument("--output-dir", default="results/iterative_bfs")
    args = parser.parse_args()
    run_iterative_bfs(args)
