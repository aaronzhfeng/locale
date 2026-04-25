# 008 — Message-Passing Causal Discovery: Local Ego-Graph Reasoning with LLM Contextual Oracles

**Date:** 2026-03-02 (originated) / 2026-03-05 (updated after vetting session)
**Origin:** Discussion during DSC 190 presentation prep (MosaCD + Wan et al. survey deep study)
**Status:** Ready to graduate → brainstorm-27-ego-causal

---

## Core Thesis

All existing LLM-causal discovery methods — including the recent interleaved ones (CausalFusion, CauScientist) — reason at the **global graph level**: the LLM sees the whole DAG and proposes modifications. This doesn't scale (context grows O(V^2)) and wastes the LLM on a task better suited to algorithmic propagation.

**Proposal:** Use the LLM as a **local contextual oracle** that reasons about ego-graph neighborhoods, with iterative expansion following a **Survey Propagation-style decimation** pattern. The LLM handles local causal reasoning (what it's good at); the algorithm handles global consistency (Meek's rules, reconciliation, calibration). They interleave round by round through a principled message-passing framework.

**One-sentence contribution:** A local-to-global message-passing framework for LLM-assisted causal discovery, where ego-graph queries play the role of local potentials and Survey Propagation-style decimation propagates confident orientations outward.

---

## Problem

### Per-edge methods (MosaCD, chatPC)
MosaCD (Lyu et al. 2025) queries the LLM 10 times per edge (shuffled orderings x 5 repetitions). For a 50-variable graph with ~100 undirected edges: ~1,000 LLM calls. Each call sees ~200 tokens (two variable names, one separating set, a binary choice). The 128K+ context window is almost entirely wasted. O(E x K) queries producing O(E) bits of information.

### Global interleaved methods (CausalFusion, CauScientist)
CausalFusion (Amazon, 2025) and CauScientist (OpenCausaLab, Jan 2026) interleave LLM and algorithm — but at the **global** level. The LLM sees the entire DAG each round and proposes structural modifications. This has two problems:
1. **Context scaling:** Full graph in context = O(V^2) tokens. Degrades as graphs grow.
2. **Wrong abstraction level:** The LLM is asked to do what Meek's rules already do perfectly (global consistency). Its comparative advantage is contextual reasoning about local causal mechanisms.

### The gap
No existing method uses the LLM for **local neighborhood reasoning** with algorithmic global propagation. The LLM's context window and reasoning abilities are best matched to "given these 5 variables and their relationships, which causes which?" — not "here's a 50-variable graph, what should I change?"

---

## Proposed Approach (Angle 1: Message-Passing Framing)

### Phase 1: Standard skeleton search (unchanged)

PC/CPC/PC-stable produces the undirected skeleton + separating sets + CI p-values. Same as MosaCD Step 1.

### Phase 2: Iterative ego-graph expansion (Survey Propagation analog)

**The SP mapping:**

| Survey Propagation for k-SAT | Ego-graph causal discovery |
|---|---|
| Variables = Boolean assignments | Variables = edge orientations (X->Y or Y->X) |
| Clauses = local constraints | Ego-graphs = local causal neighborhoods |
| Warning messages = "must be T/F" | Ego-graph output = "must be ->/</uncertain" |
| Surveys = distributions over warnings | Confidence-weighted multi-edge assessments |
| **Decimation** = fix most confident, simplify, repeat | **BFS expansion** = accept most confident, propagate, expand |

**Initialization:** Rank all nodes by centrality/confidence score (average CI p-value strength of their edges, or degree in the skeleton). Start from the most informative nodes.

**Round 1 — Seed nodes:**

For each seed node X, construct a 1-hop ego-graph query:

```
Variable X: [name, description]
Neighbors in causal skeleton (ranked by CI confidence):
  1. A [name, desc] -- CI stats: Sep(X,A)={...}, p=0.92
  2. B [name, desc] -- CI stats: Sep(X,B)={...}, p=0.85
  3. C [name, desc] -- CI stats: Sep(X,C)={...}, p=0.71

Cross-neighbor evidence:
  - A-B: separated by {X}, p=0.88
  - A-C: not separated (adjacent in skeleton)

Task: For each neighbor, determine if it causes X (parent),
X causes it (child), or uncertain. Reason about the full local
structure -- are the directions consistent with each other and
the CI evidence?
```

Run K stochastic passes (temperature > 0). Self-consistency gate: only accept orientations where f(e) = fraction of passes agreeing on majority orientation > tau_1.

**Round 2+ — Frontier expansion (decimation):**

Take nodes oriented in Round 1. Query their ego-graphs with established context:

```
Variable B: [name, description]
ESTABLISHED: X -> B (confidence: 0.91, source: round 1 reconciliation)
ERROR MEMORY: [previously rejected orientations, if any]

Remaining neighbors of B:
  1. D [name, desc] -- CI stats: ...
  2. E [name, desc] -- CI stats: ...

Task: Given established context, orient B's remaining edges.
```

Each round's output feeds the next round's input. The frontier expands like BFS. Error memory (borrowed from CauScientist) prevents redundant proposals.

