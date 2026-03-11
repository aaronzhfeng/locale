# Slide Outline — LOCALE

**Working title**: LOCALE: Ego-Graph Orientation for LLM-Assisted Causal Discovery

**Audience**: Professor Biwei Huang + DSC 190 peer students (they saw the Wan et al. + MosaCD presentation)

**Narrative arc**: In our earlier presentation, we identified the gap — per-edge methods waste the LLM's context, global methods don't scale. We proposed ego-graph prompting as the middle ground. We built LOCALE to test this. The diagnostic findings turned out to be as interesting as the pipeline: skeleton coverage is the real bottleneck, nearly all CI errors are false colliders, and open-source 27B models match proprietary ones. We close by mapping what we learned back to MosaCD's limitations and what remains open.

---

## PART 1: CONTEXT — Where We Left Off (3 slides)

### Slide 1 — Title
- "LOCALE: Ego-Graph Orientation for LLM-Assisted Causal Discovery"
- Aaron Feng | DSC 190 | Prof. Biwei Huang
- Subtitle: "From course presentation to research prototype"

### Slide 2 — Recap: The Landscape We Presented
- Wan et al. survey: three paradigms for LLM × causal discovery
  - Knowledge-driven (LLM only, no data)
  - Data-driven, per-edge (MosaCD, chatPC) — O(E×K) queries, ~200 tokens each
  - Data-driven, global (CausalFusion, CauScientist) — O(V²) context per query
- MosaCD: shuffled queries + non-collider-first propagation → best F1 in 9/10 benchmarks
- But: each query uses the LLM as a binary classifier. 128K context window, ~200 tokens used.
- Visual: the three paradigms on a spectrum (per-edge ← ? → whole-graph)

### Slide 3 — The Gap We Identified
- **Per-edge methods** (MosaCD): one query = one binary classification. No local consistency. CI constraints checked *after* LLM, not *during*.
- **Global methods** (CausalFusion): entire DAG in context. O(V²) tokens. Doesn't scale. LLM does what Meek rules already do.
- **The missing middle**: ego-graph prompting. Show the LLM one node's neighborhood. It scores all incident edges jointly, sees the CI constraints, reasons about local mechanism consistency. O(d) context. O(n) queries.
- This is what we built.

---

## PART 2: WHAT WE BUILT (2 slides)

### Slide 4 — LOCALE Pipeline Overview
- Phase 0: PC-stable skeleton + separating sets (standard, no LLM)
- Phase 1: Ego-graph LLM scoring — one query per node, K=10 votes, structured JSON output
- Phase 2: CI-derived constraints via Max-2SAT (NCO: non-collider only)
- Phase 3: Confidence-weighted dual-endpoint reconciliation
- Phase 4: Safety valve — damage detection + conservative filtering
- LLM does local reasoning; algorithm handles global consistency
- Visual: pipeline flow diagram with ego-graph prompt example inset

### Slide 5 — The Ego-Graph Prompt (Concrete Example)
- Show actual prompt for DrivingSkill node (Insurance network):
  - Node + description
  - 4 neighbors with descriptions
  - CI statistics: separating sets, p-values
  - Cross-neighbor evidence: which pairs are separated by this node
  - Task: orient all edges jointly
- One query → 4 edge orientations. MosaCD: 4 × 10 = 40 queries.
- The LLM sees the constraints and domain knowledge simultaneously (phi × psi)

---

## PART 3: WHAT WE FOUND (7 slides)

### Slide 6 — Finding 1: Ego vs Per-Edge — It Depends on Scale
- Scale trend (same edges, same skeleton, same CI evidence):
  - 4B: ego 47% vs per-edge 91% (catastrophic — model too small for joint reasoning)
  - 9B: ego 80% vs per-edge 91% (gap closing)
  - 27B: ego 95% vs per-edge 94% (crossover — ego matches or wins)
- Ego-graph prompting requires sufficient model capacity (≥27B)
- At 27B: ego ties or wins depending on domain familiarity
- Visual: line chart, accuracy vs model size, two lines crossing at 27B

### Slide 7 — Finding 2: F1 Decomposition — Skeleton Is the Bottleneck
- Decomposed directed-edge F1 into: skeleton coverage × orientation accuracy
- On edges the skeleton gets right, orientation is at ceiling:
  - Insurance: 100% orientation accuracy (F1 gap entirely from skeleton miss)
  - Asia: 100%
  - Alarm: 89.9%
- The F1 gap vs MosaCD is skeleton coverage (52-88%), not orientation quality
- Implication: improving the LLM orientation layer has diminishing returns. The field should focus on better skeletons.
- Visual: stacked bar chart — skeleton miss vs orientation error per network

### Slide 8 — Finding 3: The NCO Discovery — False Colliders Dominate
- When we added CI-derived hard constraints (Phase 2), it *hurt* on 3/6 networks
- Diagnosed why: 100% of incorrect CI facts are false colliders
  - PC says "collider" (Z not in sep set) when ground truth says "non-collider"
  - Zero false non-colliders observed across 6 networks
- Why? Non-collider = positive evidence (Z IS in sep set). Collider = absence of evidence (Z NOT FOUND in any sep set). Absence fails with finite samples.
- Validated across sample sizes: 100% false-collider rate at n≥5000, 93-99% at n=1000-2000
- Fix: use only non-collider constraints (NCO). 100% reliable. Immediately adoptable.
- This is method-agnostic — applies to MosaCD, PC, any CI-based method
- Visual: table showing CI accuracy, false collider count, Phase 2 impact per network

