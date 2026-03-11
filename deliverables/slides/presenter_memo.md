# Presenter Memo — LOCALE

A complete study guide for the presenter. After reading this document, you should understand the full research context, every result, every design choice, and be able to present and field questions without any other preparation.

---

## Background: What Is This Research About?

### Causal discovery from observational data

Causal discovery is the problem of learning cause-and-effect relationships from data alone (no experiments). Given a dataset of observations — say, insurance claim records with 27 variables like Age, DrivingSkill, Accident, MedCost — we want to recover the directed acyclic graph (DAG) that describes which variables cause which.

The standard approach is **constraint-based causal discovery**, which works in two steps:

1. **Skeleton search**: Find which pairs of variables are connected (undirected edges). The PC algorithm does this by testing conditional independence (CI): "Are X and Y independent given Z?" If yes, no direct edge between X and Y. The output is an undirected graph + separating sets (the conditioning variables that made pairs independent).

2. **Edge orientation**: Turn undirected edges into directed edges (arrows). The PC algorithm uses "v-structures" (colliders) and Meek's propagation rules. But finite-sample CI tests make errors, and many edges remain ambiguous (the equivalence class problem).

### Where LLMs enter the picture

LLMs encode domain knowledge about causal relationships ("Age causes DrivingSkill, not the other way around"). Recent work uses LLMs to help orient the ambiguous edges from step 2. The key question is: how should we query the LLM?

### Three paradigms (the spectrum from our DSC 190 presentation)

1. **Per-edge methods** (MosaCD, chatPC): Ask the LLM about one edge at a time. "Is it Age→DrivingSkill or DrivingSkill→Age?" Simple, but each query uses ~200 tokens out of a 128K context window. The LLM acts as a binary classifier. No local consistency — the LLM might say A→B, B→C, and C→A (a cycle) because each query is independent. Requires O(E × K) queries where E is edge count and K is vote repetitions (typically 10).

2. **Whole-graph methods** (CausalFusion, CauScientist): Show the LLM the entire DAG and ask it to edit. Rich context, but O(V²) tokens per query. Doesn't scale. The LLM ends up doing what Meek's rules already do perfectly (global consistency checking).

3. **Ego-graph methods** (LOCALE — ours): Show the LLM one node's neighborhood — the node, all its neighbors, and the CI relationships between them. The LLM orients all incident edges jointly. O(d) tokens per query (d = node degree), O(N × K) total queries. The LLM reasons about local mechanisms while seeing the constraints.

### MosaCD — the key predecessor (from our DSC 190 presentation)

MosaCD (Lyu et al., CMU, 2025) is the closest baseline. It uses the PC skeleton, queries the LLM per-edge with 10 shuffled repetitions (to detect positional bias), and propagates confident orientations using a non-collider-first strategy. It achieved best F1 in 9/10 benchmarks. Key innovations:

- **Shuffled queries**: Repeat each query with answer order randomized. If the LLM's answer flips with order, it's uncertain — discard. This filters hallucinations.
- **Non-collider-first propagation**: Orient edges where the evidence says "not a collider" before edges where the evidence says "collider." Empirically much more reliable. They proved theoretically (Theorem 5.5, simplified model) that collider FPR >> non-collider FPR.

MosaCD was submitted to ICLR 2026 and rejected (scores: 8, 4, 4, 2). Key reviewer concern: shuffled queries for positional bias is a known technique, not novel. They added 8 new baselines in rebuttal. The paper is under revision.

### The gap we identified

During DSC 190 presentation prep (March 2, 2026), while deeply studying MosaCD and the Wan et al. survey, we noticed: per-edge methods waste the LLM's context window (200 tokens out of 128K), and they can't check local consistency across edges. Whole-graph methods don't scale. The ego-graph is the underexplored middle ground — rich enough for mechanism reasoning, bounded enough to be auditable, naturally matched to the local structure in PC/CPC algorithms.

This became the LOCALE project.

---

## The LOCALE Pipeline (What We Built)

### Overview

LOCALE is a 4-phase orientation layer that sits on top of a standard PC-stable skeleton. The LLM does not alter the skeleton, separating sets, or CI test results. It only orients ambiguous edges.

### Phase 0: Skeleton (standard, no LLM)