**Termination:** Stop when all reachable nodes have been queried, or when remaining edges are below a confidence threshold.

### Phase 3: Reconciliation (Dawid-Skene aggregation)

Every edge X-Y was judged twice (from X's ego-graph and Y's ego-graph). This is a multi-rater aggregation problem.

**Dawid-Skene model:**
- Raters = two ego-graph perspectives
- Items = edges to orient
- True label = correct orientation (latent)
- Confusion matrix per rater = per-perspective accuracy alpha

Dawid-Skene via EM (unsupervised — no ground truth needed) gives:
1. Aggregated labels — optimal combination of two perspectives
2. Estimated rater accuracies alpha_u, alpha_v
3. Item difficulty — some edges are harder

**Independence correction (CBCC):**

The two ego-graphs share the same LLM and variable descriptions, so they're not truly independent. Correlated Bayesian Classifier Combination (Kim & Ghahramani 2012) handles this:

```
P(both agree | correct) = alpha_u * alpha_v + rho * sigma_u * sigma_v
P(both agree | wrong)   = (1-alpha_u)(1-alpha_v) + rho * sigma_u * sigma_v

where sigma_u = sqrt(alpha_u(1-alpha_u)), rho = residual correlation
```

rho estimated on calibration benchmarks (known-truth graphs), then applied to new graphs.

**Reconciliation precision (with correlation):**

```
pi(e) = P(correct | both agree)
      = P(agree|correct) * P(correct) / P(agree)
```

Accept reconciled edges where pi(e) > tau_2. Conflicts automatically rejected (pi < 0.5).

### Phase 4: Propagation (Meek's rules + confidence inheritance)

Meek's rules (1995) — proven sound and complete for CPDAG orientation.

Confidence inheritance with damping:
- Rule R1 (acyclicity): conf(b->c) = min(conf(a->b), tau_meek)
- Propagation depth tracked; confidence degrades with distance from seed
- Stop propagation when inherited confidence < tau_4

This is analogous to message damping in loopy BP — prevents oscillation and bounds error accumulation.

### Phase 5: Per-edge fallback (hard tail only)

Edges still unresolved after Phase 4 get MosaCD-style per-edge queries (shuffled, 10 calls per edge). But this is now only the hard tail — estimated 10-20% of edges.

### Phase 6: Final calibration (Venn-Abers)

All oriented edges get calibrated confidence via Venn-Abers prediction (Vovk et al. 2004, 2025):

Features per edge: reconciliation precision pi(e), CI p-value, propagation depth, self-consistency score f(e), Dawid-Skene item difficulty.

**Finite-sample guarantee:**
```
P(true orientation in Venn-Abers prediction set) >= 1 - epsilon
```
for any user-specified epsilon, distribution-free, in finite samples.

**Selective SHD:** Output only edges where calibrated confidence > tau_final. Report:
- Selective SHD (on output edges only)
- Coverage (fraction of true edges output)
- Coverage-accuracy tradeoff curve

---

## Mathematical Gating Summary

```
Skeleton (CI tests, p-values, FDR)
    |
    v
Ego-graph queries (noisy local oracle, self-consistency gate: f(e) > tau_1)
    |
    v
Reconciliation (Dawid-Skene + CBCC correlation correction, gate: pi(e) > tau_2)
    |
    v
Meek's propagation (confidence inheritance, damping gate: conf > tau_3)
    |
    v
Per-edge fallback (only for edges below all gates)
    |
    v
Venn-Abers calibration -> Selective SHD @ coverage
```

Every transition is gated by a mathematically grounded threshold.

---

## Convergence

**Termination:** Trivially guaranteed. Each round orients >= 1 new edge or terminates. Orientations are monotone (never reversed). Graph has |E| edges. Terminates in <= |E| rounds. BFS covers graph in <= D rounds (D = skeleton diameter).

**Correctness (sufficient condition):**

```
alpha_min > 1/2 + delta(Delta, K)
```

where Delta = max degree, K = number of rounds, delta = correction for error accumulation over K rounds. For bounded-degree graphs (Delta <= 10, typical for causal benchmarks), this is mild.

**Computation tree equivalence** (Tatikonda & Jordan 2002): K rounds of ego-graph expansion from seed s = effective reasoning about the depth-K neighborhood of s. If local accuracy alpha > 0.5 and confidence damping ensures distant influences decay, the process converges to the correct CPDAG.

---

## Cost Analysis

| Component | Queries | Information per query |
|---|---|---|
| Phase 2 ego-graph | N nodes x K passes | ~degree(X) edge orientations each |
| Phase 3 reconciliation | 0 LLM calls | Dawid-Skene EM |
| Phase 4 propagation | 0 LLM calls | Meek's rules |
| Phase 5 fallback | ~0.1E x 10 | 1 edge orientation each |

For a 50-variable, 100-edge graph (avg degree 4), K=1:
- Phase 2: 50 queries -> ~200 edge judgments
- Phase 5 fallback: ~10 hard edges x 10 = 100 queries
- **Total: ~150 queries** vs MosaCD ~1,000, CausalFusion ~50 but with full-graph context

