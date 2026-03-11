# A) Revised proposal (Proposal v2)

## Ego-Causal: CI-Conditioned Ego-Graph Orientation for LLM-Assisted Skeleton-Based Causal Discovery

**Citation convention.** `[#k]` refers to the `k`-th entry in `literature.md`, using the same sequential order-of-appearance convention as proposal v1 (for example, `[#1] = MosaCD`, `[#4] = chatPC`, `[#30] = Meek`, `[#48] = Dawid–Skene`, `[#66] = Generalized Venn-Abers`).

### Abstract

This proposal studies an underexplored operating point for LLM-assisted causal discovery: a **CI-conditioned ego-graph orientation layer** on top of a standard constraint-based skeleton. Rather than asking the LLM to judge one edge at a time or to plan over an entire graph, Ego-Causal presents the model with a node-centered ego graph and asks it to score the directions of all incident edges jointly. Those soft semantic scores are combined with **hard local feasibility constraints** derived from separating sets, unshielded triples, and already compelled orientations; the resulting node-local problem is solved exactly or near-exactly as a small constrained optimization problem. Edge-level judgments from both endpoints are then reconciled statistically, propagated conservatively with Meek-style rules and rollback safeguards, and converted into **selective edge orientations** with calibrated confidence. The proposal does **not** claim a new causal discovery paradigm, a new SAT formulation, a new annotator-aggregation model, or graph-level finite-sample uncertainty guarantees. Its contribution is the design and evaluation of a specific composition: local-context prompting, hard local constraint compilation, conservative propagation, and calibrated abstention inside a standard skeleton-based pipeline. The primary empirical claim is an **orientation-layer** claim: on sparse graphs and at matched token budgets, ego-graph prompting can improve the accuracy-cost tradeoff relative to per-edge prompting. Formal uncertainty claims, if made, are restricted to edge-level selective outputs across exchangeable graph instances, while within-graph calibration is empirical only [#1, #4, #30, #32, #33, #48, #53, #66, #70, #71].

## 1. Problem statement, scope, and design resolutions

Constraint-based causal discovery already has a strong local-to-global backbone. A PC-family method finds a skeleton and separating sets; collider logic orients some unshielded triples; Meek’s rules propagate the consequences; and the output is a CPDAG or PAG representing the equivalence class implied by the observed independences [#30, #31, #32, #33, #35]. The weakness of this pipeline is also classical: observational conditional independence often identifies only an equivalence class, and finite-sample CI error can destabilize separating sets, collider calls, and propagation [#32, #33, #35, #45, #46].

Recent LLM-assisted causal-discovery methods cluster into two common design patterns. One is **small local queries**: ask the model about single edges, single CI statements, or small pairwise decisions, as in MosaCD and chatPC [#1, #4]. The other is **graph-level iterative refinement**: propose and revise larger graph structures using statistical feedback or multi-agent loops, as in CausalFusion, CauScientist, ILS-CSL, MAC, and ASoT [#2, #3, #6, #9, #10]. Both are useful baselines, but they leave open a middle ground: use the LLM on a bounded local neighborhood that is large enough to expose mechanism-level context, yet still tightly conditioned on the CI structure already recovered by a classical backend.

This proposal targets that middle ground. The central object is the **ego graph** of a node: the node, its current neighbors, the local neighbor-neighbor adjacencies, and the CI facts that constrain which local orientation patterns are feasible. The motivating hypothesis is not that the ego graph is *the* uniquely correct interface for LLM reasoning, but that it is a useful and underexplored interface for skeleton-based edge orientation: richer than per-edge prompting, more auditable than whole-graph planning, and naturally matched to the local structure exploited by PC/CPC-style methods [#1, #4, #13, #36, #37, #38, #39, #40, #41, #42, #43].

### Explicit design resolutions prompted by the audits

1. **Primary claim scope.** v2 makes a primary **orientation-layer** claim, not a universal end-to-end causal-discovery claim. Headline results are therefore based on orientation quality given an oracle or estimated skeleton. End-to-end graph recovery is secondary.
2. **Novelty framing.** The novelty claim is narrowed from “new LLM-assisted causal discovery paradigm” to “an underexplored operating point within skeleton-based edge orientation.” The contribution is the composition and evaluation of modules, not novelty in Meek propagation, SAT solving, annotator aggregation, or calibration individually.
3. **Output type.** The v1 output is a **selectively oriented graph with calibrated edge-level confidence** over the supplied skeleton. When global consistency checks and Meek closure produce a valid partially oriented equivalence-class representation, the same output can also be reported as a partial CPDAG-compatible object. We do not claim graph-level finite-sample validity.
4. **Backend choice.** PC-stable is the primary backend because order-independence matters for fair comparison; CPC and consistent-separating-set variants are robustness checks, not the main pipeline [#32, #33, #45].
5. **Reconciliation choice.** Multiclass Dawid–Skene is the primary full-sweep reconciler because it is simple and cheap enough for v1, but a dependence-aware reconciliation analysis is mandatory on the confirmatory subset because endpoint/prompt judgments are correlated [#48, #50, #51, #53, #55, #61].
6. **Evaluation scope.** The confirmatory benchmark matrix is deliberately smaller than in v1. Replication, matched-budget controls, and fixed comparison rules are prioritized over breadth.

These choices resolve the main audit conflicts in favor of a proposal that is narrower, more defensible, and easier to execute without weakening the central idea.

## 2. Related work and precise positioning

### 2.1 LLM-assisted causal discovery

The closest direct baseline in the supplied literature is **MosaCD** [#1]. Like Ego-Causal, it starts from a PC-family skeleton, asks an LLM to orient ambiguous edges using variable semantics plus CI context, then propagates confident decisions. The main difference is the prompting primitive: MosaCD is fundamentally **per-edge**, with repeated vote aggregation over a single ambiguous edge, while Ego-Causal asks the LLM to score **all incident edges around a node jointly** under one local neighborhood description [#1]. That distinction matters because it changes both the information exposed to the model and the expected cost profile.

**chatPC** is another important local baseline, but it uses the LLM as a local **CI oracle** inside PC rather than as a local **orientation oracle** on top of a fixed skeleton [#4]. **Efficient Causal Graph Discovery Using LLMs** provides a strong efficiency baseline from the opposite direction: it avoids all-pairs prompts by growing the graph globally with BFS-style prompting over variable descriptions, rather than by solving constrained neighborhood orientation problems [#5]. **COAT** is the nearest adjacent local paper, but it is about target-centered factor discovery from unstructured inputs rather than fixed-skeleton edge orientation on a known variable set [#13]. Within the supplied literature and the verified 2025–2026 set summarized in `literature.md`, we did not identify another method beyond MosaCD that directly combines fixed-skeleton local neighborhood orientation with conservative propagation [#1, #4, #13].

At a larger scope, **CausalFusion**, **CauScientist**, **ILS-CSL**, **MAC**, and **ASoT** show a different operating point: interleave LLM reasoning with graph-level search, debate, or falsification loops [#2, #3, #6, #9, #10]. Those systems are valuable comparators, but they are architecturally broader, harder to make fully apples-to-apples at the prompt level, and not tailored to the “skeleton fixed, orientation unresolved” setting emphasized here.

Two more adjacent strands matter for the story even though they are not the main comparator. First, **SCD+LLM/SCP** and **Harmonized Prior** treat the reliability of LLM-derived priors as the main problem and push toward better prompt decomposition and prior injection [#7, #8]. Second, **Mitigating Prior Errors** highlights that not all prior mistakes are equally damaging, which strengthens the motivation for explicit reconciliation, confidence estimation, and abstention rather than raw one-shot use of model judgments [#14].

### 2.2 Classical constraint-based and local-discovery foundations

The classical backbone is local evidence plus global propagation. **Meek** formalizes how local arrowhead evidence propagates through an equivalence class [#30]. **PC**, **PC-stable**, and **CPC** define the baseline constraint-based family for skeleton search and cautious orientation [#31, #32, #33]. **RFCI** and **lFCI** show how locality and speed trade off with informativeness when latent variables enter the picture [#35, #41], while **consistent separating sets** and **ICD** address finite-sample coherence and progressive/iterative refinement [#45, #46].

The local-discovery literature gives the right conceptual scaling precedent. **GLL**, **IAMB**, **MMPC**, **HITON**, **sequential local learning**, and **CMB** all show that causal structure can often be queried, discovered, or approximated effectively through neighborhood-bounded problems rather than through global search alone [#36, #37, #38, #39, #42, #43]. **rPC** and **lFCI** further reinforce the idea that bounded local structure is the right scaling primitive when hubs or large graphs make worst-case global conditioning impractical [#40, #41]. Ego-Causal borrows this *local-first* philosophy, but adds LLM semantic priors and explicit abstention to the orientation layer.

### 2.3 Aggregation, conservative propagation, and calibration are borrowed modules

Ego-Causal does not claim novelty in its aggregation model. **Dawid–Skene**, **GLAD**, **BCC/CommunityBCC**, **EBCC**, and later dependence-aware LLM-judge aggregation work already supply the statistical toolbox for combining noisy judges with varying reliability, dependence, and item difficulty [#48, #49, #50, #51, #53, #54, #55, #61]. The proposal’s claim is narrower: endpoint ego-graph judgments and prompt variants can be mapped into this toolbox in a way that is specific to causal edge orientation.

Likewise, the propagation schedule is not presented as a new message-passing theory. The decimation literature mainly serves as a warning and as design inspiration: early irreversible commitments can fail badly, while conservative thresholds, backtracking, and softer constraints can help [#18, #22, #23, #24, #29]. The point is not to claim exact belief-propagation inference over DAG space, but to justify a cautious propagation schedule that does not over-commit.

Finally, the calibration layer imports existing tools rather than inventing new uncertainty machinery. **Venn–Abers**, **multiclass Venn–Abers**, **Generalized Venn/Venn–Abers**, **Conformal Structured Prediction**, and **Conformal Risk Control** are the relevant foundations [#66, #67, #69, #70, #71]. What is new here is their use as an explicit **edge-level selective calibration layer** in LLM-assisted skeleton orientation; any formal guarantee is restricted to exchangeable graph/problem instances, not a single fixed graph.

## 3. Research questions and hypotheses

The proposal is organized around five empirical hypotheses.

**H1 (ego-context hypothesis).** At matched total token budget, ego-graph prompting improves the accuracy-cost tradeoff over per-edge prompting because one query can score multiple incident edges while exposing mechanism-level neighborhood context [#1, #4].

**H2 (hard-constraint hypothesis).** Adding CI-derived hard local constraints improves local consistency and edge-orientation accuracy relative to unconstrained ego scoring because infeasible collider/non-collider patterns are removed from the feasible set [#30, #31, #33, #45].

**H3 (reconciliation hypothesis).** Statistical reconciliation of endpoint judgments improves seed precision at fixed seed coverage relative to majority vote and shuffled voting, provided the gain persists under a dependence-aware sensitivity analysis [#48, #49, #53, #55, #61].

**H4 (propagation hypothesis).** Conservative propagation resolves a substantial fraction of high-confidence, easy-to-medium edges before fallback; the residual tail should be enriched for genuinely hard edges rather than for arbitrary leftovers [#30, #18, #22, #23, #24, #29].

**H5 (selective-output hypothesis).** Post-hoc calibration and abstention reduce false-orientation risk among committed edges and improve selective SHD empirically relative to forced top-1 orientation, while any formal coverage/risk statement is restricted to held-out graph instances [#66, #67, #70, #71].

These are hypotheses to be tested, not results assumed in advance.

## 4. Method

### 4.1 Inputs, assumptions, and outputs

**Inputs**
- Observational tabular data.
- Human-readable variable names and optionally short non-directional descriptions.
- A constraint-based skeleton and separating-set structure from a PC-family backend.

**Primary v1 assumptions**
- Causal sufficiency.
- DAG structure over the measured variables.
- Human-readable metadata are available, but may be weak or partially uninformative.
- CI testing is noisy in finite samples, so the system must tolerate abstention and rollback.

**Primary output**
- A **selectively oriented graph** over the supplied skeleton, with per-edge label space `{u→v, v→u, ?}` and calibrated edge-level confidence.
- If the output is globally consistent and Meek-closed, we also report the corresponding partial CPDAG-compatible representation.

The key modeling principle is strict separation of roles: **CI structure defines what is locally feasible; the LLM only supplies soft preferences within that feasible set.**

### 4.2 Phase 0: skeleton search and local constraint extraction

We run **PC-stable** as the default backend and **CPC** as a robustness variant [#32, #33]. For each dataset we store:
- the undirected skeleton `\hat G`,
- separating sets `\widehat{Sep}(u,w)`,
- unshielded triples,
- any orientations already compelled by standard rule application.

Where finite-sample separating-set instability is severe, we include a **consistent-separating-set** variant as a robustness check [#45]. The LLM does **not** alter the skeleton, sepsets, or CI test results.

This phase supports two evaluation regimes:
1. **Oracle skeleton:** isolates orientation quality from skeleton error.
2. **Estimated skeleton:** tests whether gains survive realistic CI noise.

### 4.3 Phase 1: ego-graph construction and prompting

For each node `v`, define the ego graph

\[
\mathrm{Ego}(v) = \{v\} \cup N(v)
\]

with the induced neighbor-neighbor adjacencies. The prompt includes:
- the center variable and neighbor descriptions,
- local neighbor-neighbor adjacencies,
- a compact summary of CI/separating-set facts involving the ego,
- any already compelled local directions,
- an instruction to score each incident edge and to abstain when evidence is insufficient.

The LLM returns structured JSON with, for each incident edge `(u,v)`:
- a score for `u→v`,
- a score for `v→u`,
- an abstain / insufficient-evidence score,
- a short rationale tag (not a long free-form explanation).

To reduce order effects, we randomize neighbor order and answer-order presentation, following the debiasing lesson highlighted by MosaCD but applying it at the ego level rather than the single-edge level [#1]. All completions are cached.

#### Hub handling

To keep prompts and local solving predictable, v1 caps ego size at degree 8. Higher-degree nodes are split into overlapping sub-egos using a fixed local partition rule (for example, graph clustering or sepset-informed grouping). Hub handling is evaluated explicitly because the expected cost advantage of ego-level prompting may weaken on hub-heavy graphs [#40, #41].

### 4.4 Phase 2: local hard-constraint compilation and exact local solving

For each node `v`, introduce a binary variable `b_{u,v}` for every **currently unresolved** incident edge `(u,v)`:
- `b_{u,v}=1` means `u→v`,
- `b_{u,v}=0` means `v→u`.

The local decision problem is a hard-feasible, soft-scored optimization. The proposal uses a weighted Max-2SAT view in implementation, but the methodological claim is broader: **compile CI-derived local feasibility constraints, then solve the local feasible set exactly or near-exactly.**

#### Hard clauses from collider / non-collider logic

For each unshielded triple `u - v - w` with `u` and `w` nonadjacent:
- If `v \notin \widehat{Sep}(u,w)`, then `v` must be a collider, so add unit clauses enforcing
  - `b_{u,v}=1`,
  - `b_{w,v}=1`.
- If `v \in \widehat{Sep}(u,w)`, then `v` cannot be a collider, so add
  - `(\neg b_{u,v} \lor \neg b_{w,v})`.

Add unit clauses for any already compelled orientations from Meek closure or cycle-safe prior commitments [#30, #31, #33, #45].

#### Soft objective from LLM scores

If the LLM supplies local direction scores `s_{u→v}` and `s_{v→u}`, maximize

\[
\max_b \sum_{u \in N(v)} \Big[s_{u\to v}\, b_{u,v} + s_{v\to u}\, (1-b_{u,v})\Big]
\]

subject to the hard clauses above.

For degree `d(v) ≤ 8`, exact enumeration over `2^{d(v)}` assignments is feasible. For larger local problems, we use PySAT / OR-Tools or the hub-splitting rule described above.

#### Pre-specified infeasibility rule

Estimated skeletons and noisy separating sets can make local hard clauses conflict. v2 therefore fixes the infeasibility policy up front:

1. **Only CI-derived clauses and Meek-compelled orientations are irrevocable within a backend run.** Soft LLM preferences never become hard constraints by themselves.
2. If a local problem is infeasible, remove recent **soft-derived** propagated unit clauses touching the ego, rerun local solving, and record a rollback event.
3. If the ego remains infeasible, mark that ego as **unresolved under the current backend**, abstain on its incident ambiguous edges, and optionally re-check the region in the CPC or consistent-sepset robustness run.
4. Report infeasibility rate, rollback rate, and the fraction of final edges affected by infeasibility handling.

This rule keeps the “LLM cannot override CI facts” principle while acknowledging finite-sample noise.

### 4.5 Phase 3: dual-endpoint reconciliation

Each unresolved edge `(u,v)` receives at least two local judgments:
- one from `\mathrm{Ego}(u)`,
- one from `\mathrm{Ego}(v)`.

With prompt randomization, an edge may receive several additional judgments. We treat these as noisy annotators over the ternary label space

\[
Y_{uv} \in \{u\to v,\; v\to u,\; ?\}.
\]

#### Primary full-sweep reconciler

The v1 backbone is **multiclass Dawid–Skene** [#48]. It is chosen for three reasons:
- interpretability of per-view confusion behavior,
- low estimation and implementation burden,
- feasibility for broad confirmatory sweeps.

#### Mandatory dependence-aware sensitivity analysis

Because endpoint and prompt-variant labels are not conditionally independent, v2 does **not** rely on DS alone for its headline reconciliation story. On the confirmatory subset, we also run a dependence-aware reconciliation analysis using EBCC/BCC-style partial pooling and grouped prompt-family diagnostics [#50, #51, #53]. Recent dependence-aware LLM-judge aggregation work provides further motivation for this check [#55, #61].

**Decision rule:** the proposal’s claim is about *reconciliation as a class of methods*, not about DS specifically. If a dependence-aware model materially changes the calibration or ranking of seed confidence, the discussion will foreground that result instead of presenting DS as sufficient.

#### Edge-difficulty features

We record per-edge difficulty features motivated by GLAD and later heterogeneous-item models [#49, #54]:
- endpoint disagreement,
- local-solver margin,
- node degree / hub status,
- sepset size and instability,
- whether the edge was directly compelled or only softly preferred,
- decision source (hard CI, local solve, propagation, fallback).

These features are later used for calibration, stratified reporting, and hard-tail analysis.

### 4.6 Phase 4: conservative propagation schedule

The propagation stage is inspired by the decimation literature, but v2 no longer describes it as a message-passing contribution. It is a **conservative propagation schedule** over reconciled local orientations.

The algorithm maintains a priority queue over unresolved edges or regions, ordered by calibrated confidence and local consistency margin. It then iterates:
1. pick the next highest-confidence unresolved region,
2. commit only directions above a threshold that do not create an immediate directed cycle,
3. apply **Meek’s rules** after each small batch [#30],
4. turn newly compelled orientations into unit clauses for affected ego problems,
5. re-solve only affected egos.

#### Backtracking safeguard

The decimation literature makes clear that early irreversible commitments can cascade into failure [#18, #22, #23, #24, #29]. We therefore add rollback triggers:
- contradiction spike in nearby ego problems,
- repeated cycle rejections in a local region,
- large local-margin collapse after a new batch,
- increase in unresolved-edge count after ostensibly “confident” updates.

When triggered, the algorithm undoes the lowest-margin recent commitments, lowers the batch size, and raises the commit threshold locally.

### 4.7 Phase 5: budgeted hard-tail fallback

After conservative propagation converges, a residual set of ambiguous edges remains. For those edges only, the system switches to a **per-edge fallback** modeled on MosaCD-style prompting [#1].

The fallback prompt may include:
- endpoint descriptions,
- relevant separating-set and CI summaries,
- nearby oriented-chain context,
- repeated order-randomized prompts if necessary.

To keep cost predictable and preserve selective output, fallback is **budgeted**. If the residual ambiguous tail exceeds 10–15% of unresolved skeleton edges after propagation, the system does **not** force completion. It reports the partial selective output instead.

### 4.8 Phase 6: calibration and selective output

The final stage turns reconciled posteriors into calibrated selective decisions.

#### Calibration target

For each edge, the calibrator uses:
- the reconciled posterior over `{u→v, v→u, ?}`,
- edge-difficulty features,
- decision source (hard CI / local solve / propagation / fallback).

#### Calibrator

v2 uses **multiclass Venn–Abers** as the primary v1 calibrator because it matches the ternary label-space design more naturally than a graph-level structured guarantee [#66, #67, #71]. Calibration is fit **only on held-out graph instances**, not on held-out edges from the same test graph.

#### Risk control and abstention

**Conformal Risk Control** is used only to select operating thresholds for a monotone risk target, such as the false-orientation rate among committed edges [#70]. It is **not** used to claim graph-level validity, and selective SHD is treated as an empirical operating characteristic rather than the guaranteed target.

#### Output rule

For each edge:
- output a direction if calibrated confidence passes the chosen operating threshold,
- otherwise output `?`.

Formal statements, if made, are therefore limited to **marginal edge-level coverage/risk across held-out graph instances**. Within a single fixed graph, coverage and selective SHD are reported empirically.

### 4.9 Audit and provenance layer

Every final edge receives a machine-checkable trace containing:
- decision source,
- local hard clauses,
- local-solver margin,
- endpoint judgments,
- reconciled posterior,
- calibrated score,
- commit / rollback / abstain reason.

The audit layer is not only logged; it is explicitly evaluated in the experiment plan.

### 4.10 Pipeline diagram

```text
observational data + metadata
            |
      PC-stable skeleton
   (+ CPC / consistent-sepset robustness)
            |
     skeleton + sepsets + triples
            |
   build capped ego graph for each node
            |
   LLM scores all incident edge directions
   under local CI summaries + semantics
            |
 local hard-constraint compilation + exact solve
            |
  endpoint reconciliation (DS backbone,
 dependence-aware sensitivity analysis)
            |
 conservative propagation + Meek closure
      + cycle checks + rollback
            |
   budgeted per-edge fallback on hard tail
            |
 multiclass Venn-Abers calibration + abstention
            |
 selectively oriented graph with calibrated
       edge-level confidence (partial CPDAG
        reported only when consistency checks pass)
```

## 5. Evaluation design

### 5.1 Claim scope and evaluation modes

v2 distinguishes two evaluation modes.

1. **Orientation-only evaluation on a fixed skeleton (primary).** Measure how well the method orients edges given either an oracle or estimated PC-family skeleton.
2. **End-to-end graph recovery (secondary).** Measure overall recovered structure when skeleton search and orientation are combined.

Headline claims will be based on the first mode. End-to-end claims will be made only when strong non-LLM data-only baselines are included.

### 5.2 Confirmatory vs exploratory benchmark suite

#### Confirmatory suite (main paper)

Named benchmarks chosen to overlap prior LLM-causal papers where possible:
- Asia,
- Sachs,
- Alarm,
- Insurance [#1, #4, #5].

Synthetic graphs:
- 100-node Erdős–Rényi sparse DAGs,
- 100-node scale-free sparse DAGs,
- average degree in `{2, 4}`,
- linear-Gaussian SEMs,
- sample sizes `n ∈ {500, 2000}`,
- both oracle and estimated skeletons,
- metadata conditions `{descriptions, anonymized}`.

Replication minimum for each synthetic condition:
- at least 10 DAG draws,
- at least 3 sample draws per DAG.

If budget becomes tight, v2 reduces the number of conditions before reducing replication below this minimum.

#### Exploratory / appendix suite

- Child, Hepar2, Win95pts, and one of Pathfinder / an Insurance robustness rerun [#1].
- 200-node synthetic sparse graphs.
- Nonlinear additive-noise synthetic family.
- `names-only` metadata ablation.
- Dependence-aware reconciliation beyond the confirmatory subset.
- Optional large real graph only if metadata can be curated safely.

### 5.3 Baselines and controls

#### Orientation-only matched-backbone baselines

1. **PC-stable + Meek** [#30, #32].
2. **CPC + Meek** [#30, #33].
3. **Consistent-separating-set variant** where finite-sample sepset instability is relevant [#45].
4. **MosaCD-style per-edge prompting + propagation** under the same skeleton, metadata condition, LLM model, and token budget [#1].
5. **Per-edge same-information baseline:** the same fields as Ego-Causal, but queried one target edge at a time.
6. **Same-context per-edge control:** the same local neighborhood context shown to the ego prompt, but only one queried edge is scored. This isolates joint local reasoning from “just seeing more context.”
7. **CI-only local solver:** the same local hard-constraint layer but with uniform / uninformative soft weights.
8. **Semantics controls:** descriptions without CI summaries, and anonymized variables without descriptions.

#### Secondary end-to-end baselines

For secondary end-to-end tables, include:
- one standard score-based baseline,
- one continuous-optimization baseline for continuous synthetic settings,
- chatPC and Efficient BFS as secondary LLM baselines where applicable [#4, #5].

CausalFusion and CauScientist are treated as literature-reference comparators unless code and prompt details support a faithful reproduction [#2, #3].

### 5.4 Fair-comparison rules

Any direct comparison in the same result table must match on:
- dataset split,
- skeleton condition (oracle or estimated),
- metadata condition,
- variable descriptions,
- LLM model ID/version,
- temperature / top_p / max_tokens,
- prompt repeat count and order-randomization policy,
- fallback budget,
- cycle-check policy,
- threshold-tuning budget.

Each main comparison reports both:
1. fixed-budget results at three total-token budgets, and
2. full accuracy-vs-cost curves.

A single matched-token point is not sufficient.

### 5.5 Core experiments

#### E1. Context-isolated ego vs per-edge comparison

Compare:
- per-edge minimal prompt,
- per-edge same-context control,
- ego prompt without local solver,
- ego prompt + local solver.

Primary readouts:
- oriented-edge precision / recall / F1,
- arrowhead F1,
- unresolved fraction,
- tokens and cost per correct orientation.

**Design target:** at matched total tokens within ±10%, ego + local solving should either improve oriented-edge F1 by at least 5 absolute points over the best per-edge control, or match within 2 points at no more than 35% of cost.

#### E2. Hard-constraint benefit and infeasibility analysis

Compare:
- ego prompt without hard constraints,
- ego prompt + hard local constraints,
- CI-only local solver.

Report:
- oriented-edge precision / F1,
- hard-clause violation rate,
- collider/non-collider consistency,
- infeasibility rate,
- error breakdown by triple type.

**Design target:** zero hard-clause violations by construction, measurable precision/F1 gain over unconstrained ego scoring, and explicit infeasibility statistics in estimated-skeleton settings.

#### E3. Reconciliation and dependence test

Compare:
- majority vote,
- shuffled voting,
- multiclass DS,
- DS + difficulty features,
- dependence-aware EBCC/BCC-style analysis on the confirmatory subset.

Readouts:
- seed precision at fixed seed coverage,
- seed recall,
- Brier score,
- NLL,
- ECE,
- endpoint-disagreement error rate.

**Design target:** at matched seed coverage, DS or a dependence-aware variant should improve seed precision by at least 5 points over raw majority vote and at least 3 points over shuffled voting; if dependence-aware aggregation improves calibration materially, its result takes precedence in interpretation.

#### E4. Propagation and hard-tail decomposition

Operationalize edge difficulty using endpoint disagreement, local-solver margin, node degree, sepset instability, and decision source. Compare the full method against no-Meek, no-backtracking, and no-fallback variants.

Readouts:
- fraction of edges resolved before fallback,
- propagated-edge precision,
- rollback rate,
- cycle rejection count,
- hard-tail composition by difficulty stratum.

**Design target:** at least 80% of the easiest-half edges resolved before fallback, with propagated-edge precision within 2 points of final precision and the residual tail concentrated among harder edges.

#### E5. Scaling and efficiency on sparse graphs

Run the confirmatory synthetic suite and compare the full method against MosaCD-style per-edge prompting, the same-context per-edge control, and Efficient BFS where appropriate [#1, #5].

Readouts:
- oriented-edge F1,
- unresolved fraction,
- API calls,
- total tokens,
- dollar cost,
- wall-clock time,
- cost per correct committed orientation.

**Design target:** on sparse 100-node graphs, either match the per-edge baseline within 2 F1 points at ≤35% of cost/tokens, or exceed it by at least 5 F1 points at similar cost.

#### E6. Calibration and selective prediction

Calibrate on held-out graph instances only. Compare uncalibrated posteriors, simple post-hoc scaling baselines, and multiclass Venn–Abers. Use CRC only to choose an abstention threshold for false-orientation risk [#66, #67, #70, #71].

Readouts:
- empirical coverage at 80/90/95%,
- false-orientation rate among committed edges,
- Brier score,
- NLL,
- ECE,
- average prediction-set size,
- selective SHD (empirical),
- metrics stratified by decision source and difficulty stratum.

**Design target:** at nominal 90% coverage, empirical coverage between 87% and 93% on held-out graph instances, ECE ≤ 0.03, and selective SHD at fixed coverage at least 10% lower than forced top-1 orientation.

#### E7. Provenance and audit evaluation

Turn the audit layer into an evaluated artifact rather than a logging feature.

Readouts:
- provenance coverage,
- fraction of committed edges with machine-checkable derivations,
- error rate by decision source,
- counterfactual trace-fidelity check (remove the top cited evidence item and measure confidence change).

**Design target:** all committed edges have machine-checkable provenance, hard-clause violation rate is zero, and the lowest-error strata correspond to the most trusted decision sources.

### 5.6 Metrics and statistical analysis

#### Primary metrics
- oriented-edge F1 at fixed budget,
- false-orientation rate among committed edges at target coverage.

#### Secondary metrics
- SHD (secondary / end-to-end),
- arrowhead precision / recall,
- unresolved-edge fraction,
- seed precision / recall before propagation,
- tokens per correct orientation,
- wall-clock time,
- Brier score,
- NLL,
- ECE,
- infeasibility rate,
- rollback rate,
- cycle-rejection count.

#### Unit of analysis and inference

The unit of analysis is one sampled dataset from one ground-truth DAG. **Edges are not treated as independent observations for significance testing.**

For the synthetic confirmatory suite we use:
- 95% paired hierarchical bootstrap over DAG draw and sample draw,
- paired permutation test or Wilcoxon signed-rank test on per-instance differences for the primary hypotheses,
- Holm correction over the primary hypotheses.

For small named benchmarks, results are primarily descriptive and do not rely on edge-level p-values.

### 5.7 Threats-to-validity gates

Before making headline claims, the study must pass the following gates.

1. **Benchmark contamination gate.** If named-benchmark performance greatly exceeds anonymized and held-out synthetic performance, claims are narrowed to semantic prior injection rather than data-grounded causal orientation.
2. **Metadata gate.** Variable descriptions may define variables but may not contain directional language, interventions, or known benchmark relations.
3. **Baseline-fidelity gate.** No direct apples-to-apples claim is made against a system without official code or sufficiently detailed prompts.
4. **Estimated-skeleton gate.** No success claim is made if gains appear only with oracle skeletons.
5. **Anonymization gate.** No headline claim is made unless gains persist, at least partially, under anonymized variables.
6. **Infeasibility gate.** Infeasibility rate, rollback rate, cycle-rejection count, and manual intervention count must be reported whenever estimated skeletons are used.
7. **Fair-compute gate.** Every accuracy comparison must be paired with unresolved fraction and cost per correct orientation, not just raw tokens or raw F1.

## 6. Risks and mitigations

**Skeleton and equivalence-class limits.** No orientation layer can recover edges that are missing from the skeleton, and no method can orient what is not identifiable from the observed equivalence class. Mitigation: keep oracle vs estimated skeletons separate, use PC-stable as default, and report abstention instead of forced completion [#30, #32, #33, #45].

**Correlated endpoint judgments.** DS can be overconfident under dependence. Mitigation: treat DS as the full-sweep baseline only, run dependence-aware reconciliation on the confirmatory subset, and stratify calibration by decision source [#48, #53, #55, #61].

**Hub nodes and prompt inflation.** Ego prompts may lose their cost advantage on scale-free graphs. Mitigation: hard degree cap, overlapping sub-egos, and dedicated hub stress tests [#40, #41].

**Fallback tail inflation.** A large residual tail can erase the budget advantage. Mitigation: cap fallback to 10–15% of unresolved edges and keep a partial output otherwise [#1].

**Calibration overreach.** Edge judgments within a single graph are dependent. Mitigation: fit calibrators on held-out graph instances only, report within-graph calibration empirically, and restrict formal statements to across-instance marginal guarantees [#66, #67, #70, #71].

**Baseline reproducibility.** Some global LLM baselines are hard to reproduce faithfully. Mitigation: direct comparison only where prompt/code fidelity is adequate; otherwise cite them as contextual comparators [#2, #3].

## 7. Compute, data, and timeline

### 7.1 Compute and budget

The system is CPU-first: no gradient training is required, and the main cost is API inference plus caching. A **confirmatory suite** with a mini model, cached completions, reused ego outputs across experiments, and a capped fallback tail is plausible within a **low-hundreds-of-dollars API budget**. Broader 200-node, nonlinear, or dependence-aware extension sweeps are exploratory and may require additional budget.

### 7.2 Data requirements

Required assets:
- benchmark DAG definitions and simulation code,
- observational samples at the chosen `n`,
- a blinded metadata protocol and metadata files,
- held-out graph-level train/dev/test splits for calibration and model selection,
- graph generators for sparse ER and scale-free DAGs.

The most important non-algorithmic asset is the **metadata protocol**. Descriptions must be informative enough to define variables, but scrubbed of directional or benchmark-specific causal language.

### 7.3 Reuse and caching policy

Experiments E1, E2, and E6 reuse the same cached ego-query outputs wherever possible. Reconciliation, calibration, and many ablations are therefore mostly CPU-side once the prompt outputs exist.

### 7.4 Timeline

Assume **1 full-time research engineer and 0.25 FTE research lead/advisor**.

- **Weeks 1–2:** loaders, metadata protocol, PC-stable/CPC wrapper, ego builder, prompt cache, JSON schema.
- **Weeks 3–4:** local hard-constraint solver, infeasibility handling, per-edge and same-context controls.
- **Weeks 5–6:** DS reconciliation, propagation engine, cycle check, rollback, initial confirmatory benchmarks.
- **Weeks 7–8:** 100-node synthetic suite, scaling/cost experiments, fallback cap.
- **Weeks 9–10:** calibration split, multiclass Venn–Abers, selective risk curves, provenance evaluation.
- **Weeks 11–12:** ablations, robustness subset, writeup, figures, error analysis.

Add 4–6 more weeks for 200-node graphs, richer dependence-aware aggregation, or faithful reproduction of broader global baselines.

## 8. Expected contributions

If successful, the project contributes:

1. A carefully scoped **ego-graph orientation layer** for LLM-assisted causal discovery that sits between per-edge prompting and whole-graph planning.
2. A concrete **hard local constraint compilation** design showing how CI-derived collider/non-collider logic can limit semantic LLM preferences without letting the LLM override structure.
3. A **selective-output framing** for LLM-assisted skeleton orientation, with explicit abstention, calibration, and provenance rather than forced full-graph claims.
4. A more rigorous **evaluation protocol** for LLM-assisted causal orientation: same-context controls, matched budgets, orientation-only vs end-to-end separation, graph-level calibration splits, and audited decision traces.

The intended contribution is therefore not “LLMs solve causal discovery,” but rather: **there is a viable, testable, and auditable local-context operating point between per-edge querying and full-graph LLM planning, and it should be evaluated as an orientation layer rather than as a universal discovery engine.**

---

# B) Revision notes

## Major changes and which audit prompted them

- Narrowed the novelty claim from a broad “new LLM orientation paradigm” to an **underexplored operating point** inside skeleton-based edge orientation. The revised abstract and related-work sections now say the novelty is in the composition and evaluation of ego-context prompting, hard local constraints, conservative propagation, and abstention, not in Meek rules, SAT, DS/EBCC, or calibration alone. **Prompted by:** C01, C02.

- Reframed the proposal as a **primary orientation-layer paper** with secondary end-to-end evaluation, instead of making universal end-to-end causal-discovery claims. This aligns the story, claims, and evaluation. **Prompted by:** C03, C05.

- Replaced “the ego graph is the right unit of LLM reasoning” with the weaker and more defensible claim that ego-graph prompting is a **useful middle ground** between per-edge prompting and whole-graph planning. **Prompted by:** C01, C02.

- Changed the output from “calibrated partial CPDAG” to **selectively oriented graph with calibrated edge-level confidence**, and only report partial CPDAG compatibility when consistency checks and Meek closure support it. **Prompted by:** C02, C03, C04, C05.

- Froze the primary backend choice to **PC-stable**, with **CPC** and **consistent-separating sets** as robustness variants. This resolves an open v1 TODO and avoids letting backend choice blur the main claim. **Prompted by:** C02, C03, C05.

- Kept **multiclass Dawid–Skene** as the full-sweep backbone for feasibility, but made a **dependence-aware reconciliation analysis mandatory on the confirmatory subset**. This explicitly resolves the C03 vs C05 tension: the method remains feasible, but no headline reconciliation claim rests on DS alone. **Prompted by:** C03, C05.

- Added a **pre-specified infeasibility policy** for hard local clauses under estimated skeletons: rollback soft-derived commitments, abstain on unresolved egos if needed, and report infeasibility statistics. **Prompted by:** C03.

- Softened the “message passing / decimation” framing into a **conservative propagation schedule** justified by the decimation literature, rather than a claimed message-passing contribution. **Prompted by:** C01, C02.

- Reworked the evaluation around a **smaller confirmatory suite** (4 named benchmarks + 100-node sparse synthetic graphs) plus an exploratory appendix suite, so the plan is statistically powered and feasible rather than over-broad. **Prompted by:** C03, C05.

- Added the missing **same-context per-edge control**, so any ego-graph advantage cannot be explained away as “just more context.” **Prompted by:** C04.

- Added a **propagation / hard-tail decomposition** experiment that explicitly measures whether propagation resolves easier edges before fallback, instead of assuming that claim. **Prompted by:** C04.

- Added stronger evaluation controls: **fair-comparison rules**, fixed-budget comparisons plus cost curves, graph-level calibration splits, graph-instance-level inference, and explicit success targets for the main experiments. **Prompted by:** C03, C04.

- Tightened the calibration story: **multiclass Venn–Abers** is now the primary v1 calibrator; **CRC** is used only for false-orientation-risk threshold selection; formal claims are limited to **held-out graph instances**, and within-graph calibration is empirical only. **Prompted by:** C02, C03, C04, C05.

- Added a **hub cap and sub-ego strategy** (degree cap 8 in v1) plus a dedicated hub stress test, so the cost and solver claims are benchmark-conditional rather than universal. **Prompted by:** C02, C05.

- Added **budgeted fallback** (10–15% cap) and a rule to keep a partial output instead of forcing completion when the hard tail is too large. **Prompted by:** C04, C05.

- Turned the audit layer from a logging feature into an **evaluated provenance artifact** with machine-checkable traces and trace-fidelity checks. **Prompted by:** C04.

## Explicit conflict resolutions

- **DS vs EBCC/BCC as the “main” reconciler:** chose **DS as the shipped full-sweep backbone**, but required **dependence-aware sensitivity analysis on the confirmatory subset** and explicitly limited the interpretation of reconciliation gains unless they persist. This balances C03’s statistical concern with C05’s feasibility constraint.

- **Broad end-to-end ambition vs feasible, rigorous study:** chose **orientation-only evaluation as the primary claim** and moved end-to-end recovery to secondary status. This preserves rigor without dropping the larger motivation.

- **Graph-level calibration language vs honest guarantees:** chose **edge-level selective calibration** across held-out graph instances, with empirical within-graph analysis only. This resolves the overclaim risk identified across C02–C05.

- **Large benchmark matrix vs sufficient replication:** chose a **smaller confirmatory matrix** with stronger replication and more controls, then moved broader datasets and 200-node studies to exploratory status.

## Unresolved questions / TODOs

- If the bibliography is expanded beyond `literature.md`, add the adjacent citations flagged in C01 that are not currently in the supplied literature pack (for example, the “imperfect experts” paper and other alternative local-query interfaces). In v2, the novelty claim was narrowed so the proposal remains defensible without them.

- Decide whether the dependence-aware confirmatory analysis will use a full **EBCC-style model**, a lighter grouped-prompt-family Bayesian model, or both.

- Finalize the exact sub-ego partition rule for degree `> 8` nodes and specify whether it is based on local clustering, sepset structure, or a fixed neighborhood ordering.

- Choose the specific **score-based** and **continuous-optimization** end-to-end baselines that match the final synthetic data regime and are realistic to implement.

- Decide whether the exploratory appendix will include a **latent-confounder extension** using RFCI/lFCI, or defer that entirely to future work.

- Finalize the benchmark-recognition / contamination audit protocol and whether it includes an explicit prompt asking the LLM to identify named benchmark networks from variable lists.

- Determine whether the final selective operating point in the headline tables will be keyed primarily to **false-orientation risk**, **coverage**, or a small set of standard operating points (for example, conservative / balanced).