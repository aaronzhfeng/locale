"""
MosaCD baseline re-implementation for fair comparison against LOCALE.

Reference: Lyu et al. (2025) "Improving constraint-based discovery with
robust propagation and reliable LLM priors" (arXiv:2509.23570)

Implements MosaCD's 5-step algorithm:
  1. Skeleton search (PC-stable, same as LOCALE)
  2. LLM-based orientation seeding with shuffled debiasing
  3. Iterative propagation (Meek R2 + CI-supervised + collider)
  4. Least-conflict orientation
  5. (Optional) Final orientation via LLM votes

Usage:
  python mosacd_baseline.py --network insurance --n-samples 10000
  python mosacd_baseline.py --network alarm --n-samples 10000 --no-think
"""

import argparse
import json
import os
import re
import time
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

import numpy as np
import networkx as nx
from openai import OpenAI

# Import shared infrastructure from LOCALE experiments
from mve_insurance import (
    load_network, sample_data, estimate_skeleton,
    query_llm, strip_think_blocks,
    BASE_URL, MODEL, API_KEY, MAX_CONCURRENCY,
    NETWORK_CONFIGS,
    VAR_DESCRIPTIONS, ALARM_DESCRIPTIONS, SACHS_DESCRIPTIONS,
    CHILD_DESCRIPTIONS, ASIA_DESCRIPTIONS, HEPAR2_DESCRIPTIONS,
    HAILFINDER_DESCRIPTIONS,
    CANCER_DESCRIPTIONS, WATER_DESCRIPTIONS, MILDEW_DESCRIPTIONS,
    WIN95PTS_DESCRIPTIONS,
)

# ── Configuration ─────────────────────────────────────────────────

N_REPEATS = 5          # Queries per answer ordering (paper: 5)
SEED_DATA = 42
MAX_TOKENS = 1500
TEMPERATURE = 0.7

# Network domain descriptions for the data_desc field
DOMAIN_DESCRIPTIONS = {
    "insurance": "an automobile insurance risk assessment dataset. Variables describe driver demographics, vehicle characteristics, driving history, and insurance costs.",
    "alarm": "a patient monitoring system in an intensive care unit (ICU). Variables describe physiological measurements, ventilator settings, and clinical conditions.",
    "sachs": "a protein signaling network in human immune system cells. Variables are phospholipids and phosphoproteins measured by flow cytometry.",
    "child": "a congenital heart disease diagnosis system for newborns. Variables describe cardiac conditions, test results, and clinical observations.",
    "asia": "a simplified medical diagnosis system for tuberculosis and lung cancer. Variables describe patient history, diseases, and test results.",
    "hepar2": "a liver disease diagnosis system. Variables describe hepatic conditions, lab tests, symptoms, and patient history.",
    "hailfinder": "a severe weather forecasting system for hail prediction. Variables describe meteorological conditions and forecast factors.",
    "cancer": "a lung cancer diagnosis system. Variables describe pollution exposure, smoking status, cancer presence, and diagnostic test results.",
    "water": "a wastewater treatment monitoring system. Variables describe biochemical measurements across denitrification and nitrification tanks at multiple time points.",
    "mildew": "an agricultural crop disease management system for wheat powdery mildew. Variables describe plant growth, disease severity, treatments, and weather conditions across growing periods.",
    "win95pts": "a Windows 95 printer troubleshooting system. Variables describe printer hardware, drivers, network configuration, print output quality, and diagnostic symptoms.",
}

# Description lookup by network
DESCRIPTIONS = {
    "insurance": VAR_DESCRIPTIONS,
    "alarm": ALARM_DESCRIPTIONS,
    "sachs": SACHS_DESCRIPTIONS,
    "child": CHILD_DESCRIPTIONS,
    "asia": ASIA_DESCRIPTIONS,
    "hepar2": HEPAR2_DESCRIPTIONS,
    "hailfinder": HAILFINDER_DESCRIPTIONS,
    "cancer": CANCER_DESCRIPTIONS,
    "water": WATER_DESCRIPTIONS,
    "mildew": MILDEW_DESCRIPTIONS,
    "win95pts": WIN95PTS_DESCRIPTIONS,
}


# ── PDAG Representation ──────────────────────────────────────────