With K=3 stochastic passes: ~250 queries total. 3-4x cheaper than MosaCD AND richer information per query AND constant context size.

---

## Competitive Landscape (as of March 2026)

| Method | LLM role | Context per query | Interleaved? | Scaling |
|---|---|---|---|---|
| chatPC | CI oracle | One triple (X,Y,Z) | No | O(triples) |
| ILS-CSL | Iterative proposer | Full variable list, no CI | Yes | O(V) context |
| MosaCD | Edge classifier | One edge + sep set | No | O(E x K) queries |
| CausalFusion | Global DAG editor | Full DAG + falsification | Yes | O(V^2) context |
| CauScientist | Global DAG editor | Full DAG + error memory | Yes | O(V^2) context |
| **This work** | Local ego-graph oracle | 1-hop neighborhood | Yes | O(d) context, O(V x K) queries |

Key differentiator: **local-to-global** interleaving vs. global-to-global. Constant context per query regardless of graph size.

---

## Classical Mathematical Foundations

Every component maps to established theory:

| Component | Classical foundation | Key reference |
|---|---|---|
| Ego-graph expansion + decimation | Survey Propagation | Braunstein, Mezard & Zecchina (2002) |
| Dual-perspective reconciliation | Dawid-Skene multi-rater model | Dawid & Skene (1979) |
| Correlation correction | Correlated Bayesian Classifier Combination | Kim & Ghahramani (2012) |
| Meek's orientation propagation | CPDAG completeness | Meek (1995) |
| Convergence analysis | Computation tree equivalence | Tatikonda & Jordan (2002) |
| Message error bounds | Loopy BP error analysis | Ihler, Fisher & Willsky (2005) |
| Finite-sample calibration | Venn-Abers prediction | Vovk et al. (2004, 2025 ICML) |

---

## Differentiation from Prior Work

The OLD claim ("first to interleave LLM and algorithm") is **false** — CausalFusion and CauScientist both interleave.

The CORRECT claim: **first to use local ego-graph reasoning with Survey Propagation-style decimation** for LLM-causal discovery. All prior interleaved methods reason globally. This is:
1. More principled (local potentials + global consistency, like BP)
2. More scalable (O(d) context vs O(V^2))
3. More efficient (multi-edge per query, natural reconciliation)
4. Mathematically grounded (SP, Dawid-Skene, Venn-Abers, computation tree)

---

## Why This Might Work

1. **LLMs are good at local contextual reasoning.** "Given these 5 variables and their relationships, which causes which?" is a natural reasoning task. "Here's a 50-variable graph, edit it" is not.

2. **SP-style decimation is proven effective.** Survey Propagation solved hard random k-SAT instances that no other method could. The same local-message + decimation pattern should work for causal orientation.

3. **Dawid-Skene reconciliation provides free uncertainty.** Two independent local perspectives on the same edge, aggregated without ground truth. Agreement without coordination is stronger evidence than repeated narrow queries.

4. **Venn-Abers gives what no other causal method offers.** Finite-sample calibrated confidence on every edge orientation. Enables principled selective prediction.

5. **The fallback is principled.** Per-edge queries reserved for edges where local context genuinely wasn't enough.

---

## Key Risks / Open Questions

1. **Does richer local context actually improve accuracy?** The fundamental empirical question. MVE tests this directly.

2. **Error propagation across rounds.** Mistakes in Round 1 propagate as "established" context. Mitigations: only propagate reconciled (agreed) edges; error memory tracks conflicts; confidence damping limits influence radius.

3. **Ordering effects.** Starting node affects downstream orientations. Mitigations: stochastic passes with different starting nodes; start from highest-confidence nodes.

4. **LLM structured output reliability.** Multi-edge ego-graph outputs need robust parsing + graceful handling of partial responses.

5. **Reconciliation independence assumption.** The CBCC correlation correction helps but rho estimation requires calibration data. How sensitive is performance to rho misspecification?

6. **Convergence rate in practice.** Theoretical termination is guaranteed but convergence might be slow on large sparse graphs. Empirical characterization needed.

---

## Minimum Viable Experiment

Before committing to a full project:

1. Take Insurance (27 variables) with known ground truth
2. Run standard PC Phase 1 to get skeleton
3. For 5 central nodes, construct ego-graph prompts manually
4. Compare: per-edge accuracy (MosaCD-style) vs ego-graph accuracy (this approach) on the same edges
5. If ego-graph accuracy > per-edge accuracy by >5 percentage points, proceed

This takes an afternoon with API calls. No infrastructure needed.

---

## A-Prompt Categories (Angle 1: Message-Passing Framing)

1. **LLM x causal discovery methods** — MosaCD, CausalFusion, CauScientist, chatPC, ILS-CSL, ALCM, Causal-LLM, MATMCD, ASoT
2. **Belief propagation / message passing in graphical models** — loopy BP, survey propagation, warning propagation, TRW, computation tree, convergence conditions
3. **Constraint-based causal discovery at scale** — PC variants, FCI, large-graph methods, Markov blanket methods (HITON, MMPC)
4. **Multi-rater aggregation and reconciliation** — Dawid-Skene, CBCC, crowdsourcing, inter-annotator agreement, multi-agent debate
5. **Calibration with finite-sample guarantees** — Venn-Abers, conformal prediction for structured outputs, selective prediction, coverage-accuracy tradeoffs