Run PC-stable on observational data. Output: undirected skeleton + separating sets + CI p-values. This is identical to what MosaCD uses. We use n=10,000 samples and alpha=0.05 for CI testing.

**Skeleton quality matters enormously**: if the skeleton misses a true edge, no orientation method can recover it. This becomes a key finding (see Slide 7).

### Phase 1: Ego-graph LLM scoring

For each node v with degree ≥ 2:
1. Construct the ego graph: v, all neighbors N(v), neighbor-neighbor adjacencies, CI facts (which pairs are separated by v, which are not).
2. Build a structured prompt showing: the center node with description, all neighbors with descriptions, statistical constraints from CI tests (non-collider/collider rules), and the task instruction.
3. Run K=10 stochastic passes with temperature variation and shuffled neighbor order (debiasing). Parse structured JSON responses.
4. Collect vote counts for each edge direction.

**The key mathematical insight**: Each ego-graph orientation is a weighted 2-SAT instance. CI-derived constraints (phi) define the feasible set of local orientations. LLM domain knowledge (psi) provides soft scores within that set. Per-edge methods compute psi without phi. Only ego-graph queries give the LLM both simultaneously — the joint phi × psi optimization.

**Model**: Qwen3.5-27B-FP8 running on RunPod vLLM (A40 GPU). Open-source, local inference. Not a proprietary API.

### Phase 2: Max-2SAT with NCO constraints

For each node, compile the ego-graph votes into a constrained optimization:

- **Hard constraints**: From CI-derived non-collider evidence only (NCO mode). If v is in the separating set of neighbors u and w, then u and w cannot BOTH be parents of v: NOT(b_u=1 AND b_w=1) as a 2-SAT clause.
- **Soft objective**: Maximize the sum of LLM vote scores for the chosen direction of each edge.
- **Solver**: Exact enumeration over 2^d assignments (feasible for d ≤ 8, which covers all benchmark nodes).

**Why NCO (non-collider only)?** This is one of our key discoveries. We found that ~98% of incorrect CI-derived facts are false colliders (PC says "collider" when truth is "non-collider"). Zero or near-zero false non-colliders. So collider constraints are unreliable and we drop them. Non-collider constraints are always reliable. (Full explanation in Slide 8 section below.)

### Phase 3: Confidence-weighted reconciliation

Each edge (u, v) gets orientations from two ego-graphs: Ego(u) and Ego(v). These may agree or disagree. Reconciliation strategy: the endpoint with higher vote margin wins.

**Why not Dawid-Skene?** The proposal called for Dawid-Skene multi-rater aggregation. We built and tested it. It underperforms simple majority vote because there are only 2 "annotators" per edge — too sparse for EM to estimate meaningful confusion matrices.

### Phase 4: Safety valve

Compare Phase 2 (with constraints) to Phase 1 (without constraints) per node. If Phase 2 hurt accuracy at a node, revert that node's edges to Phase 1 orientations. Also break any cycles by flipping the lowest-confidence edge.

**This is the largest single contributor in ablation (+2.5pp)**. It ensures the pipeline is monotonically non-decreasing — adding constraints and reconciliation never hurts overall accuracy, because damage is detected and reverted.

### What about iterative expansion?

The original proposal (from the raw idea document) described a Survey Propagation-style iterative approach: query seed nodes in Round 1, commit high-confidence edges, then query frontier nodes in Round 2+ with established orientations as additional context. This was formally mapped to SP (variables = edge orientations, factors = ego-graph queries, decimation = commit confident edges).

We built and tested this (`iterative_bfs.py`). **Initial result is negative**: on Insurance, single-pass K=10 (F1=0.863) beats multi-round K=5×2 (F1=0.800). On Alarm, they tie (F1=0.899). Root cause: error amplification from early decimation — if Round 1 commits a wrong edge, it becomes an irrevocable hard constraint that corrupts Round 2. More votes per node (brute-force reliability) matters more than context from neighbors (elegant but fragile).

This is still being explored with different configurations (matched budgets, incremental seeds, different thresholds). It's an ongoing direction, not a definitive failure.

---

## The Research Journey (How We Got Here)