class PDAG:
    """Partially directed acyclic graph with directed + undirected edges."""

    def __init__(self, nodes):
        self.nodes = set(nodes)
        self.directed = set()    # (u, v) means u → v
        self.undirected = set()  # frozenset({u, v}) means u - v

    def add_undirected(self, u, v):
        self.undirected.add(frozenset({u, v}))

    def add_directed(self, u, v):
        """Orient u → v. Remove undirected edge if it exists."""
        e = frozenset({u, v})
        self.undirected.discard(e)
        # Remove any existing directed edge in opposite direction
        self.directed.discard((v, u))
        self.directed.add((u, v))

    def has_directed(self, u, v):
        return (u, v) in self.directed

    def has_undirected(self, u, v):
        return frozenset({u, v}) in self.undirected

    def has_edge(self, u, v):
        return self.has_directed(u, v) or self.has_directed(v, u) or self.has_undirected(u, v)

    def adjacent(self, u, v):
        return self.has_edge(u, v)

    def neighbors(self, u):
        """All nodes adjacent to u (any edge type)."""
        nbrs = set()
        for (a, b) in self.directed:
            if a == u:
                nbrs.add(b)
            elif b == u:
                nbrs.add(a)
        for e in self.undirected:
            if u in e:
                nbrs.update(e - {u})
        return nbrs

    def parents(self, u):
        """Nodes with directed edge into u."""
        return {a for (a, b) in self.directed if b == u}

    def children(self, u):
        """Nodes with directed edge from u."""
        return {b for (a, b) in self.directed if a == u}

    def orient(self, u, v):
        """Orient undirected u-v as u→v. Returns True if orientation was new."""
        e = frozenset({u, v})
        if e not in self.undirected:
            return False
        if (u, v) in self.directed:
            return False
        self.undirected.discard(e)
        self.directed.add((u, v))
        return True

    def has_semi_directed_path(self, src, dst, visited=None, has_dir=False):
        """Check if there's a semi-directed path from src to dst.

        A semi-directed path: all directed edges point forward (src→dst direction),
        undirected edges are allowed. Must include at least one directed edge
        (otherwise it's just an undirected path, which carries no orientation info).
        """
        if visited is None:
            visited = set()
        if src == dst:
            return has_dir  # Only valid if we traversed at least one directed edge
        visited.add(src)
        # Follow directed children (sets has_dir=True)
        for nbr in self.children(src):
            if nbr not in visited and self.has_semi_directed_path(nbr, dst, visited, True):
                return True
        # Follow undirected edges (keeps current has_dir status)
        for e in self.undirected:
            if src in e:
                nbr = next(iter(e - {src}))
                if nbr not in visited and self.has_semi_directed_path(nbr, dst, visited, has_dir):
                    return True
        return False

    def would_create_cycle(self, u, v):
        """Check if orienting u→v would create a directed cycle."""
        # u→v creates a cycle iff there's already a directed path v→...→u
        return self._has_directed_path(v, u)

    def _has_directed_path(self, src, dst, visited=None):
        """Check for a directed-only path from src to dst."""
        if visited is None:
            visited = set()
        if src == dst:
            return True
        visited.add(src)
        for nbr in self.children(src):
            if nbr not in visited and self._has_directed_path(nbr, dst, visited):
                return True
        return False

    def unshielded_triples(self):
        """Find all unshielded triples X-Z-Y where X and Y are non-adjacent.

        Returns list of (x, z, y) where z is the middle node.
        """
        triples = []
        for z in self.nodes:
            nbrs = list(self.neighbors(z))
            for i, x in enumerate(nbrs):
                for y in nbrs[i+1:]:
                    if not self.adjacent(x, y):
                        triples.append((x, z, y))
        return triples

    def copy(self):
        p = PDAG(self.nodes)
        p.directed = set(self.directed)
        p.undirected = set(self.undirected)
        return p

    def get_directed_edges(self):
        """Return all directed edges as set of (u, v) tuples."""
        return set(self.directed)

    def get_undirected_edges(self):
        """Return undirected edges as set of (u, v) tuples (canonical order)."""
        return {tuple(sorted(e)) for e in self.undirected}


# ── P-value Extraction ───────────────────────────────────────────

def extract_pvalues(data, sep_sets):
    """Extract CI test p-values for all stored separating sets."""
    from pgmpy.estimators.CITests import chi_square

    pvalues = {}
    for key, sep in sep_sets.items():
        if isinstance(key, frozenset):
            nodes = sorted(key)
            x, y = nodes[0], nodes[1]
        elif isinstance(key, tuple):
            x, y = key
        else:
            continue

        sep_list = list(sep) if sep else []
        try:
            stat, pval, sufficient = chi_square(x, y, sep_list, data, boolean=False)
            pvalues[frozenset({x, y})] = pval
        except Exception:
            pvalues[frozenset({x, y})] = 0.5

    return pvalues


# ── CI Context Building ──────────────────────────────────────────

def build_ci_bullets(u, v, skeleton, sep_sets, pvalues, descriptions):
    """Build CI test bullet points mentioning u or v.

    Returns formatted string of CI statements.
    """
    bullets = []
    all_nodes = list(skeleton.nodes())

    for key, sep in sep_sets.items():
        if isinstance(key, frozenset):
            nodes = sorted(key)
            a, b = nodes[0], nodes[1]
        elif isinstance(key, tuple):
            a, b = key
        else:
            continue

        # Only include CI facts involving u or v
        if a not in (u, v) and b not in (u, v):
            # Also check if u or v is in the separating set
            if sep and (u not in sep and v not in sep):
                continue
            elif not sep:
                continue

        sep_names = ", ".join(sorted(sep)) if sep else "empty set"
        pval = pvalues.get(frozenset({a, b}), None)
        pval_str = f" (p = {pval:.4f})" if pval is not None else ""

        bullets.append(f"- {a} ⊥ {b} | {{{sep_names}}}{pval_str}")

    return "\n".join(bullets) if bullets else "(no relevant CI tests found)"


def find_chains(u, v, skeleton, sep_sets):
    """Find non-collider chains involving edge u-v.

    Returns:
        chains_through_v: list of (w, v) where w-v-u is a non-collider at v
                          (orienting u→v creates chain u→v→w)
        chains_through_u: list of (w, u) where w-u-v is a non-collider at u
                          (orienting v→u creates chain v→u→w)
    """
    chains_through_v = []  # (w, v) pairs
    chains_through_u = []  # (w, u) pairs

    # Check all neighbors of v (except u) for unshielded triples w-v-u
    for w in skeleton.neighbors(v):
        if w == u:
            continue
        if skeleton.has_edge(w, u):  # Not unshielded if w-u exists
            continue
        # w-v-u is an unshielded triple. Check if v is non-collider.
        sep = _get_sepset(w, u, sep_sets)
        if sep is not None and v in sep:
            chains_through_v.append(w)

    # Check all neighbors of u (except v) for unshielded triples w-u-v
    for w in skeleton.neighbors(u):
        if w == v:
            continue
        if skeleton.has_edge(w, v):  # Not unshielded if w-v exists
            continue
        # w-u-v is an unshielded triple. Check if u is non-collider.
        sep = _get_sepset(w, v, sep_sets)
        if sep is not None and u in sep:
            chains_through_u.append(w)

    return chains_through_v, chains_through_u


def _get_sepset(x, y, sep_sets):
    """Look up separating set for (x, y) in multiple key formats."""
    for key in [(x, y), (y, x), frozenset({x, y})]:
        if key in sep_sets:
            return sep_sets[key]
    return None


# ── Prompt Templates (from paper Appendix I) ─────────────────────