---

## Venue Targets

- **CLeaR 2027** (Causal Learning and Reasoning) — perfect fit
- **UAI 2027** (Uncertainty in AI) — reconciliation + calibration angle
- **NeurIPS 2026** — if results are strong enough for main track

---

## Connection to Existing Work

- **Independent from brainstorm-18** (calibrated selective TS causal) — different scope, different contribution, different benchmarks
- **Independent from brainstorm-19** (retrieval-as-treatment) — different domain entirely
- **Shares calibration techniques** with brainstorm-18 (Venn-Abers), TrustPPI (domain-specific trust signals), AR-Bench (selective prediction)
- **Motivated by MosaCD ICLR reviews** — reviewer JtHM criticized shuffled queries as "a known technique." Ego-graph reasoning + SP decimation + Dawid-Skene reconciliation is not known

---

## Formal SP Mapping: Factor Graph for Causal Edge Orientation

### Factor graph construction

Given skeleton S = (V, E_undirected) from PC Phase 1:

**Variable nodes:** One binary variable x_e in {+1, -1} per undirected edge e = (u,v), where x_e = +1 means u->v and x_e = -1 means v->u.

**Factor nodes:** One factor per node v in V, connecting to all edge-variables incident to v:

```
f_v(x_{e1}, x_{e2}, ..., x_{ed_v}) = LLM_oracle(EG(v))
```

where EG(v) is the ego-graph of v. The factor f_v encodes the LLM's joint assessment of all edges incident to v. Unlike standard BP where factors are fixed potentials, here the factor is **adaptive** — it conditions on the current state of established orientations.

### Local potential decomposition

The LLM's output for ego-graph query at node v decomposes as:

```
f_v(x_{e1}, ..., x_{ed_v}) = prod_i psi_v(x_{ei}) * phi_v(x_{e1}, ..., x_{ed_v})
```

where:
- **psi_v(x_{ei})** = marginal orientation confidence for edge e_i from v's perspective. This is the "warning" in SP terms.
- **phi_v(...)** = consistency potential capturing cross-edge dependencies within v's ego-graph (e.g., "if A->v and v->B, consistent with A-B separated by {v}")

Key insight: per-edge methods (MosaCD) only compute psi. The ego-graph approach additionally computes phi — the **local consistency term** that no per-edge method can capture.

### Message update rule

In round k, the message from factor v to edge-variable e = (v,u):

```
m_{v->e}^(k)(x_e) = sum_{x_{e'}: e' != e, e' incident to v}
    f_v(x_e, x_{e1}^*, ..., x_{ed-1}^*)
    * prod_{e' != e} m_{e'->v}^(k-1)(x_{e'})
```

where x_{ei}^* are the current decimated (established) orientations, treated as delta functions. In practice, the LLM implicitly marginalizes over local configurations — the LLM IS the message computation.

### Decimation criterion

After each round of ego-graph queries:
1. Compute the "bias" of each undirected edge: b(e) = |m_{u->e}(+1) - m_{u->e}(-1)| averaged over both perspectives
2. Reconciliation: agree/disagree/partial (Dawid-Skene)
3. **Decimate:** Fix edges where reconciliation precision pi(e) > tau_2
4. Remove decimated edges from the undirected set
5. Feed established orientations into next round's ego-graph queries

This is exactly SP's decimation loop: compute marginals -> fix most biased -> simplify -> repeat.

### Key theoretical parallel

**MosaCD is to this method as Warning Propagation is to Survey Propagation.**
- WP sends 1-bit messages; SP sends distributions
- MosaCD queries 1 edge at a time; we query entire neighborhoods
- WP works on easy instances; SP works on hard instances near the phase transition

---

## Concrete Walkthrough: Insurance Network (27 nodes, 52 edges)

### Ground truth (relevant subgraph)

```
Age -----> DrivingSkill -----> DrivQuality -----> Accident
                ^                    ^
          SeniorTrain          RiskAversion
                ^                    |
          Age, RiskAversion          v
                              DrivHist
                                 ^
                           RiskAversion, DrivingSkill
```

DrivingSkill has 4 neighbors: Age, SeniorTrain, DrivQuality, DrivHist.

### After PC Phase 1 (skeleton + CI stats)

Skeleton edges incident to DrivingSkill:
- DrivingSkill -- Age
- DrivingSkill -- SeniorTrain
- DrivingSkill -- DrivQuality
- DrivingSkill -- DrivHist

Cross-neighbor CI results (non-edges among neighbors):
- Age _||_ DrivQuality | {**DrivingSkill**}, p = 0.87
- Age _||_ DrivHist | {**DrivingSkill**}, p = 0.91
- SeniorTrain _||_ DrivQuality | {**DrivingSkill**}, p = 0.83
- SeniorTrain _||_ DrivHist | {**DrivingSkill**}, p = 0.79
- DrivQuality _||_ DrivHist | {**DrivingSkill**, RiskAversion}, p = 0.74

