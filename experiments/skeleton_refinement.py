"""
Skeleton Refinement: Use LLM to recover edges PC missed.

F1 decomposition shows skeleton coverage is the binding constraint:
  Insurance 82.7%, Alarm 93.5%, Child 100%, Hepar2 52%

Strategy:
1. Identify candidate missing edges (node pairs not in PC skeleton
   but within 2 hops — they share a neighbor)
2. Query LLM: "Is there a direct causal relationship between X and Y?"
3. Add edges where LLM votes yes with supermajority (precision-first)
4. Re-run orientation pipeline on the refined skeleton

Uses non-thinking mode for speed (~50x faster than thinking).
"""

import json
import time
import random
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

import numpy as np
import networkx as nx
from openai import OpenAI

# Import shared config from mve_insurance
from mve_insurance import (
    BASE_URL, MODEL, API_KEY, MAX_CONCURRENCY,
    load_network, sample_data, estimate_skeleton,
    VAR_DESCRIPTIONS, ALARM_DESCRIPTIONS, SACHS_DESCRIPTIONS,
    CHILD_DESCRIPTIONS, ASIA_DESCRIPTIONS, HEPAR2_DESCRIPTIONS,
    query_llm,
)

NETWORK_DESCRIPTIONS = {
    "insurance": VAR_DESCRIPTIONS,
    "alarm": ALARM_DESCRIPTIONS,
    "sachs": SACHS_DESCRIPTIONS,
    "child": CHILD_DESCRIPTIONS,
    "asia": ASIA_DESCRIPTIONS,
    "hepar2": HEPAR2_DESCRIPTIONS,
}


def find_candidate_pairs(skeleton, gt_edges=None, max_hop=2):
    """Find node pairs NOT in skeleton but within max_hop distance.

    These are the most likely missing edges: close in the graph but
    not directly connected (PC removed the edge or never found it).

    Returns:
        candidates: list of (u, v) tuples
        gt_missing: set of (u, v) tuples that ARE in ground truth but not skeleton
    """
    nodes = list(skeleton.nodes())
    skeleton_edges = set(frozenset({u, v}) for u, v in skeleton.edges())

    candidates = []
    seen = set()

    for node in nodes:
        # Get nodes within max_hop
        for dist in range(2, max_hop + 1):
            # BFS to find nodes at exactly this distance
            lengths = nx.single_source_shortest_path_length(skeleton, node, cutoff=dist)
            for other, d in lengths.items():
                if d < 2:  # skip self and direct neighbors
                    continue
                pair = frozenset({node, other})
                if pair not in seen and pair not in skeleton_edges:
                    seen.add(pair)
                    candidates.append(tuple(sorted([node, other])))

    # Compute ground truth missing edges (for evaluation)
    gt_missing = set()
    if gt_edges:
        for u, v in gt_edges:
            if frozenset({u, v}) not in skeleton_edges:
                gt_missing.add((u, v))

    return candidates, gt_missing


def build_edge_query_prompt(u, v, var_descriptions, skeleton, context_edges=None):
    """Build a prompt asking whether there's a direct causal edge between u and v.

    Provides:
    - Variable descriptions
    - Known neighbors of both nodes (from skeleton)
    - Any relevant context (nearby oriented edges)
    """
    desc_u = var_descriptions.get(u, f"Variable {u}")
    desc_v = var_descriptions.get(v, f"Variable {v}")

    # Get neighbors
    nbrs_u = sorted(skeleton.neighbors(u))
    nbrs_v = sorted(skeleton.neighbors(v))

    # Shared neighbors (these form potential colliders/chains)
    shared = sorted(set(nbrs_u) & set(nbrs_v))

    nbrs_u_desc = ", ".join(f"{n} ({var_descriptions.get(n, n)})" for n in nbrs_u[:8])
    nbrs_v_desc = ", ".join(f"{n} ({var_descriptions.get(n, n)})" for n in nbrs_v[:8])
    shared_desc = ", ".join(f"{n} ({var_descriptions.get(n, n)})" for n in shared[:5])

    prompt = f"""You are a domain expert building a Bayesian network. We are checking whether our causal graph is missing any edges.

Variable 1: {u} — {desc_u}
Variable 2: {v} — {desc_v}

Currently known neighbors of {u}: {nbrs_u_desc if nbrs_u_desc else 'none'}
Currently known neighbors of {v}: {nbrs_v_desc if nbrs_v_desc else 'none'}
{f'Variables connected to both: {shared_desc}' if shared_desc else ''}

Question: Should there be a DIRECT causal link between {u} and {v} in a Bayesian network?

Think about whether {u} can directly influence {v} (or vice versa) without going through any intermediate variable.

A) Yes, there should be a direct causal edge
B) No, their relationship is fully explained through other variables
C) Uncertain"""

    return prompt