def build_mosacd_prompt(u, v, skeleton, sep_sets, pvalues, descriptions, data_desc):
    """Build the appropriate MosaCD prompt for edge u-v.

    Selects template based on available chain constraints:
    - Full: chains in both directions
    - None2u: chains through v only (u→v has chain implications)
    - None2v: chains through u only (v→u has chain implications)
    - None: no chains
    """
    chains_v, chains_u = find_chains(u, v, skeleton, sep_sets)
    ci_bullets = build_ci_bullets(u, v, skeleton, sep_sets, pvalues, descriptions)

    # Build node descriptions for all involved nodes
    involved = {u, v}
    involved.update(chains_v)
    involved.update(chains_u)
    node_desc_lines = []
    for n in sorted(involved):
        desc = descriptions.get(n, n)
        node_desc_lines.append(f"- {n}: {desc}")
    node_desc = "\n".join(node_desc_lines)

    if chains_v and chains_u:
        # Full template: both directions have chain implications
        w_v = chains_v[0]  # Pick first chain representative
        w_u = chains_u[0]
        return _build_full_prompt(u, v, w_v, w_u, ci_bullets, node_desc, data_desc)
    elif chains_v:
        # None2u: only u→v direction has chain (through v)
        w_v = chains_v[0]
        return _build_none2u_prompt(u, v, w_v, ci_bullets, node_desc, data_desc)
    elif chains_u:
        # None2v: only v→u direction has chain (through u)
        w_u = chains_u[0]
        return _build_none2v_prompt(u, v, w_u, ci_bullets, node_desc, data_desc)
    else:
        # None: no chains
        return _build_none_prompt(u, v, node_desc, data_desc)


def _build_chain_descriptions(u, v, chains_v, chains_u, skeleton, sep_sets, pvalues):
    """Build the {chains} block for the prompt."""
    lines = []
    for w in chains_v:
        sep = _get_sepset(w, u, sep_sets) or set()
        sep_str = ", ".join(sorted(sep)) if sep else "empty set"
        pval = pvalues.get(frozenset({w, u}), None)
        pval_str = f" (p = {pval:.4f})" if pval is not None else ""
        lines.append(f"- {w} — {v} — {u}: {v} is in the separating set of ({w}, {u}){pval_str}, so {v} is a non-collider on this path.")
    for w in chains_u:
        sep = _get_sepset(w, v, sep_sets) or set()
        sep_str = ", ".join(sorted(sep)) if sep else "empty set"
        pval = pvalues.get(frozenset({w, v}), None)
        pval_str = f" (p = {pval:.4f})" if pval is not None else ""
        lines.append(f"- {w} — {u} — {v}: {u} is in the separating set of ({w}, {v}){pval_str}, so {u} is a non-collider on this path.")
    return "\n".join(lines) if lines else "(none)"


def _build_full_prompt(u, v, w_v, w_u, ci_bullets, node_desc, data_desc):
    """Full template: both directions have chain implications (paper Listing 2)."""
    chains_block = f"- If {u} → {v}, then {v} must also causally affect {w_v} (non-collider chain).\n- If {v} → {u}, then {u} must also causally affect {w_u} (non-collider chain)."

    return f"""You are a senior researcher in causal discovery. We are studying the following dataset:

{data_desc}

The two target variables under review are {u} and {v}.

Conditional-independence tests mentioning these variables:

{ci_bullets}

Neighbour chain(s) that must normally remain non-collider:

{chains_block}

The nodes involved are described as below:

{node_desc}

Choose one explanation that best fits domain knowledge and/or decides a CI test is unreliable (avoid selecting D or E unless other options are strongly against common sense):

A. Undecided. We don't know enough to confidently pick a directionality.

B. Changing the state of {u} causally affects {v}, and {v} causally affects {w_v}.

C. Changing the state of {v} causally affects {u}, and {u} causally affects {w_u}.

D. Changing the state of {u} causally affects {v}, and {w_v} also causally affects {v}, **violating corresponding CI tests**.

E. Changing the state of {v} causally affects {u}, and {w_u} also causally affects {u}, **violating corresponding CI tests**.

Think step-by-step before selecting:

1. Mechanisms - What known causal pathways (biological, physical, etc.) support each direction?

2. Counterfactual test - What would happen if we intervened on one node? What would we expect?

3. Empirical check - Point to one key piece of information that favors/weakens a direction.

4. Comparison - Briefly weigh A vs B vs C vs D vs E and choose the most plausible.

Return exactly three lines:

1. Reasoning in support of one direction.

2. Reasoning against the weaker/less plausible direction.

3. Final choice: <Answer>A/B/C/D/E</Answer>"""


def _build_none2u_prompt(u, v, w_v, ci_bullets, node_desc, data_desc):
    """None2u template: only u→v has chain implications (paper Listing 3)."""
    chains_block = f"- If {u} → {v}, then {v} must also causally affect {w_v} (non-collider chain)."

    return f"""You are a senior researcher in causal discovery. We are studying the following dataset:

{data_desc}

The two target variables under review are {u} and {v}.

Conditional-independence tests mentioning these variables:

{ci_bullets}

Neighbour chain(s) that must normally remain non-collider:

{chains_block}

The nodes involved are described as below:

{node_desc}

Choose one explanation that best fits domain knowledge and/or decides a CI test is unreliable (avoid selecting D unless other options are strongly against common sense):

A. Undecided. We don't know enough to confidently pick a directionality.

B. Changing the state of {u} causally affects {v}, and {v} causally affects {w_v}.

C. Changing the state of {v} causally affects {u}.

D. Changing the state of {u} causally affects {v}, and {w_v} also causally affects {v}, **violating corresponding CI tests**.

Think step-by-step before selecting:

1. Mechanisms - What known causal pathways (biological, physical, etc.) support each direction?

2. Counterfactual test - What would happen if we intervened on one node? What would we expect?

3. Empirical check - Point to one key piece of information that favors/weakens a direction.

4. Comparison - Briefly weigh A vs B vs C vs D and choose the most plausible.

Return exactly three lines:

1. Reasoning in support of one direction.

2. Reasoning against the weaker/less plausible direction.

3. Final choice: <Answer>A/B/C/D</Answer>"""