DrivingSkill appears in EVERY separating set -> non-collider in all unshielded triples -> mediator or source. CI data tells topology (chain) but NOT direction.

### Round 1: Ego-graph query at DrivingSkill

**Prompt:**
```
NODE: DrivingSkill
  Description: Driver's overall driving skill level

NEIGHBORS (4 undirected edges):
  1. Age -- "Driver's age group: Adolescent, Adult, Senior"
     CI: Age _||_ DrivQuality | {DrivingSkill}, p=0.87
         Age _||_ DrivHist | {DrivingSkill}, p=0.91
  2. SeniorTrain -- "Senior training program completed"
     CI: SeniorTrain _||_ DrivQuality | {DrivingSkill}, p=0.83
         SeniorTrain _||_ DrivHist | {DrivingSkill}, p=0.79
  3. DrivQuality -- "Quality of driving: Poor to Excellent"
     CI: DrivQuality _||_ DrivHist | {DrivingSkill, RiskAversion}, p=0.74
  4. DrivHist -- "Driving violation history: None, One, Many"

CROSS-NEIGHBOR: Age--SeniorTrain ADJACENT. All other pairs NOT adjacent,
separated by sets containing DrivingSkill.

TASK: Orient each edge. Reason about full local consistency.
```

**Expected LLM output:**
```
Age -> DrivingSkill        (Parent)    confidence: HIGH
SeniorTrain -> DrivingSkill (Parent)   confidence: HIGH
DrivingSkill -> DrivQuality (Child)    confidence: HIGH
DrivingSkill -> DrivHist   (Child)     confidence: MEDIUM-HIGH
```

Reasoning: Age and training PRECEDE skill; quality and history are OUTCOMES of skill. DrivingSkill in all separating sets confirms mediator role.

**Self-consistency gate (K=3 passes):**

| Edge | Pass 1 | Pass 2 | Pass 3 | f(e) | Gate (tau_1=0.67) |
|------|--------|--------|--------|------|-------------------|
| Age -> DS | -> | -> | -> | 1.0 | PASS |
| ST -> DS | -> | -> | -> | 1.0 | PASS |
| DS -> DQ | -> | -> | -> | 1.0 | PASS |
| DS -> DH | -> | -> | <- | 0.67 | PASS (borderline) |

One query -> 4 edge orientations. MosaCD: 4 x 10 = 40 queries.

### Round 2: Expansion to DrivQuality (established: DrivingSkill -> DrivQuality)

**Prompt:**
```
NODE: DrivQuality
ESTABLISHED: DrivingSkill -> DrivQuality (conf: 1.0, Round 1)
ERROR MEMORY: (empty)

REMAINING NEIGHBORS:
  1. RiskAversion -- "Risk tolerance: Psychopath to Cautious"
  2. Accident -- "Accident severity: None to Severe"

TASK: Given established context, orient remaining edges.
```

**Expected output:**
```
RiskAversion -> DrivQuality  (Parent)  confidence: HIGH
DrivQuality -> Accident      (Child)   confidence: HIGH
```

The LLM recognizes DrivingSkill -> DrivQuality <- RiskAversion as a collider, consistent with CI evidence.

### Reconciliation: DrivingSkill -- DrivQuality

Both perspectives agree: DrivingSkill -> DrivQuality.

```
alpha_u = alpha_v ~ 0.85, rho ~ 0.2

P(agree|correct) = 0.85*0.85 + 0.2*sqrt(0.85*0.15*0.85*0.15) = 0.748
P(agree|wrong) = 0.15*0.15 + 0.2*sqrt(0.85*0.15*0.85*0.15) = 0.048

pi(e) = 0.748 / (0.748 + 0.048) = 0.940 > tau_2 = 0.80 -> ACCEPT
```

### Decimation after Rounds 1-2

```
DECIMATED (6 edges from 2 ego-graph queries, 15 API calls with K=3):
  Age -> DrivingSkill          pi = 0.94
  SeniorTrain -> DrivingSkill  pi = 0.94
  DrivingSkill -> DrivQuality  pi = 0.94
  DrivingSkill -> DrivHist     pi = 0.88
  RiskAversion -> DrivQuality  pi = 0.91
  DrivQuality -> Accident      pi = 0.91

REMAINING: 46 undirected edges -> continue BFS...
```

MosaCD for same 6 edges: 60 API calls. Ego-graph: 15 API calls (4x cheaper).

---

## Lit Check Results (2026-03-05)

Searched for prior connections of SP/Dawid-Skene/Venn-Abers to causal discovery:

| Connection | Found? | Closest match |
|---|---|---|
| Survey Propagation -> causal discovery | **None** | Huang & Zhou (2025) do sequential orientation via additive noise models, not SP |
| Dawid-Skene -> causal edge aggregation | **None** | DS used for crowdsourcing, never causal graphs |
| Venn-Abers -> causal graph calibration | **None** | VA used for classification/regression, never structure learning |
| Decimation/cavity -> causal structure | **None** | Statistical physics tools haven't crossed into causal discovery |