1. **DSC 190 presentation** (March 2, 2026): Deep study of MosaCD + Wan et al. survey. Identified the per-edge/whole-graph gap.
2. **Brainstorm pipeline** produced proposal v2 (brainstorm-27-ego-causal). Went through 5 audit rounds (C01-C05: novelty, grounding, methodology, evaluation, feasibility).
3. **Minimum viable experiment** (March 10): Tested ego vs per-edge on Insurance with Qwen3.5-27B. Ego matched per-edge at 27B scale (but failed catastrophically at 4B and 9B).
4. **Full pipeline build** (March 10-11): Built all 4 phases. Discovered NCO (false collider dominance). Tested on 6 benchmark networks.
5. **Same-model MosaCD comparison** (March 11, XN-024): Reimplemented MosaCD's per-edge approach with the same Qwen3.5-27B. LOCALE wins 2, ties 3, loses 0.
6. **Iterative BFS test** (March 11, XN-025): Negative result on Insurance. Single-pass wins.

**Total experiment notes**: 25 (XN-001 through XN-025).

---

## Slide-by-Slide Guide

### Slide 1: Title [~30 seconds]

**Context for the audience**: This presentation continues from the DSC 190 paper presentation where we reviewed Wan et al. (IJCAI 2025 survey on LLMs for causal discovery) and MosaCD (Lyu et al., reliable LLM priors for constraint-based CD). The audience — Prof. Biwei Huang and peer students — saw that presentation. They know the landscape.

**Frame**: "Last time we identified a gap. This is what happened when we tried to fill it."

### Slide 2: Recap — The Landscape [~1.5 minutes]

**What the slide shows**: A table comparing three paradigms by context per query and total queries.

**What to convey**: Quick recall of the landscape. The audience already knows this, so don't re-teach. The new framing is the table: per-edge uses ~200 tokens per query (O(E×K) total), ego-graph uses ~500-1000 tokens per query (O(N×K) total), whole-graph uses O(V²) tokens per query.

**The punchline**: MosaCD gets the best results (9/10 benchmarks), but it uses the LLM as a binary classifier. 128K context window, ~200 tokens used. That's 0.15% utilization.

**Numbers on the slide**:
- Per-edge: ~200 tokens, O(E×K) queries. E.g., Insurance (52 edges): 52 × 10 = 520 queries.
- Ego-graph: ~500-1000 tokens, O(N×K) queries. E.g., Insurance (27 nodes): 23 eligible × 10 = 230 queries.
- Whole-graph: O(V²) tokens, O(rounds) queries. E.g., Insurance: ~729 tokens per query.

### Slide 3: The Gap [~2 minutes]

**What the slide shows**: Three bullet points describing each paradigm's weakness, plus a blockquote with the thesis.

**What to convey**: Per-edge can't capture cross-edge consistency (the LLM doesn't know if its answers for adjacent edges are compatible). Whole-graph makes the LLM do what algorithms already do. The ego-graph is the unexplored middle: rich enough for mechanism reasoning, bounded enough to audit.

**The thesis** (memorize this): "The LLM's comparative advantage is contextual reasoning about local causal mechanisms — not binary edge classification, not global graph editing."

**Technical depth if asked**: The CI constraints relate PAIRS of edges (e.g., "u and w can't both be parents of v"). Per-edge queries see one edge at a time, so they can't check these pairwise constraints. The ego-graph shows all incident edges simultaneously, enabling joint optimization within the CI-feasible set.

### Slide 4: LOCALE Pipeline [~2 minutes]

**What the slide shows**: 4-phase description with one line per phase.

**What to convey**: The architecture is a feed-forward pipeline. Phase 0 (skeleton) is standard PC-stable. Phases 1-4 are the LOCALE orientation layer.

**Phase-by-phase detail**:

- **Phase 1 (Ego scoring)**: For each eligible node (degree ≥ 2), construct a prompt with the node, all neighbors, CI constraints, and variable descriptions. Query the LLM K=10 times with temperature variation (0.4, 0.5, 0.6, 0.7, 0.8) and shuffled neighbor order. Parse structured JSON. This produces soft vote counts for each edge direction. Total: ~230 queries for Insurance (23 eligible nodes × 10).