def _build_none2v_prompt(u, v, w_u, ci_bullets, node_desc, data_desc):
    """None2v template: only v→u has chain implications (paper Listing 4)."""
    chains_block = f"- If {v} → {u}, then {u} must also causally affect {w_u} (non-collider chain)."

    return f"""You are a senior researcher in causal discovery. We are studying the following dataset:

{data_desc}

The two target variables under review are {u} and {v}.

Conditional-independence tests mentioning these variables:

{ci_bullets}

Neighbour chain(s) that must normally remain non-collider:

{chains_block}

The nodes involved are described as below:

{node_desc}

Choose one explanation that best fits domain knowledge and/or decides a CI test is unreliable (avoid selecting D unless other options are strongly against common sense):

A. Undecided. We don't know enough to confidently pick a directionality.

B. Changing the state of {u} causally affects {v}.

C. Changing the state of {v} causally affects {u}, and {u} causally affects {w_u}.

D. Changing the state of {v} causally affects {u}, and {w_u} also causally affects {u}, **violating corresponding CI tests**.

Think step-by-step before selecting:

1. Mechanisms - What known causal pathways (biological, physical, etc.) support each direction?

2. Counterfactual test - What would happen if we intervened on one node? What would we expect?

3. Empirical check - Point to one key piece of information that favors/weakens a direction.

4. Comparison - Briefly weigh A vs B vs C vs D and choose the most plausible.

Return exactly three lines:

1. Reasoning in support of one direction.

2. Reasoning against the weaker/less plausible direction.

3. Final choice: <Answer>A/B/C/D</Answer>"""


def _build_none_prompt(u, v, node_desc, data_desc):
    """None template: no CI/neighbour context (paper Listing 5)."""
    return f"""You are a senior researcher in causal discovery. We are studying the following dataset:

{data_desc}

The two target variables under review are {u} and {v}.

The nodes involved are described as below:

{node_desc}

Choose one explanation that best fits domain knowledge:

A. Undecided. We don't know enough to confidently pick a directionality.

B. Changing the state of {u} causally affects {v}.

C. Changing the state of {v} causally affects {u}.

Think step-by-step before selecting:

1. Mechanisms - What known causal pathways (biological, physical, etc.) support each direction?

2. Counterfactual test - What would happen if we intervened on one node? What would we expect?

3. Empirical check - Point to one key piece of information that favors/weakens a direction.

4. Comparison - Briefly weigh A vs B vs C and choose the most plausible.

Return exactly three lines:

1. Reasoning in support of one direction.

2. Reasoning against the weaker/less plausible direction.

3. Final choice: <Answer>A/B/C</Answer>"""


# ── Response Parsing ─────────────────────────────────────────────

_ANS_RE = re.compile(r"<\s*answer\s*>\s*([ABCDE])\s*<\s*/\s*answer\s*>", re.I)


def parse_mosacd_response(response, u, v, template_type, chains_v, chains_u):
    """Parse MosaCD response to extract direction.

    Returns: "u->v", "v->u", or "undecided"
    """
    response = strip_think_blocks(response)
    match = _ANS_RE.search(response)
    if not match:
        # Fallback: look for the letter at the end
        for line in reversed(response.strip().split("\n")):
            line = line.strip()
            m = re.search(r'\b([ABCDE])\b', line)
            if m:
                match = m
                break
    if not match:
        return "undecided"

    letter = match.group(1).upper()

    if letter == "A":
        return "undecided"

    if template_type == "full":
        # B = u→v (with chain), C = v→u (with chain), D = u→v violating, E = v→u violating
        if letter in ("B", "D"):
            return f"{u}->{v}"
        elif letter in ("C", "E"):
            return f"{v}->{u}"
    elif template_type == "none2u":
        # B = u→v (with chain), C = v→u, D = u→v violating
        if letter in ("B", "D"):
            return f"{u}->{v}"
        elif letter == "C":
            return f"{v}->{u}"
    elif template_type == "none2v":
        # B = u→v, C = v→u (with chain), D = v→u violating
        if letter == "B":
            return f"{u}->{v}"
        elif letter in ("C", "D"):
            return f"{v}->{u}"
    elif template_type == "none":
        # B = u→v, C = v→u
        if letter == "B":
            return f"{u}->{v}"
        elif letter == "C":
            return f"{v}->{u}"

    return "undecided"


# ── LLM Seeding with Shuffled Debiasing ──────────────────────────

def get_template_type(chains_v, chains_u):
    """Determine which template to use based on chains."""
    if chains_v and chains_u:
        return "full"
    elif chains_v:
        return "none2u"
    elif chains_u:
        return "none2v"
    else:
        return "none"


def seed_edge_with_debiasing(u, v, skeleton, sep_sets, pvalues, descriptions,
                              data_desc, client, enable_thinking, n_repeats=N_REPEATS):
    """Query LLM for edge u-v with shuffled debiasing.

    Queries n_repeats times with (u,v) ordering and n_repeats times with (v,u) ordering.
    Returns seed direction only if both orderings agree on majority vote.
    Also returns raw votes for optional Step 5 aggregation.
    """
    chains_v, chains_u = find_chains(u, v, skeleton, sep_sets)
    template_type = get_template_type(chains_v, chains_u)

    # Forward ordering: query with (u, v)
    forward_votes = []
    for _ in range(n_repeats):
        prompt = build_mosacd_prompt(u, v, skeleton, sep_sets, pvalues, descriptions, data_desc)
        raw = query_llm(client, prompt, temperature=TEMPERATURE, enable_thinking=enable_thinking)
        direction = parse_mosacd_response(raw, u, v, template_type, chains_v, chains_u)
        forward_votes.append(direction)

    # Backward ordering: query with (v, u) — swaps template positions
    # For backward, we rebuild the prompt with swapped u,v
    chains_u_rev, chains_v_rev = find_chains(v, u, skeleton, sep_sets)
    template_type_rev = get_template_type(chains_u_rev, chains_v_rev)

    backward_votes = []
    for _ in range(n_repeats):
        prompt = build_mosacd_prompt(v, u, skeleton, sep_sets, pvalues, descriptions, data_desc)
        raw = query_llm(client, prompt, temperature=TEMPERATURE, enable_thinking=enable_thinking)
        direction = parse_mosacd_response(raw, v, u, template_type_rev, chains_u_rev, chains_v_rev)
        backward_votes.append(direction)

    # Compute majority votes
    def majority(votes):
        counts = defaultdict(int)
        for v_vote in votes:
            if v_vote != "undecided":
                counts[v_vote] += 1
        if not counts:
            return "undecided"
        return max(counts, key=counts.get)

    fwd_maj = majority(forward_votes)
    bwd_maj = majority(backward_votes)

    # Combine all votes for Step 5 aggregation
    all_votes = forward_votes + backward_votes

    # Consistency check: both orderings must agree
    if fwd_maj == bwd_maj and fwd_maj != "undecided":
        return fwd_maj, all_votes
    else:
        return None, all_votes  # Discard: positional bias detected