The entire mathematical assembly is novel. Each piece is decades-old (defensible), but the combination is ours.

---

## The Consistency Potential phi_v: Closed-Form Derivation

### Orientation variables

Node v with neighbors u_1, ..., u_d. Define:
- x_i = +1 means u_i -> v (parent)
- x_i = -1 means v -> u_i (child)

### Pairwise constraints from CI evidence

For each non-adjacent pair (u_i, u_j):

**v in Sep(u_i, u_j) -> non-collider: forbid both parents**
```
phi_{ij}^{nc}(x_i, x_j) = I(x_i = -1 OR x_j = -1)
Boolean: (NOT x_i OR NOT x_j) -- a 2-SAT clause
```

**v not in Sep(u_i, u_j) -> collider: require both parents**
```
phi_{ij}^{c}(x_i, x_j) = I(x_i = +1 AND x_j = +1)
Boolean: (x_i AND x_j) -- two unit clauses
```

**u_i, u_j adjacent (shielded triple): no constraint**
```
phi_{ij}^{s}(x_i, x_j) = 1
```

### Full consistency potential

```
phi_v(x_1, ..., x_d) = prod_{(i,j): non-adjacent} phi_{ij}(x_i, x_j)
```

### Core theorem: ego-graph orientation is weighted 2-SAT

The complete local factorization:
```
f_v(x_1, ..., x_d) = [prod_i psi_v(x_i)] x [prod_{(i,j)} phi_{ij}(x_i, x_j)]
                    = LLM domain weights    x  CI-derived 2-SAT clauses
```

The feasible set F_v = {orientations satisfying all phi constraints} is the solution set of a 2-SAT instance (poly-time solvable). Typically |F_v| > 1 -- this IS the local Markov equivalence class. The LLM's psi selects from F_v using domain knowledge.

### Contribution decomposition

| Component | Provides | Without it |
|---|---|---|
| phi alone (CI) | Feasible set F_v | No domain knowledge -- many equivalent DAGs |
| psi alone (MosaCD) | Marginal preferences | No consistency -- may violate CI constraints |
| phi x psi (ego-graph) | Joint optimum in F_v | -- |

Per-edge methods compute psi WITHOUT phi. They can propose orientations that collectively violate CI constraints. Ego-graph gives the LLM both, enabling joint optimization.

### Worked example: DrivingSkill

Neighbors: Age (x1), SeniorTrain (x2), DrivQuality (x3), DrivHist (x4).
All non-adjacent pairs have v in Sep -> all non-collider clauses:

```
(NOT x1 OR NOT x3) AND (NOT x1 OR NOT x4) AND
(NOT x2 OR NOT x3) AND (NOT x2 OR NOT x4) AND (NOT x3 OR NOT x4)
```

Feasible set: at most 1 of {x3, x4} can be +1, and if either is +1 then neither {x1, x2} can be +1 with it. Age-SeniorTrain are adjacent (shielded) -> no clause between them -> both can be +1 simultaneously.

Ground truth (+1,+1,-1,-1) = Age->v, ST->v, v->DQ, v->DH is in F_v. The LLM's psi correctly selects it.

---

## MVE Protocol: Does phi x psi Beat psi Alone?

### Hypothesis

Ego-graph queries (phi x psi) orient edges more accurately than per-edge queries (psi only) because the LLM can check local consistency against CI constraints.

### Design: Matched A/B comparison

Same edges, same LLM, same variable descriptions, same CI evidence. Only difference: whether the LLM sees the neighborhood.

| Condition | Prompt | Tests |
|---|---|---|
| A (psi only) | Single edge + descriptions + Sep + p-value | Domain knowledge without consistency |
| B (phi x psi) | Full ego-graph: all neighbors, all CI stats, cross-neighbor evidence | Domain knowledge WITH consistency |

### Step 0: Setup (30 min)

```python
from pgmpy.utils import get_example_model
from pgmpy.sampling import BayesianModelSampling
from pgmpy.estimators import PC

model = get_example_model("insurance")
ground_truth = set(model.edges())
data = BayesianModelSampling(model).forward_sample(size=5000)
skeleton = PC(data).build_skeleton()
```

### Step 1: Select 5 test nodes (10 min)

| Node | Degree | Structure type |
|---|---|---|
| DrivingSkill | 4 | Pure mediator (all non-collider) |
| DrivQuality | 3 | Collider (v-structure) |
| Accident | 7 | High-degree, mixed |
| CarValue | 3 | Multiple parents |
| SocioEcon | 6 | High out-degree (source-like) |

Covers ~18-22 unique edges.

### Step 2: Construct prompts (1 hr)

Condition A: one prompt per edge (MosaCD format).
Condition B: one prompt per node (ego-graph format).

### Step 3: Run API calls (2-3 hrs)

```
LLM: GPT-4o or Claude Sonnet 4.6
Temperature: 0.7
K = 5 passes per prompt

Condition A: ~20 edges x 5 passes = 100 calls
Condition B: 5 nodes x 5 passes = 25 calls
Total: ~125 calls, ~$5
```