def parse_edge_response(response):
    """Parse LLM response into yes/no/uncertain."""
    import re

    if not response:
        return "uncertain"

    text = response.strip()
    text_upper = text.upper()

    # Standalone letter (common with non-thinking mode)
    if text_upper in ("A", "A)", "A."):
        return "yes"
    if text_upper in ("B", "B)", "B."):
        return "no"
    if text_upper in ("C", "C)", "C."):
        return "uncertain"

    # Check last few lines for longer responses
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    tail = "\n".join(lines[-3:]) if len(lines) > 3 else text
    tail_upper = tail.upper()

    # "Answer: A" or "Final answer: B" patterns
    final_match = re.search(r'(?:FINAL\s+)?ANSWER[:\s]+([ABC])\b', tail_upper)
    if final_match:
        ans = final_match.group(1)
        return {"A": "yes", "B": "no"}.get(ans, "uncertain")

    # "A)" or "A." patterns
    if re.search(r'\bA\s*[).]', tail_upper) or "YES, THERE SHOULD" in tail_upper:
        return "yes"
    if re.search(r'\bB\s*[).]', tail_upper) or "NO, ANY RELATIONSHIP" in tail_upper:
        return "no"
    if re.search(r'\bC\s*[).]', tail_upper):
        return "uncertain"

    # Standalone letter at end of last line
    last_line = lines[-1].strip().upper() if lines else ""
    if last_line.endswith(" A") or last_line == "A":
        return "yes"
    if last_line.endswith(" B") or last_line == "B":
        return "no"
    if last_line.endswith(" C") or last_line == "C":
        return "uncertain"

    # Fallback: yes/no keywords
    if "YES" in tail_upper and "NO" not in tail_upper:
        return "yes"
    if "NO" in tail_upper and "YES" not in tail_upper:
        return "no"

    return "uncertain"