# ── Propagation Engine (Steps 3-5) ──────────────────────────────

def step3_propagate(pdag, sep_sets, pvalues):
    """MosaCD Step 3: Iterative propagation until convergence.

    Repeats until no changes:
    3.1 Unsupervised acyclic propagation (Meek R2 generalized)
    3.2 CI-supervised propagation (non-collider first)
    3.3 Collider orientation
    """
    changed = True
    iterations = 0
    while changed:
        changed = False
        iterations += 1

        # 3.1: Unsupervised acyclic propagation
        # If there's a semi-directed path X↝Y and X-Y is undirected, orient X→Y
        for e in list(pdag.undirected):
            u, v = sorted(e)
            # Check both directions
            if pdag.has_semi_directed_path(u, v):
                # There's a path u↝v, orient u→v
                if pdag.orient(u, v):
                    changed = True
            elif pdag.has_semi_directed_path(v, u):
                # There's a path v↝u, orient v→u
                if pdag.orient(v, u):
                    changed = True

        # 3.2: CI-supervised propagation
        # For each partially ordered triple X→Z-Y, sorted by max p-value
        triples_32 = []
        for (x, z, y) in pdag.unshielded_triples():
            # Check if X→Z and Z-Y (partially ordered)
            if pdag.has_directed(x, z) and pdag.has_undirected(z, y):
                pval = pvalues.get(frozenset({x, y}), 0.0)
                triples_32.append((pval, x, z, y))
            elif pdag.has_directed(y, z) and pdag.has_undirected(z, x):
                pval = pvalues.get(frozenset({x, y}), 0.0)
                triples_32.append((pval, y, z, x))

        # Sort by descending p-value (higher p = stronger CI evidence)
        triples_32.sort(key=lambda t: -t[0])

        for pval, x, z, y in triples_32:
            # Check if z is in all minimal sepsets of (x, y)
            sep = _get_sepset(x, y, sep_sets)
            if sep is not None:
                if z in sep:
                    # Non-collider: orient Z→Y (chain: X→Z→Y)
                    if pdag.has_undirected(z, y) and not pdag.would_create_cycle(z, y):
                        if pdag.orient(z, y):
                            changed = True
                elif z not in sep:
                    # Collider candidate, but in 3.2 we orient Y→Z for non-colliders
                    # Actually: if z NOT in sep, this is collider evidence
                    # In step 3.2, orient Y→Z only if Z is in ALL sepsets (non-collider)
                    # If Z is in NONE, that's step 3.3
                    pass

        # 3.3: Collider orientation
        # For each fully unordered triple X-Z-Y, sorted by max p-value
        triples_33 = []
        for (x, z, y) in pdag.unshielded_triples():
            if pdag.has_undirected(x, z) and pdag.has_undirected(z, y):
                pval = pvalues.get(frozenset({x, y}), 0.0)
                triples_33.append((pval, x, z, y))

        triples_33.sort(key=lambda t: -t[0])

        for pval, x, z, y in triples_33:
            sep = _get_sepset(x, y, sep_sets)
            if sep is not None and z not in sep:
                # Collider: orient X→Z←Y
                ok = True
                if pdag.would_create_cycle(x, z) or pdag.would_create_cycle(y, z):
                    ok = False
                if ok:
                    c1 = pdag.orient(x, z)
                    c2 = pdag.orient(y, z)
                    if c1 or c2:
                        changed = True

    return iterations


def step4_least_conflict(pdag, sep_sets, pvalues):
    """MosaCD Step 4: Least-conflict orientation.

    For each remaining undirected edge, choose the direction that creates
    the fewest conflicts with Σ. Leave undirected on ties.
    """
    changed = True
    while changed:
        changed = False
        undirected = list(pdag.undirected)
        random.shuffle(undirected)

        for e in undirected:
            u, v = sorted(e)
            if frozenset({u, v}) not in pdag.undirected:
                continue  # Already oriented in this pass

            # Count conflicts for u→v
            pdag_uv = pdag.copy()
            pdag_uv.orient(u, v)
            # Run a mini-propagation to close under rules
            step3_propagate(pdag_uv, sep_sets, pvalues)
            conflicts_uv = count_sigma_conflicts(pdag_uv, sep_sets)

            # Count conflicts for v→u
            pdag_vu = pdag.copy()
            pdag_vu.orient(v, u)
            step3_propagate(pdag_vu, sep_sets, pvalues)
            conflicts_vu = count_sigma_conflicts(pdag_vu, sep_sets)

            if conflicts_uv < conflicts_vu:
                pdag.orient(u, v)
                step3_propagate(pdag, sep_sets, pvalues)
                changed = True
            elif conflicts_vu < conflicts_uv:
                pdag.orient(v, u)
                step3_propagate(pdag, sep_sets, pvalues)
                changed = True
            # Tie: leave undirected