### Step 4: Metrics

```
delta = mean(acc_B) - mean(acc_A)   # THE KEY NUMBER
phi_violations_A = count of CI-inconsistent per-edge proposals
phi_violations_B = same for ego-graph (should be ~0)
```

### Step 5: Go / No-Go

| delta | Action |
|---|---|
| > 10 pp | Full build. Target CLeaR 2027 |
| 5-10 pp | Proceed cautiously. Focus on structures where phi helps |
| < 5 pp | Re-examine. Maybe value is in cost savings, not accuracy |
| < 0 pp | Kill this angle |

### Resource requirements

```
Time: ~5 hours (one afternoon)
Cost: ~$5 API calls
Dependencies: pgmpy, API key
```

---

## Graduation Package (ready to copy into brainstorm-27)

### topic.yml

```yaml
name: "Message-Passing Causal Discovery with LLM Ego-Graph Oracles"
slug: "ego-causal"

genre: "Causal discovery / LLM-assisted structure learning"

description: >
  A local-to-global message-passing framework for LLM-assisted causal
  discovery. The LLM reasons about ego-graph neighborhoods (local
  potentials); Survey Propagation-style decimation propagates confident
  orientations outward; Dawid-Skene reconciliation aggregates dual
  perspectives; Venn-Abers calibration provides finite-sample edge
  confidence. Targets static causal discovery benchmarks (Insurance,
  Alarm, Sachs, Hepar2, Pathfinder). Excludes time-series causal
  discovery (see brainstorm-18).

categories:
  - "LLM x causal discovery methods"
  - "Belief propagation / message passing / survey propagation"
  - "Constraint-based causal discovery at scale"
  - "Multi-rater aggregation and reconciliation"
  - "Calibration with finite-sample guarantees"

sources:
  - "LLM prompts (A01-A05)"
  - "arXiv search"
  - "Manual additions (MosaCD, CausalFusion, CauScientist)"
```

### topic_brief.md (pre-filled)

```markdown
# Topic Brief

## Research Topic

**Working Title:** Message-Passing Causal Discovery: Local Ego-Graph Reasoning with LLM Contextual Oracles

**One-line pitch:** A local-to-global framework where the LLM orients edges via ego-graph reasoning (weighted 2-SAT: CI constraints + domain knowledge), and Survey Propagation-style decimation propagates confident orientations outward — 3-4x cheaper than MosaCD with richer information per query.

## Problem Statement

Existing LLM-assisted causal discovery methods waste the LLM's capabilities. Per-edge methods (MosaCD, chatPC) use the LLM as a binary classifier — "is it X->Y or Y->X?" — with O(E x K) queries producing O(E) bits. Global interleaved methods (CausalFusion, CauScientist) stuff the entire DAG into the LLM's context — O(V^2) tokens per query, degrading as graphs grow. Neither approach matches the LLM's comparative advantage: contextual reasoning about local causal mechanisms.

The core theoretical insight: each ego-graph orientation problem is a weighted 2-SAT instance where CI-derived constraints (non-collider/collider from separating sets) define the feasible set, and LLM domain knowledge selects from it. Per-edge methods compute the weights without the constraints; pure algorithmic methods enforce constraints without weights. Only ego-graph queries give the LLM both simultaneously.

## Key Questions

1. Does ego-graph context (phi x psi) improve edge orientation accuracy over per-edge queries (psi only)?
2. How does reconciliation precision (dual-perspective Dawid-Skene) compare to MosaCD's shuffled-query debiasing?
3. Does the scaling advantage (O(d) context vs O(V^2)) translate to better accuracy on large graphs (100+ nodes)?
4. Can Venn-Abers calibration provide meaningful finite-sample coverage guarantees for causal edge orientations?

## Proposed Approach (High-Level)

Phase 1: Standard PC skeleton search (unchanged). Phase 2: Iterative ego-graph expansion following SP-style decimation — query each node's 1-hop neighborhood, gate by self-consistency, expand BFS from high-confidence seeds. Phase 3: Dawid-Skene reconciliation with CBCC correlation correction aggregates dual perspectives per edge. Phase 4: Meek's rules propagate from reconciled seeds. Phase 5: Per-edge fallback for the hard tail (~10-20% of edges). Phase 6: Venn-Abers calibration with finite-sample guarantees, enabling selective SHD at user-specified coverage.

## Target Venue

| Venue | Deadline | Track |
|-------|----------|-------|
| CLeaR 2027 | TBD (~Sep 2026) | Main conference |
| UAI 2027 | TBD (~Feb 2027) | Main conference |
| NeurIPS 2026 | May 2026 | Main conference (stretch) |

## Constraints

- **Compute budget:** API calls only (~$50-200 for full experiments). No GPU training.
- **Timeline:** MVE in one afternoon; full system 2-3 months
- **Team size:** Solo (first-authored)

## Relevant Background

- DSC 190 coursework: deep study of MosaCD + Wan et al. survey
- brainstorm-18: calibrated selective TS causal discovery (related but independent)
- Statistical foundations: dual degree in Statistics, conformal prediction, calibration
- GNN background: message passing, PyG (direct parallel to SP framework)

## Keywords for Literature Search

- LLM causal discovery, MosaCD, CausalFusion, CauScientist
- Survey propagation, belief propagation, message passing, decimation
- Dawid-Skene, multi-rater aggregation, crowdsourcing, CBCC
- Venn-Abers calibration, conformal prediction, selective prediction
- Constraint-based causal discovery, PC algorithm, Meek's rules, CPDAG
- Ego graph, local causal discovery, Markov blanket

## What to Include in Literature

- All LLM x causal discovery methods (2023-2026)
- Survey propagation and related message-passing algorithms
- Multi-rater aggregation models (Dawid-Skene and extensions)
- Calibration with finite-sample guarantees (Venn-Abers, conformal)
- Large-scale constraint-based causal discovery methods

## What to Exclude

- Time-series causal discovery (covered by brainstorm-18)
- Score-based / continuous optimization causal discovery (NOTEARS, GOLEM)
- Causal inference / treatment effect estimation (different problem)
- General LLM reasoning / prompting techniques (unless causal-specific)
```