def run_skeleton_refinement(network_name, n_samples=10000, alpha=0.05,
                            k_passes=5, concurrency=32,
                            add_threshold=0.8, max_candidates=None,
                            enable_thinking=False, smoketest=False):
    """Run skeleton refinement on a network.

    Args:
        network_name: pgmpy network name
        n_samples: sample size for PC
        alpha: significance level for PC
        k_passes: number of LLM votes per candidate pair
        concurrency: parallel LLM queries
        add_threshold: fraction of 'yes' votes needed to add edge (precision-first)
        max_candidates: cap on number of candidates to query (None = all)
        enable_thinking: use thinking mode (slower but potentially better)
        smoketest: if True, only query 5 candidates

    Returns:
        dict with results
    """
    var_descriptions = NETWORK_DESCRIPTIONS.get(network_name, {})
    if not var_descriptions:
        raise ValueError(f"No descriptions for network {network_name}")

    # Load network and run PC
    print(f"Loading {network_name} network...")
    model, gt_edges = load_network(network_name)
    gt_edge_set = set(frozenset({u, v}) for u, v in gt_edges)

    print(f"Sampling {n_samples} data points...")
    data = sample_data(model, n=n_samples)

    print(f"Running PC (alpha={alpha})...")
    skeleton, sep_sets = estimate_skeleton(data, alpha=alpha)

    skeleton_edges = set(frozenset({u, v}) for u, v in skeleton.edges())
    n_gt = len(gt_edges)
    n_skeleton = len(skeleton_edges)

    # Skeleton quality
    gt_in_skeleton = sum(1 for u, v in gt_edges if frozenset({u, v}) in skeleton_edges)
    skeleton_coverage = gt_in_skeleton / max(n_gt, 1)
    false_positives = n_skeleton - gt_in_skeleton
    skeleton_precision = gt_in_skeleton / max(n_skeleton, 1)

    print(f"Skeleton: {n_skeleton} edges, coverage={skeleton_coverage:.1%}, "
          f"precision={skeleton_precision:.1%}, FP={false_positives}")

    # Find candidate missing edges
    candidates, gt_missing = find_candidate_pairs(skeleton, gt_edges, max_hop=2)

    print(f"Candidates: {len(candidates)} pairs (2-hop), "
          f"GT missing: {len(gt_missing)} edges")

    if max_candidates and len(candidates) > max_candidates:
        # Prioritize: pairs with more shared neighbors first
        def shared_neighbor_count(pair):
            u, v = pair
            nbrs_u = set(skeleton.neighbors(u))
            nbrs_v = set(skeleton.neighbors(v))
            return len(nbrs_u & nbrs_v)

        candidates.sort(key=shared_neighbor_count, reverse=True)
        candidates = candidates[:max_candidates]
        print(f"Capped to {max_candidates} candidates (by shared neighbor count)")

    if smoketest:
        # Take 5 candidates: mix of true positives and true negatives
        tp_candidates = [c for c in candidates if (c[0], c[1]) in gt_missing or (c[1], c[0]) in gt_missing]
        tn_candidates = [c for c in candidates if c not in tp_candidates]
        smoke_candidates = tp_candidates[:3] + tn_candidates[:2]
        if len(smoke_candidates) < 5:
            smoke_candidates = candidates[:5]
        candidates = smoke_candidates
        print(f"Smoketest: {len(candidates)} candidates")

    # Query LLM
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    temperatures = [0.3, 0.5, 0.7, 0.9, 1.1]

    results = {}
    total_queries = len(candidates) * k_passes
    print(f"\nQuerying LLM: {len(candidates)} candidates x {k_passes} passes "
          f"= {total_queries} queries (concurrency={concurrency})")

    # Build all prompts
    tasks = []
    for u, v in candidates:
        prompt = build_edge_query_prompt(u, v, var_descriptions, skeleton)
        for k in range(k_passes):
            temp = temperatures[k % len(temperatures)]
            tasks.append({
                "pair": (u, v),
                "prompt": prompt,
                "temperature": temp,
                "pass_idx": k,
            })

    # Shuffle for load balancing
    random.shuffle(tasks)

    # Execute queries
    completed = 0
    start_time = time.time()
    pair_votes = defaultdict(list)  # (u,v) -> list of "yes"/"no"/"uncertain"

    def do_query(task):
        resp = query_llm(client, task["prompt"], temperature=task["temperature"],
                         enable_thinking=enable_thinking)
        vote = parse_edge_response(resp)
        return task["pair"], vote, resp

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(do_query, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                pair, vote, resp = future.result()
                pair_votes[pair].append(vote)
                completed += 1
                if completed % 50 == 0 or completed == total_queries:
                    elapsed = time.time() - start_time
                    rate = completed / max(elapsed, 0.1)
                    print(f"  {completed}/{total_queries} queries "
                          f"({elapsed:.0f}s, {rate:.1f} q/s)")
            except Exception as e:
                completed += 1
                print(f"  Query error: {e}")

    elapsed = time.time() - start_time
    print(f"\nCompleted {completed} queries in {elapsed:.1f}s")

    # Aggregate votes and decide
    edges_to_add = []
    edge_details = {}

    for (u, v), votes in pair_votes.items():
        n_yes = votes.count("yes")
        n_no = votes.count("no")
        n_uncertain = votes.count("uncertain")
        n_total = len(votes)
        yes_fraction = n_yes / max(n_total, 1)

        is_gt = (u, v) in gt_missing or (v, u) in gt_missing
        add = yes_fraction >= add_threshold

        if add:
            edges_to_add.append((u, v))

        edge_details[f"{u}--{v}"] = {
            "votes": {"yes": n_yes, "no": n_no, "uncertain": n_uncertain},
            "yes_fraction": yes_fraction,
            "add": add,
            "is_gt_missing": is_gt,
        }

    # Evaluate
    n_added = len(edges_to_add)
    tp_added = sum(1 for u, v in edges_to_add
                   if (u, v) in gt_missing or (v, u) in gt_missing)
    fp_added = n_added - tp_added

    # New skeleton metrics
    new_skeleton_edges = skeleton_edges | set(frozenset({u, v}) for u, v in edges_to_add)
    new_gt_in_skeleton = sum(1 for u, v in gt_edges if frozenset({u, v}) in new_skeleton_edges)
    new_coverage = new_gt_in_skeleton / max(n_gt, 1)
    new_precision = new_gt_in_skeleton / max(len(new_skeleton_edges), 1)
    new_fp = len(new_skeleton_edges) - new_gt_in_skeleton

    # Recall of missing edges
    recall_missing = tp_added / max(len(gt_missing), 1)

    result = {
        "metadata": {
            "network": network_name,
            "n_samples": n_samples,
            "alpha": alpha,
            "k_passes": k_passes,
            "add_threshold": add_threshold,
            "enable_thinking": enable_thinking,
            "n_candidates": len(candidates),
            "n_queries": total_queries,
            "elapsed_seconds": elapsed,
        },
        "original_skeleton": {
            "n_edges": n_skeleton,
            "coverage": skeleton_coverage,
            "precision": skeleton_precision,
            "false_positives": false_positives,
        },
        "refinement": {
            "n_candidates_queried": len(candidates),
            "n_gt_missing": len(gt_missing),
            "n_added": n_added,
            "tp_added": tp_added,
            "fp_added": fp_added,
            "recall_missing": recall_missing,
            "add_precision": tp_added / max(n_added, 1),
        },
        "refined_skeleton": {
            "n_edges": len(new_skeleton_edges),
            "coverage": new_coverage,
            "precision": new_precision,
            "false_positives": new_fp,
        },
        "improvement": {
            "coverage_delta": new_coverage - skeleton_coverage,
            "precision_delta": new_precision - skeleton_precision,
            "fp_delta": new_fp - false_positives,
        },
        "edge_details": edge_details,
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Skeleton refinement via LLM")
    parser.add_argument("--network", default="insurance", help="Network name")
    parser.add_argument("--n-samples", type=int, default=10000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--k-passes", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--add-threshold", type=float, default=0.8,
                        help="Fraction of yes votes to add edge (default 0.8 = 4/5)")
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--smoketest", action="store_true")
    args = parser.parse_args()

    result = run_skeleton_refinement(
        args.network,
        n_samples=args.n_samples,
        alpha=args.alpha,
        k_passes=args.k_passes,
        concurrency=args.concurrency,
        add_threshold=args.add_threshold,
        max_candidates=args.max_candidates,
        enable_thinking=args.thinking,
        smoketest=args.smoketest,
    )

    # Print summary
    orig = result["original_skeleton"]
    ref = result["refinement"]
    new = result["refined_skeleton"]
    imp = result["improvement"]

    print(f"\n{'='*60}")
    print(f"SKELETON REFINEMENT: {args.network}")
    print(f"{'='*60}")
    print(f"Original: {orig['n_edges']} edges, "
          f"coverage={orig['coverage']:.1%}, precision={orig['precision']:.1%}")
    print(f"Candidates: {ref['n_candidates_queried']}, "
          f"GT missing: {ref['n_gt_missing']}")
    print(f"Added: {ref['n_added']} edges "
          f"(TP={ref['tp_added']}, FP={ref['fp_added']}, "
          f"precision={ref['add_precision']:.1%})")
    print(f"Missing edge recall: {ref['recall_missing']:.1%}")
    print(f"\nRefined: {new['n_edges']} edges, "
          f"coverage={new['coverage']:.1%} ({imp['coverage_delta']:+.1%}), "
          f"precision={new['precision']:.1%} ({imp['precision_delta']:+.1%})")

    # Per-candidate details
    print(f"\nPer-candidate results:")
    for edge_str, detail in sorted(result["edge_details"].items()):
        votes = detail["votes"]
        gt = "GT-MISS" if detail["is_gt_missing"] else "GT-ABSENT"
        action = "ADD" if detail["add"] else "skip"
        print(f"  {edge_str}: yes={votes['yes']} no={votes['no']} "
              f"unc={votes['uncertain']} → {action} [{gt}]")

    # Save
    out_dir = Path("projects/locale/experiments/results") / f"skeleton_{args.network}_{args.n_samples}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "refinement_results.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