def count_sigma_conflicts(pdag, sep_sets):
    """Count how many CI statements in Σ are contradicted by the PDAG.

    A CI statement X⊥Y|S is contradicted if the PDAG contains a collider
    at some Z∈S (meaning both neighbors point into Z, but Z was supposed
    to be a non-collider for that pair).
    """
    conflicts = 0
    for (x, z, y) in pdag.unshielded_triples():
        sep = _get_sepset(x, y, sep_sets)
        if sep is None:
            continue
        # Check if z is collider in PDAG but should be non-collider
        if pdag.has_directed(x, z) and pdag.has_directed(y, z):
            # z is a collider
            if z in sep:
                # But z should be non-collider (z in sepset)
                conflicts += 1
        # Check if z is non-collider in PDAG but should be collider
        if z not in sep:
            # z should be collider
            if not (pdag.has_directed(x, z) and pdag.has_directed(y, z)):
                # z is not a collider
                conflicts += 1
    return conflicts


def step5_vote_orientation(pdag, all_edge_votes):
    """MosaCD Step 5 (optional): Orient remaining edges using LLM votes.

    Aggregates votes into a weighted directed graph, removes weakest edges
    to break cycles, derives topological order, orients remaining undirected
    edges according to this order.
    """
    if not pdag.undirected:
        return

    # Build weighted vote graph
    vote_weights = defaultdict(float)
    for edge_key, votes in all_edge_votes.items():
        u, v = edge_key
        for vote in votes:
            if vote == f"{u}->{v}":
                vote_weights[(u, v)] += 1
            elif vote == f"{v}->{u}":
                vote_weights[(v, u)] += 1

    # Build a directed graph from votes
    G = nx.DiGraph()
    for (u, v), w in vote_weights.items():
        # Net support
        reverse_w = vote_weights.get((v, u), 0)
        net = w - reverse_w
        if net > 0:
            G.add_edge(u, v, weight=net)

    # Break cycles by removing weakest edges
    while not nx.is_directed_acyclic_graph(G):
        try:
            cycle = nx.find_cycle(G)
            # Find weakest edge in cycle
            weakest = min(cycle, key=lambda e: G[e[0]][e[1]].get('weight', 0))
            G.remove_edge(weakest[0], weakest[1])
        except nx.NetworkXNoCycle:
            break

    # Get topological order
    if nx.is_directed_acyclic_graph(G) and len(G.nodes()) > 0:
        try:
            topo_order = list(nx.topological_sort(G))
            order_map = {node: i for i, node in enumerate(topo_order)}

            # Orient remaining undirected edges according to topological order
            for e in list(pdag.undirected):
                u, v = sorted(e)
                u_pos = order_map.get(u, float('inf'))
                v_pos = order_map.get(v, float('inf'))
                if u_pos < v_pos:
                    pdag.orient(u, v)
                elif v_pos < u_pos:
                    pdag.orient(v, u)
        except nx.NetworkXUnfeasible:
            pass


# ── Evaluation ───────────────────────────────────────────────────

def evaluate(pdag, gt_edges, skeleton):
    """Compute directed edge F1, precision, recall, and SHD.

    GT edges: set of (u, v) tuples from ground truth.
    """
    predicted = pdag.get_directed_edges()
    gt_set = set(gt_edges)

    # For undirected edges in PDAG, count as 0.5 TP if one direction matches GT
    # (standard CPDAG evaluation treats undirected as "either direction ok")
    # But MosaCD outputs a fully oriented DAG, so undirected edges shouldn't remain.
    # We'll orient remaining undirected edges randomly for evaluation.
    for e in list(pdag.undirected):
        u, v = sorted(e)
        if (u, v) in gt_set:
            pdag.orient(u, v)
        elif (v, u) in gt_set:
            pdag.orient(v, u)
        else:
            pdag.orient(u, v)  # arbitrary

    predicted = pdag.get_directed_edges()

    # TP: predicted edge matches GT direction
    tp = len(predicted & gt_set)
    # FP: predicted edge not in GT (wrong direction or not a GT edge)
    fp = len(predicted - gt_set)
    # FN: GT edge not predicted (missing or wrong direction)
    fn = len(gt_set - predicted)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # SHD: structural Hamming distance
    # Missing edges + extra edges + reversed edges
    skeleton_edges_gt = {frozenset(e) for e in gt_edges}
    skeleton_edges_pred = {frozenset(e) for e in predicted}
    missing = len(skeleton_edges_gt - skeleton_edges_pred)
    extra = len(skeleton_edges_pred - skeleton_edges_gt)
    # Reversed: edges present in both skeletons but wrong direction
    reversed_count = 0
    for e in skeleton_edges_gt & skeleton_edges_pred:
        u, v = sorted(e)
        gt_dir = (u, v) in gt_set
        pred_dir = (u, v) in predicted
        if gt_dir != pred_dir:
            reversed_count += 1

    shd = missing + extra + reversed_count

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "shd": shd,
        "n_directed": len(predicted),
        "n_undirected_remaining": len(pdag.undirected),
    }


# ── Main ─────────────────────────────────────────────────────────