### Slide 9 — Finding 4: Head-to-Head vs MosaCD
- LOCALE: open-source Qwen3.5-27B, local inference
- MosaCD: proprietary GPT-4o-mini, API calls
- Results:
  | Network | LOCALE | MosaCD | Winner |
  |---------|--------|--------|--------|
  | Insurance | 88.4% | 87% | LOCALE (+1.4pp) |
  | Alarm | 89.9% | 93% | MosaCD (-3.1pp) |
  | Child | 88.0% | 90% | MosaCD (-2.0pp) |
  | Asia | 93.3% | 93% | LOCALE (+0.3pp) |
  | Hepar2 | 58.8% | 72% | MosaCD (-13.2pp) |
- Score: 2-3. Competitive — not dominant, but with open-source model + 2.4-4x fewer queries
- Hepar2 gap is skeleton (52% coverage), not orientation

### Slide 10 — Finding 5: Query Efficiency
- Ego-graph batching: one query scores all incident edges
- 2.4-4.0x fewer queries across all 6 networks (58-75% savings)
- Cost scales with nodes O(n), not edges O(e)
- At 27B scale, each ego-graph query costs more tokens but produces more information
- Net: competitive accuracy at fraction of the cost
- Visual: paired bar chart — LOCALE vs MosaCD query counts per network

### Slide 11 — Ablation: What Each Phase Contributes
- Full pipeline: +6.6pp over per-edge baseline (85.6% → 92.2%)
- Breakdown:
  - P1 Ego scoring: +1.4pp (ego context helps)
  - P2 NCO constraints: +1.9pp (CI evidence constrains the feasible set)
  - P3 Reconciliation: +0.8pp (dual perspectives beat single)
  - P4 Safety valve: +2.5pp (prevents damage from imperfect constraints)
- Safety valve is essential — not cleanup but core design
- Visual: waterfall chart showing cumulative accuracy gain

### Slide 12 — Negative Results: What Didn't Work (and Why It Matters)
- **Dawid-Skene reconciliation** (from proposal): underperforms majority vote. Why? Only 2 annotators per edge — too sparse for DS's EM to find signal.
- **Meek propagation** (from proposal): complete no-op. Max-2SAT already orients everything. Nothing left for Meek to propagate.
- **Skeleton refinement via LLM**: 0 true positives across 6 networks. LLM too conservative; most missing edges are >2 hops apart (unreachable by local reasoning).
- **Ego at degree 3**: "valley of confusion" — too few CI constraints to guide, enough complexity to confuse. PE wins at d=3.
- These negatives are informative: they tell us where LLMs *can't* help in causal discovery.

---

## PART 4: CONNECTING BACK (3 slides)

### Slide 13 — What MosaCD Got Right, Where LOCALE Adds
- **MosaCD's key insight confirmed**: non-collider-first propagation works because colliders are unreliable. Our NCO finding provides the theoretical grounding — it's not just empirically better, we now know *why*: 100% of CI errors are false colliders.
- **What LOCALE adds**:
  1. NCO as a general principle (method-agnostic, not MosaCD-specific)
  2. F1 decomposition showing the skeleton bottleneck (reframes where the field should focus)
  3. Query efficiency via ego-graph batching (2.4-4x savings)
  4. Open-source viability (27B matches proprietary on most benchmarks)
- **Where both struggle**: skeleton coverage. Neither MosaCD nor LOCALE can overcome a bad skeleton. The PC algorithm is the ceiling.

### Slide 14 — Limitations and Open Questions
- Causal sufficiency assumed (no latent confounders)
- Only Qwen3.5 family tested (no cross-model validation yet)
- PC skeleton is the hard ceiling — future work needs better skeletons
- Calibration (Venn-Abers) not yet validated (needs held-out graph instances)
- n=1000 for most experiments (CI tests degrade on large graphs)

### Slide 15 — Contributions and What's Next
- **Five contributions**:
  1. NCO discovery: ~100% of CI errors are false colliders (method-agnostic)
  2. F1 decomposition: skeleton, not orientation, is the binding constraint
  3. Ego-graph batching: 2.4-4x query savings
  4. Open-source competitiveness: 27B matches GPT-4o-mini
  5. Safety valve: monotonically non-decreasing pipeline design
- **What's next**:
  - Better skeletons: hybrid statistical-LLM skeleton learning
  - Cross-model validation: GPT-4o, Claude, Llama
  - Calibrated selective output (Venn-Abers on edge confidence)
  - Large-scale networks (100+ nodes)
  - NCO as a general preprocessing step for all CI-based methods

---

## Figures Needed

1. Spectrum diagram: per-edge ← ego-graph → whole-graph (Slide 2)
2. Pipeline architecture diagram with ego prompt inset (Slide 4)
3. Actual ego-graph prompt example (Slide 5)
4. Scale trend line chart: accuracy vs model size (Slide 6)
5. F1 decomposition stacked bar chart (Slide 7)
6. NCO table: CI accuracy, false collider count, impact (Slide 8)
7. MosaCD comparison table (Slide 9)
8. Query count paired bar chart (Slide 10)
9. Ablation waterfall chart (Slide 11)

## Data Sources (for script-extraction)

- MosaCD comparison: `results/mve_27b_{network}_10k/`
- Ablation: experiment XN-012
- NCO validation: `results/nco_validation/`
- Query counts: experiment logs
- Scale trend: XN-001 (4B), XN-002 (9B), XN-003 (27B)
- F1 decomposition: XN-016