### A-prompt category details

**A01 — LLM x causal discovery methods**
Focus: MosaCD, CausalFusion, CauScientist, chatPC, ILS-CSL, ALCM, Causal-LLM, MATMCD, ASoT. How each uses the LLM (per-edge, global, iterative). What works, what breaks. ICLR/NeurIPS/KDD reviews where available.
Must-find: MosaCD (Lyu et al. 2025), CausalFusion (Amazon 2025), CauScientist (OpenCausaLab Jan 2026), Wan et al. survey (IJCAI 2025).

**A02 — Belief propagation / message passing / survey propagation**
Focus: Loopy BP convergence (Tatikonda & Jordan 2002), survey propagation for k-SAT (Braunstein et al. 2002), warning propagation, computation tree equivalence, decimation algorithms. Factor graph construction for constraint satisfaction. Cavity method basics.
Must-find: Mezard & Montanari (2009) textbook, Ihler et al. (2005) message errors, Coja-Oghlan (2011) WP convergence.

**A03 — Constraint-based causal discovery at scale**
Focus: PC variants (PC-stable, CPC, FCI), large-graph methods, local discovery (HITON, MMPC, Markov blanket), Meek's rules (1995) soundness/completeness, sequential edge orientation (Huang & Zhou 2025). Scaling challenges and solutions.
Must-find: Spirtes et al. (2000) Causation textbook, Colombo & Maathuis (2014) PC-stable, Meek (1995).

**A04 — Multi-rater aggregation and reconciliation**
Focus: Dawid-Skene (1979) and extensions, CBCC (Kim & Ghahramani 2012), IBCC, item difficulty models, correlated annotator models, multi-agent debate/consensus mechanisms. Application to structured prediction.
Must-find: Dawid & Skene (1979), Albert & Dodd (2004), Kim & Ghahramani (2012).

**A05 — Calibration with finite-sample guarantees**
Focus: Venn-Abers prediction (Vovk et al. 2004, 2025 ICML), conformal prediction for structured outputs, self-calibrating conformal prediction, selective prediction, coverage-accuracy tradeoffs. Application to graph-valued outputs.
Must-find: Vovk et al. (2025 ICML) generalized Venn-Abers, van der Laan et al. (2024 NeurIPS) self-calibrating CP.

### Key prior work to download via arxiv_to_md.py

```
# Core competitors
MosaCD: 2509.23570
CauScientist: 2601.13614
CausalFusion: (Amazon Science, check for arXiv ID)
Wan et al. survey: 2402.11068

# Sequential orientation (closest non-LLM analog)
Huang & Zhou 2025: 2506.05590

# Venn-Abers
Generalized Venn-Abers (ICML 2025): 2502.05676
Self-Calibrating CP: 2402.07307

# Multi-agent causal
MATMCD: 2412.13667
Causal-LLM: (check EMNLP 2025 proceedings)
```

---

## Vetting Progress (2026-03-05)

- [x] Step 1: Understand the idea
- [x] Step 2: Stress test (scope, novelty, feasibility, venue)
- [x] Novelty check: CausalFusion + CauScientist identified; differentiator reframed
- [x] Angle selection: Angle 1 (Message-Passing) chosen
- [x] Mathematical foundations: SP, Dawid-Skene, CBCC, Venn-Abers, computation tree
- [x] Formalize the SP mapping (factor graph, potentials, update rules, decimation criterion)
- [x] Lit check: verified no prior SP/DS/VA connection to causal discovery
- [x] Concrete walkthrough: Insurance network, DrivingSkill seed, 2 rounds, reconciliation
- [x] Phi consistency potential: closed-form derivation, weighted 2-SAT theorem
- [x] MVE protocol: matched A/B comparison, go/no-go thresholds
- [x] Graduation package: topic.yml, topic_brief.md, A-prompt specs, arXiv IDs
- [ ] **NEXT: Graduate to brainstorm-27-ego-causal** (user will handle with new agent)
- [ ] Run MVE during implementation (one afternoon, ~$5)