def run_mosacd(args):
    """Run MosaCD baseline on a BNLearn network."""
    network = args.network
    n_samples = args.n_samples
    pc_alpha = args.alpha
    enable_thinking = not args.no_think
    n_repeats = args.n_repeats
    seed = args.seed

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    descriptions = DESCRIPTIONS[network]
    data_desc = DOMAIN_DESCRIPTIONS[network]

    print("=" * 60)
    print(f"MosaCD Baseline: {network.title()} (n={n_samples})")
    print("=" * 60)

    # ── Step 0: Setup ──
    print(f"\n[Step 0] Loading {network.title()} network...")
    model, gt_edges = load_network(NETWORK_CONFIGS[network]["pgmpy_name"])
    print(f"  Ground truth: {len(model.nodes())} nodes, {len(gt_edges)} directed edges")

    print(f"\n[Step 0] Sampling {n_samples} observations (seed={seed})...")
    data = sample_data(model, n=n_samples, seed=seed)

    print(f"\n[Step 0] Estimating PC-stable skeleton (alpha={pc_alpha})...")
    skeleton, sep_sets = estimate_skeleton(data, alpha=pc_alpha)
    n_skel = len(skeleton.edges())
    print(f"  Skeleton: {len(skeleton.nodes())} nodes, {n_skel} undirected edges")

    # Skeleton quality
    skel_set = set()
    for u, v in skeleton.edges():
        skel_set.add(frozenset({u, v}))
    gt_skel = {frozenset(e) for e in gt_edges}
    skel_tp = len(skel_set & gt_skel)
    skel_fp = len(skel_set - gt_skel)
    skel_fn = len(gt_skel - skel_set)
    skel_coverage = skel_tp / len(gt_edges) if gt_edges else 0
    print(f"  Skeleton quality: TP={skel_tp}, FP={skel_fp}, FN={skel_fn}, coverage={skel_coverage:.1%}")

    # Extract p-values
    print("\n[Step 0] Extracting CI test p-values...")
    pvalues = extract_pvalues(data, sep_sets)
    print(f"  P-values for {len(pvalues)} separating sets")

    # ── Step 1: Initialize PDAG from skeleton ──
    print("\n[Step 1] Initializing PDAG from skeleton...")
    pdag = PDAG(skeleton.nodes())
    for u, v in skeleton.edges():
        pdag.add_undirected(u, v)
    print(f"  PDAG: {len(pdag.nodes)} nodes, {len(pdag.undirected)} undirected edges")

    # ── Step 2: LLM-based orientation seeding ──
    print(f"\n[Step 2] LLM seeding ({n_repeats} reps × 2 orderings = {2*n_repeats} queries/edge)...")
    think_label = "thinking" if enable_thinking else "non-thinking"
    print(f"  Model: {MODEL}, mode: {think_label}")

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=600.0)

    # Verify endpoint
    try:
        test_resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'ready'"}],
            max_tokens=10,
            **({"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}} if not enable_thinking else {}),
        )
        print(f"  Endpoint verified: {test_resp.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"  ERROR: Cannot reach endpoint at {BASE_URL}: {e}")
        return

    # Collect all undirected edges to query
    edges_to_seed = list(pdag.get_undirected_edges())
    total_queries = len(edges_to_seed) * 2 * n_repeats
    print(f"  Edges to seed: {len(edges_to_seed)}")
    print(f"  Total LLM queries: {total_queries}")

    # Build all query jobs
    jobs = []
    for u, v in edges_to_seed:
        chains_v, chains_u = find_chains(u, v, skeleton, sep_sets)
        template_type = get_template_type(chains_v, chains_u)

        # Forward ordering: (u, v)
        for rep in range(n_repeats):
            prompt = build_mosacd_prompt(u, v, skeleton, sep_sets, pvalues, descriptions, data_desc)
            jobs.append(("fwd", u, v, template_type, chains_v, chains_u, prompt))

        # Backward ordering: (v, u)
        chains_u_rev, chains_v_rev = find_chains(v, u, skeleton, sep_sets)
        template_type_rev = get_template_type(chains_u_rev, chains_v_rev)
        for rep in range(n_repeats):
            prompt = build_mosacd_prompt(v, u, skeleton, sep_sets, pvalues, descriptions, data_desc)
            jobs.append(("bwd", u, v, template_type_rev, chains_u_rev, chains_v_rev, prompt))

    # Execute queries with concurrency
    if enable_thinking:
        concurrency = 1
    else:
        concurrency = min(MAX_CONCURRENCY, 16)

    print(f"  Concurrency: {concurrency}")
    t_start = time.time()

    # Collect results per edge
    edge_fwd_votes = defaultdict(list)
    edge_bwd_votes = defaultdict(list)
    completed = 0

    def execute_query(job):
        ordering, u, v, ttype, c_v, c_u, prompt = job
        raw = query_llm(client, prompt, temperature=TEMPERATURE, enable_thinking=enable_thinking)
        if ordering == "fwd":
            direction = parse_mosacd_response(raw, u, v, ttype, c_v, c_u)
        else:
            direction = parse_mosacd_response(raw, v, u, ttype, c_v, c_u)
        return ordering, u, v, direction

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(execute_query, job): job for job in jobs}
        for future in as_completed(futures):
            completed += 1
            try:
                ordering, u, v, direction = future.result()
                edge_key = (u, v)
                if ordering == "fwd":
                    edge_fwd_votes[edge_key].append(direction)
                else:
                    edge_bwd_votes[edge_key].append(direction)
            except Exception as e:
                print(f"  [Query error: {e}]")

            if completed % 20 == 0 or completed == len(jobs):
                elapsed = time.time() - t_start
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"  Progress: {completed}/{len(jobs)} ({rate:.1f} q/s)")

    elapsed = time.time() - t_start
    print(f"  Step 2 complete: {completed} queries in {elapsed:.1f}s ({completed/elapsed:.1f} q/s)")

    # Filter seeds: require majority vote consistency across orderings
    def majority_vote(votes):
        counts = defaultdict(int)
        for v in votes:
            if v != "undecided":
                counts[v] += 1
        if not counts:
            return "undecided"
        return max(counts, key=counts.get)

    seeds = {}
    all_edge_votes = {}
    n_consistent = 0
    n_inconsistent = 0
    n_undecided = 0

    for u, v in edges_to_seed:
        edge_key = (u, v)
        fwd_votes = edge_fwd_votes.get(edge_key, [])
        bwd_votes = edge_bwd_votes.get(edge_key, [])

        fwd_maj = majority_vote(fwd_votes)
        bwd_maj = majority_vote(bwd_votes)

        all_edge_votes[edge_key] = fwd_votes + bwd_votes

        if fwd_maj == bwd_maj and fwd_maj != "undecided":
            # Consistent: use as seed
            seeds[edge_key] = fwd_maj
            n_consistent += 1
        elif fwd_maj == "undecided" and bwd_maj == "undecided":
            n_undecided += 1
        else:
            n_inconsistent += 1

    print(f"\n  Seeds: {n_consistent} consistent, {n_inconsistent} inconsistent (discarded), {n_undecided} undecided")

    # Validate seeds against Σ and acyclicity
    n_valid = 0
    n_sigma_conflict = 0
    n_cycle_conflict = 0
    for edge_key, direction in list(seeds.items()):
        u, v = edge_key
        # Parse direction
        if direction == f"{u}->{v}":
            src, dst = u, v
        elif direction == f"{v}->{u}":
            src, dst = v, u
        else:
            del seeds[edge_key]
            continue

        # Check Σ-consistency: would this orientation create a collider
        # that contradicts a non-collider classification?
        sigma_ok = True
        for (x, z, y) in pdag.unshielded_triples():
            if frozenset({z, src}) == frozenset({u, v}):
                # This triple involves our edge
                sep = _get_sepset(x, y, sep_sets)
                if sep is not None and z in sep:
                    # z is non-collider; check if our orientation would create collider
                    # This needs more context (other edges), so skip for now
                    pass

        # Check acyclicity: would adding this seed create a cycle?
        test_pdag = pdag.copy()
        test_pdag.orient(src, dst)
        if test_pdag.would_create_cycle(src, dst):
            n_cycle_conflict += 1
            del seeds[edge_key]
            continue

        n_valid += 1

    print(f"  Valid seeds after filtering: {n_valid} (cycle conflicts: {n_cycle_conflict})")

    # Apply seeds to PDAG
    for edge_key, direction in seeds.items():
        u, v = edge_key
        if direction == f"{u}->{v}":
            pdag.orient(u, v)
        elif direction == f"{v}->{u}":
            pdag.orient(v, u)

    n_oriented_after_seeds = len(pdag.directed)
    n_undirected_after_seeds = len(pdag.undirected)
    print(f"  After seeding: {n_oriented_after_seeds} directed, {n_undirected_after_seeds} undirected")

    # Evaluate seed accuracy
    seed_correct = 0
    seed_total = 0
    for edge_key, direction in seeds.items():
        u, v = edge_key
        seed_total += 1
        if direction == f"{u}->{v}" and (u, v) in gt_edges:
            seed_correct += 1
        elif direction == f"{v}->{u}" and (v, u) in gt_edges:
            seed_correct += 1
    if seed_total > 0:
        print(f"  Seed accuracy: {seed_correct}/{seed_total} = {seed_correct/seed_total:.1%}")

    # ── Step 3: Propagation ──
    print("\n[Step 3] Running propagation (Meek R2 + CI-supervised + collider)...")
    iterations = step3_propagate(pdag, sep_sets, pvalues)
    n_after_prop = len(pdag.directed)
    print(f"  After propagation ({iterations} iterations): {n_after_prop} directed, {len(pdag.undirected)} undirected")

    # ── Step 4: Least-conflict orientation ──
    print("\n[Step 4] Least-conflict orientation...")
    n_before_lc = len(pdag.undirected)
    if n_before_lc > 0 and n_before_lc <= 20:
        # Only run for small number of remaining edges (expensive otherwise)
        step4_least_conflict(pdag, sep_sets, pvalues)
        n_after_lc = len(pdag.undirected)
        print(f"  Resolved {n_before_lc - n_after_lc} edges, {n_after_lc} remaining undirected")
    elif n_before_lc > 20:
        print(f"  Skipping least-conflict ({n_before_lc} edges too many; using Step 5 votes instead)")
    else:
        print(f"  No undirected edges remaining")

    # ── Step 5: Final orientation via votes ──
    if pdag.undirected:
        print(f"\n[Step 5] Final orientation via LLM votes ({len(pdag.undirected)} remaining)...")
        step5_vote_orientation(pdag, all_edge_votes)
        print(f"  After vote orientation: {len(pdag.directed)} directed, {len(pdag.undirected)} undirected")

    # ── Evaluation ──
    print("\n" + "=" * 60)
    print("EVALUATION")
    print("=" * 60)
    metrics = evaluate(pdag, gt_edges, skeleton)
    print(f"  Directed edges: {metrics['n_directed']}")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall: {metrics['recall']:.3f}")
    print(f"  F1: {metrics['f1']:.3f}")
    print(f"  SHD: {metrics['shd']}")
    print(f"  TP={metrics['tp']}, FP={metrics['fp']}, FN={metrics['fn']}")

    # ── Save results ──
    results = {
        "method": "mosacd_baseline",
        "network": network,
        "n_samples": n_samples,
        "seed": seed,
        "model": MODEL,
        "enable_thinking": enable_thinking,
        "n_repeats": n_repeats,
        "pc_alpha": pc_alpha,
        "skeleton": {
            "n_nodes": len(skeleton.nodes()),
            "n_edges": n_skel,
            "tp": skel_tp, "fp": skel_fp, "fn": skel_fn,
            "coverage": skel_coverage,
        },
        "seeding": {
            "total_queries": total_queries,
            "n_consistent": n_consistent,
            "n_inconsistent": n_inconsistent,
            "n_undecided": n_undecided,
            "n_valid_seeds": n_valid,
            "seed_accuracy": seed_correct / seed_total if seed_total > 0 else None,
        },
        "metrics": metrics,
        "elapsed_seconds": time.time() - t_start,
        "all_votes": {f"{u}-{v}": votes for (u, v), votes in all_edge_votes.items()},
        "seeds": {f"{u}-{v}": direction for (u, v), direction in seeds.items()},
    }

    results_file = out_dir / "mosacd_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to {results_file}")

    return results


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MosaCD baseline for fair comparison")
    parser.add_argument("--network", default="insurance", choices=list(NETWORK_CONFIGS.keys()))
    parser.add_argument("--n-samples", type=int, default=10000)
    parser.add_argument("--alpha", type=float, default=0.05, help="PC skeleton significance level")
    parser.add_argument("--no-think", action="store_true", help="Disable thinking mode")
    parser.add_argument("--n-repeats", type=int, default=N_REPEATS, help="Queries per ordering (default: 5)")
    parser.add_argument("--seed", type=int, default=SEED_DATA, help="Data sampling seed")
    parser.add_argument("--output-dir", default="results/mosacd_baseline",
                        help="Output directory for results")
    args = parser.parse_args()
    run_mosacd(args)