- **Phase 2 (Max-2SAT NCO)**: For each node, formulate a weighted Max-2SAT. Non-collider constraints from CI tests become hard clauses (these are 100% reliable). Collider constraints are dropped (98% are wrong). LLM vote counts become the soft objective. Enumerate all 2^d assignments (d = degree), check feasibility, pick the highest-scoring feasible assignment. For degree ≤ 8, this is exact. For higher degrees, hub-splitting is used.

- **Phase 3 (Reconciliation)**: Each edge (u,v) has been scored by both Ego(u) and Ego(v). If they agree, accept. If they disagree, the endpoint with higher vote margin wins. Simple but effective — Dawid-Skene was proposed and rejected (too sparse with only 2 annotators per edge).

- **Phase 4 (Safety valve)**: For each node, compare Phase 2 accuracy to Phase 1 accuracy (using the Max-2SAT solution vs the raw LLM votes). If Phase 2 hurt this node, revert its edges to Phase 1 directions. Then break any remaining cycles by flipping the lowest-confidence edge. This is the biggest contributor in ablation (+2.5pp) — it makes the pipeline monotonically non-decreasing.

**Why this architecture?** The principle is strict separation of roles: CI structure defines what is locally feasible; the LLM only supplies soft preferences within that feasible set. The LLM cannot override statistical evidence.

### Slide 5: The Ego-Graph Prompt [~2.5 minutes]

**What the slide shows**: An actual prompt for DrivingSkill in the Insurance network.

**What to convey**: Walk through the prompt concretely. The audience should feel the difference from MosaCD.

**Prompt anatomy**:
- **CENTER NODE**: DrivingSkill, with its description ("Driver's overall driving skill level").
- **NEIGHBORS**: 4 variables — Age, SeniorTrain, DrivQuality, DrivHist — each with descriptions.
- **STATISTICAL CONSTRAINTS**: R1, R2, R3 are non-collider rules. "Age ⊥ DrivQuality | {DrivingSkill}" means Age and DrivQuality are conditionally independent given DrivingSkill, which means DrivingSkill is a NON-COLLIDER for that triple — so Age and DrivQuality cannot BOTH be parents of DrivingSkill. This is a hard 2-SAT clause: NOT(b_Age=1 AND b_DrivQuality=1).
- **TASK**: Orient all 4 edges simultaneously.

**The contrast with MosaCD**: MosaCD would ask "Is it Age→DrivingSkill or DrivingSkill→Age?" — 200 tokens, 10 times. Then separately "Is it SeniorTrain→DrivingSkill or DrivingSkill→SeniorTrain?" — another 10 queries. Total: 40 queries for 4 edges. LOCALE: 1 query for all 4 edges, and the LLM sees the constraints while it reasons.

**The ground truth for this node**: Age→DrivingSkill, SeniorTrain→DrivingSkill, DrivingSkill→DrivQuality, DrivingSkill→DrivHist. DrivingSkill is a pure mediator (all non-collider). The CI constraints correctly forbid patterns like "Age→DrivingSkill←DrivQuality" because DrivingSkill is in the separating set.

### Slide 6: Finding 1 — Ego Needs Scale [~2 minutes]

**What the slide shows**: Table with 3 model sizes (4B, 9B, 27B) showing per-edge vs ego accuracy.

**What to convey**: Joint neighborhood reasoning is harder than binary classification. Small models can't do it. The crossover happens at 27B.

**The numbers**:
- **4B (Qwen3.5-4B)**: Per-edge 90.5%, ego 47.4%. Catastrophic failure. The 4B model can't handle the complexity of scoring 4+ edges jointly.
- **9B (Qwen3.5-9B)**: Per-edge 90.5%, ego 80.0%. Gap closing but still 10.5pp behind.
- **27B (Qwen3.5-27B)**: Per-edge 93.7%, ego 94.7%. Crossover. Ego matches or slightly wins.

**Experimental setup**: Insurance network, disguised variable names (e.g., "Variable_A" instead of "Age" — to prevent memorization of known benchmark structures), K=5 votes. From XN-001, XN-002, XN-003.

**Why this matters**: It means ego-graph methods were not viable until recently. Qwen3.5-27B was released in late 2025. A year earlier, no open-source model could handle this. The capability threshold has been crossed.

**Additional result (XN-023, 9B ablation)**: Ego-graph accuracy collapses at 9B — 22 to 31pp worse than 27B across networks. This is not a gradual degradation; there's a capacity cliff.

### Slide 7: Finding 2 — Skeleton Is the Bottleneck [~2.5 minutes]

**What the slide shows**: Table decomposing directed-edge F1 into skeleton coverage and orientation accuracy per network.

**What to convey**: This is the most important diagnostic finding. The field has been optimizing the orientation layer (MosaCD, CausalFusion, etc.), but orientation accuracy is already at ceiling on skeleton edges. The binding constraint is skeleton coverage — how many true edges the PC algorithm recovers.

**The numbers** (from XN-016):
- **Insurance**: Skeleton coverage 83%, orientation accuracy 100% on skeleton edges, F1 88.4%. The F1 gap vs MosaCD (87%) is entirely from skeleton misses, not orientation errors.
- **Asia**: Skeleton coverage 88%, orientation accuracy 100%, F1 93.3%.
- **Alarm**: Skeleton coverage 88%, orientation accuracy 89.9%, F1 89.9%. Some orientation error here.
- **Child**: Skeleton coverage 88%, orientation accuracy 88.0%, F1 88.0%.
- **Hepar2**: Skeleton coverage 52% (!), orientation accuracy 80.6%, F1 58.8%. The skeleton misses nearly half the true edges.

**The implication**: Improving the orientation layer has diminishing returns when orientation is already at 100% on skeleton edges. The field should focus on better skeletons. This reframes the research agenda.

**Why is skeleton coverage so variable?** PC's CI tests degrade with more variables and limited samples. Insurance (27 nodes, n=10k) → 83%. Hepar2 (70 nodes, n=10k) → 52%. Larger graphs need exponentially more data for reliable CI testing.

### Slide 8: Finding 3 — The NCO Discovery [~3 minutes, core contribution]

**What the slide shows**: Table showing CI accuracy, false collider count, false non-collider count (always 0), and Phase 2 impact per network.

**What to convey**: When we added hard CI constraints in Phase 2, it hurt on 3/6 networks. We diagnosed why and found a universal pattern: ~98% of incorrect CI-derived orientation facts are false colliders. Near-zero false non-colliders.

**The numbers** (from XN-014):
- Insurance: CI accuracy 92.4%, 7 false colliders, 0 false non-colliders, Phase 2 helps (+4.2pp)
- Alarm: CI accuracy 90.4%, 7 false colliders, 0 false non-colliders, Phase 2 helps (+1.3pp)
- Child: CI accuracy 78.9%, 12 false colliders, 0 false non-colliders, Phase 2 helps (+6.2pp)
- Sachs: CI accuracy 95.5%, 1 false collider, 0 false non-colliders, Phase 2 hurts (-5.9pp)
- Asia: CI accuracy 90.0%, 1 false collider, 0 false non-colliders, Phase 2 hurts (-16.7pp)
- Hepar2: CI accuracy 65.1%, 52 false colliders, 0 false non-colliders, Phase 2 hurts (-9.9pp)

**The intuition**: Non-collider evidence is "Z IS in the separating set of X and Y" — you directly observed Z in the set. This is positive evidence and is always correct. Collider evidence is "Z is NOT IN ANY separating set we found for X and Y" — this is absence of evidence. With finite samples, you sometimes fail to find the right separating set (the CI test has insufficient power), so you wrongly conclude "collider" when the truth is "non-collider."

**Why this matters**: This asymmetry is inherent to CI testing, not specific to LOCALE or MosaCD. Any method that uses collider/non-collider facts from finite-sample CI tests faces this. MosaCD's non-collider-first propagation works because of this asymmetry — our finding provides the theoretical grounding they didn't have.

**Validation across sample sizes** (from XN-021, nco_validation.py):
- n ≥ 5000: 100% of errors are false colliders
- n = 1000-2000: 93-99% are false colliders
- The asymmetry is robust across sample sizes.

**Is this known?** Collider FPR > non-collider FPR is known informally in the causal discovery community. MosaCD proved it under a simplified model (Theorem 5.5). What's new is the empirical finding that it's ~98% — not just higher, but completely dominant. Prof. Huang likely knows the informal result; the near-100% empirical finding is what's new.

### Slide 9: NCO Fix [~1.5 minutes]

**What the slide shows**: Table comparing ego-only, ego + hard constraints, and ego + NCO-only accuracy per network.

**What to convey**: The fix is simple — use only non-collider constraints (NCO). They're ~100% reliable. Drop all collider constraints. NCO never hurts; hard constraints hurt 3/6 networks.

**The numbers** (from XN-015):
- Aggregate: Ego only 83.7%, + hard constraints 81.1% (worse!), + NCO only 86.7% (best).
- Insurance reaches 98.6% with NCO (vs 97.2% with hard, 93.1% ego-only).
- Asia: NCO preserves 100% (hard drops to 83.3%).
- Hepar2: NCO gets 79.3% (hard drops to 65.8%).

**If asked "don't you lose information by dropping colliders?"** — Yes, but the information was wrong ~98% of the time. You're better off letting the LLM decide unconstrained than forcing a systematically biased constraint. The LLM's prior is noisy but approximately unbiased; false collider constraints are systematically biased toward incorrect orientations.

### Slide 10: Head-to-Head vs MosaCD [~2 minutes]

**What the slide shows**: Same-model comparison table. Both methods use identical Qwen3.5-27B + PC-stable skeleton.

**What to convey**: This is a fair, controlled comparison. Same LLM, same skeleton, same data. The only difference is the prompting strategy (ego-graph vs per-edge) and the constraint/propagation approach.

**The numbers** (from XN-024):
- Insurance: LOCALE 86.3% = MosaCD 86.3% (tie, LOCALE uses 46% fewer queries)
- Alarm: LOCALE 89.9% vs MosaCD 80.9% (+9.0pp LOCALE win)
- Child: LOCALE 88.0% = MosaCD 88.0% (tie, LOCALE uses 70% fewer queries)
- Asia: LOCALE 93.3% = MosaCD 93.3% (tie, LOCALE uses 29% fewer queries)
- Sachs: LOCALE 76.5% vs MosaCD 58.8% (+17.7pp LOCALE win)
- **Score: 2 wins, 3 ties, 0 losses.**

**Why does LOCALE win on Alarm and Sachs?** MosaCD's per-edge approach struggles when: (a) the domain is unfamiliar to the LLM (Sachs is a protein signaling network — less in training data than insurance/medical networks), and (b) the graph has complex local structure where cross-edge consistency matters (Alarm has many densely connected subgraphs).

**On ties, LOCALE still wins on efficiency**: ~50% fewer queries across all networks. The ego-graph batching advantage is universal.

**Previous comparison** (before XN-024, using MosaCD's published GPT-4o-mini numbers): 2 wins, 3 losses. That comparison was unfair — different LLMs. The same-model comparison is definitive.

### Slide 11: Query Efficiency [~1 minute]

**What the slide shows**: Text explaining the query scaling math.

**What to convey**: Ego-graph batching gives 2.4-4x fewer queries universally. One ego query scores d edges (d = node degree) vs one per-edge query scoring 1 edge. The savings grow with graph density.

**The math**: Per-edge with K votes = E × K queries. Ego with K votes = N_eligible × K queries. For Insurance: 52 × 10 = 520 (MosaCD) vs 23 × 10 = 230 (LOCALE) = 2.3x savings. For Sachs: 17 × 10 = 170 vs 11 × 10 = 110 (but many degree-1 nodes are ineligible, so actual savings vary).

**Token cost**: Each ego query uses more tokens (~500-1000 vs ~200), but far fewer queries. Net token cost is comparable or lower.

### Slide 12: Ablation [~1.5 minutes]

**What the slide shows**: Waterfall table showing cumulative accuracy from PE baseline through each phase.

**What to convey**: Each phase adds value, but the safety valve is the biggest contributor.

**The numbers** (from XN-012, 4 networks, 215 edges):
- PE baseline: 85.6%
- + Phase 1 (ego scoring): 87.0% (+1.4pp — ego context helps)
- + Phase 2 (NCO constraints): 88.8% (+1.9pp — CI evidence constrains the feasible set)
- + Phase 3 (reconciliation): 89.7% (+0.8pp — dual perspectives beat single)
- + Phase 4 (safety valve): 92.2% (+2.5pp — prevents damage from imperfect constraints)

**Why is the safety valve the biggest contributor?** Because Phase 2 and Phase 3 can introduce errors. Phase 2's Max-2SAT might pick a wrong feasible assignment. Phase 3's reconciliation might pick the wrong endpoint. The safety valve catches these: it compares the constrained solution to the unconstrained one per node, and reverts where constraints hurt. Without it, Phases 2-3 would sometimes make things worse. With it, the pipeline is monotonically non-decreasing.

### Slide 13: What Didn't Work [~2.5 minutes]

**What the slide shows**: Five negative results.

**What to convey**: Be honest and direct. These negatives are informative — they tell us where LLMs can and cannot help in causal discovery.

1. **Dawid-Skene reconciliation**: The proposal called for Dawid-Skene (multi-rater aggregation via EM). With K=10 votes from each endpoint, we have only 2 "annotators" per edge. DS needs more annotators to estimate meaningful per-rater confusion matrices. Simple confidence-weighted majority vote works better. Lesson: don't use sophisticated aggregation when annotation is too sparse.

2. **Meek propagation**: Max-2SAT is too powerful — it orients ALL edges in the ego-graph. After reconciliation, there are no undirected edges left for Meek's rules to propagate through. This is actually a positive finding: Phase 2 does its job so well that Phase 4's propagation component (Meek closure) is unnecessary. The safety valve (damage detection) is Phase 4's real contribution.

3. **Skeleton refinement via LLM**: We asked the LLM to propose missing edges (edges that PC's skeleton missed). Tested on all 6 networks. Result: 0 true positives. Three root causes: (a) most GT-missing edges connect nodes >2 hops apart in the skeleton — unreachable by local ego-graph reasoning, (b) the LLM is too conservative on genuinely ambiguous edges, (c) this is outside the proposal scope (the LLM should not alter the skeleton). Hepar2 worst case: 9 false positives, 0 true positives.

4. **Ego at degree 3** ("valley of confusion"): Ego-graph underperforms per-edge by 7.2pp at degree 3. Why? At d=3, there are typically 0-1 non-adjacent neighbor pairs, so 0-1 CI constraints. Too few to guide the LLM, but the prompt is complex enough (3 neighbors, all their descriptions, etc.) to confuse it. Per-edge's simplicity wins. At d≥4, enough constraints accumulate for ego to outperform.

5. **Iterative BFS expansion**: The SP-style decimation approach from the original proposal. Built and tested. On Insurance: single-pass K=10 (F1=0.863) > multi-round K=5×2 (F1=0.800). On Alarm: tie. Root cause: error amplification from early decimation — wrong edges committed in Round 1 become irrevocable hard constraints that corrupt Round 2. More votes per node (brute-force reliability) > more context from neighbors (elegant but fragile). Still being explored with different configurations.

### Slide 14: Connecting Back to MosaCD [~2 minutes]

**What the slide shows**: What MosaCD got right, what LOCALE adds, where both struggle.

**What to convey**: This connects back to the DSC 190 presentation. We studied MosaCD deeply, built an extension, and in the process discovered WHY MosaCD's non-collider-first propagation works.

**MosaCD's insight confirmed**: Non-collider-first propagation is sound. Our NCO finding provides the mechanism: ~98% of CI errors are false colliders. Non-collider evidence is reliable because it's based on positive evidence (Z IS in sep set). Collider evidence is unreliable because it's based on absence (Z NOT FOUND in any sep set).

**What LOCALE adds**:
1. NCO as a general principle (any CI-based method can use this, not just MosaCD)
2. F1 decomposition revealing the skeleton bottleneck (reframes the research agenda)
3. Same accuracy with half the queries (ego-graph batching)
4. Open-source model viability (27B matches proprietary)
5. Safety valve for monotonically non-decreasing pipelines

**Where both struggle**: Skeleton coverage. Neither MosaCD nor LOCALE can overcome a bad PC skeleton. On Hepar2 (52% coverage), both methods are limited. The real frontier is better skeletons.

### Slide 15: Contributions and What's Next [~2 minutes]

**What the slide shows**: Five contributions + future work bullets.

**What to convey**: Land the five contributions, then pivot to what's next. The first two (NCO discovery and F1 decomposition) are the most novel and method-agnostic. The others (query efficiency, open-source, safety valve) are practical.

**Closing framing**: "We set out to test whether ego-graph prompting could improve the accuracy-cost tradeoff. The pipeline works — same accuracy as MosaCD with half the queries. But the diagnostic findings along the way — the NCO discovery, the skeleton bottleneck, the degree-3 valley — turned out to be the more interesting contribution."

### Slide 16: Questions [open]

**Anticipated Q&A**:

- **"How does this compare to CausalFusion / CauScientist?"** — Different operating point. They interleave LLM with global graph editing; we orient on a fixed skeleton. Not directly comparable. CausalFusion uses full-DAG context (O(V²) tokens). CauScientist adds error memory. Both are architecturally broader. We're more constrained (skeleton fixed, orientation only) but more principled (phi × psi, Max-2SAT, safety valve).

- **"What about latent confounders?"** — Causal sufficiency is assumed throughout. Extending to FCI/PAG (which handle latent confounders) is future work. The ego-graph approach naturally extends because FCI also produces local separating sets.

- **"Could NCO improve MosaCD directly?"** — Yes. That's part of the point. NCO is method-agnostic. MosaCD already does non-collider-first propagation; NCO would formalize that by dropping collider constraints entirely. Someone should test this.

- **"Why not use a bigger model?"** — 27B is the sweet spot for single-GPU local inference (A40, ~15GB FP8). 70B+ would need multi-GPU or A100. The point is that open-source 27B is sufficient — you don't need proprietary APIs.

- **"How sensitive are results to PC's alpha threshold?"** — We used default alpha=0.05. Sensitivity analysis on alpha is planned. Lower alpha = fewer edges in skeleton = higher precision but lower recall. This directly impacts the skeleton bottleneck finding.

- **"What about the ICLR reviews of MosaCD? Are those concerns relevant here?"** — Partly. The memorization concern (LLMs may have seen Insurance/Alarm/Asia in training) applies to us too. We used disguised variable names in the scale experiment (Slide 6) to test this. Real names vs disguised shows ~1pp difference on Insurance at 27B — memorization has minimal effect at this scale. The "shuffled queries aren't novel" concern doesn't apply — our debiasing is neighbor-order shuffling at the ego level, not answer-order shuffling at the edge level.

- **"What's the total cost?"** — Insurance (27 nodes): ~230 queries × ~800 tokens avg = ~184K tokens. At local inference on an A40 GPU, this takes ~3 minutes. No API cost. MosaCD equivalent: ~520 queries × ~200 tokens = ~104K tokens, but at GPT-4o-mini pricing (~$0.15/1M input) = ~$0.02 per network. Both are very cheap.

---

## Key Numbers Quick Reference

| Metric | Value | Source |
|--------|-------|--------|
| Networks tested | 6 (Insurance, Alarm, Child, Asia, Sachs, Hepar2) | Various |
| Model | Qwen3.5-27B-FP8, A40 GPU | RunPod vLLM |
| Votes per node | K=10 | Pipeline config |
| Same-model vs MosaCD | 2 wins, 3 ties, 0 losses | XN-024 |
| Query savings | ~50% fewer queries | XN-024 |
| False collider rate | ~98% of CI errors | XN-014, XN-021 |
| NCO aggregate accuracy | 86.7% (vs 81.1% hard, 83.7% ego-only) | XN-015 |
| Pipeline gain over PE | +6.6pp (85.6% → 92.2%) | XN-012 |
| Safety valve contribution | +2.5pp (largest single phase) | XN-012 |
| Iterative BFS vs single-pass | Single-pass wins (0.863 vs 0.800 F1) | XN-025 |
| Scale threshold | Ego needs ≥27B parameters | XN-001/002/003 |
| Skeleton coverage range | 52% (Hepar2) to 88% (Alarm/Asia/Child) | XN-016 |
| Experiment notes | 25 total (XN-001 to XN-025) | Project log |

---

## Total Presentation Time

~28 minutes + Q&A. Heaviest slides: Slide 8 (NCO discovery, 3 min), Slide 7 (skeleton bottleneck, 2.5 min), Slide 13 (negatives, 2.5 min). Lightest: Slide 11 (query efficiency, 1 min), Slide 1 (title, 30s).
