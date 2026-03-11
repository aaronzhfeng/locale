---
marp: true
theme: default
paginate: true
size: 16:9
footer: 'LOCALE | DSC 190 | Prof. Biwei Huang'
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Fira+Code:wght@400;500;700&display=swap');

:root {
  --color-background: #0d1117;
  --color-foreground: #c9d1d9;
  --color-heading: #58a6ff;
  --color-accent: #7ee787;
  --color-code-bg: #161b22;
  --color-border: #30363d;
  --font-default: 'Inter', 'Helvetica Neue', sans-serif;
  --font-code: 'Fira Code', 'Consolas', 'Monaco', monospace;
}

section {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-family: var(--font-default);
  font-weight: 400;
  box-sizing: border-box;
  border-left: 4px solid var(--color-accent);
  position: relative;
  line-height: 1.6;
  font-size: 20px;
  padding: 56px;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  color: var(--color-heading);
  margin: 0;
  padding: 0;
  font-family: var(--font-code);
}

h1 {
  font-size: 52px;
  line-height: 1.3;
  text-align: left;
}

h1::before {
  content: '# ';
  color: var(--color-accent);
}

h2 {
  font-size: 38px;
  margin-bottom: 40px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--color-border);
}

h2::before {
  content: '## ';
  color: var(--color-accent);
}

h3 {
  color: var(--color-foreground);
  font-size: 26px;
  margin-top: 32px;
  margin-bottom: 12px;
}

h3::before {
  content: '### ';
  color: var(--color-accent);
}

ul, ol {
  padding-left: 32px;
}

li {
  margin-bottom: 10px;
}

li::marker {
  color: var(--color-accent);
}

pre {
  background-color: var(--color-code-bg);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  font-family: var(--font-code);
  font-size: 16px;
  line-height: 1.5;
}

code {
  background-color: var(--color-code-bg);
  color: var(--color-accent);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: var(--font-code);
  font-size: 0.9em;
}

pre code {
  background-color: transparent;
  padding: 0;
  color: var(--color-foreground);
}

footer {
  font-size: 14px;
  color: #8b949e;
  font-family: var(--font-code);
  position: absolute;
  left: 56px;
  right: 56px;
  bottom: 40px;
  text-align: right;
}

footer::before {
  content: '// ';
  color: var(--color-accent);
}

section.title {
  border-left: 4px solid var(--color-accent);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

section.title h1 {
  font-size: 48px;
  margin-bottom: 10px;
}

section.title h1::before {
  content: '';
}

section.title h3 {
  color: #8b949e;
  font-weight: 400;
}

section.section-break {
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}

section.section-break h2 {
  font-size: 44px;
  text-align: center;
  border-bottom: none;
}

section.section-break h2::before {
  content: '';
}

section.section-break p {
  font-size: 22px;
  color: #8b949e;
  margin-top: 16px;
  font-family: var(--font-code);
}

strong {
  color: var(--color-accent);
  font-weight: 700;
}

em {
  color: #ffa657;
  font-style: normal;
}

a {
  color: var(--color-heading);
}

section::after {
  color: #8b949e;
  background: transparent !important;
  font-family: var(--font-code);
  font-size: 14px;
}

table {
  border-collapse: collapse;
  font-size: 18px;
  margin-top: 8px;
  width: 100%;
}

th {
  background-color: var(--color-code-bg) !important;
  color: var(--color-heading);
  padding: 8px 12px;
  text-align: left;
  border-bottom: 2px solid var(--color-border);
}

td {
  padding: 6px 12px;
  border-bottom: 1px solid var(--color-border);
  color: #8b949e;
  background-color: var(--color-background) !important;
}

tr:nth-child(even) td {
  background-color: var(--color-code-bg) !important;
}

.highlight { color: var(--color-accent); font-weight: 700; }
.dim { color: #484f58; }
.warn { color: #f85149; }
.small { font-size: 20px; color: #8b949e; }

blockquote {
  border-left: 4px solid var(--color-heading);
  padding-left: 16px;
  color: #8b949e;
  font-size: 24px;
}
</style>

<!-- _class: title -->

# LOCALE

## Ego-Graph Orientation for LLM-Assisted Causal Discovery

### Aaron Feng · DSC 190 · Prof. Biwei Huang

<span class="small">March 2026</span>

---

## Recap: The Landscape We Presented

Three paradigms for LLM-assisted causal discovery:

| Paradigm | Example | Context/Query | Queries |
|----------|---------|---------------|---------|
| **Per-edge** | MosaCD, chatPC | ~200 tokens (one edge) | O(E × K) |
| **Ego-graph** | *LOCALE (ours)* | ~500-1000 tokens (neighborhood) | O(N × K) |
| **Whole-graph** | CausalFusion | O(V²) tokens (full DAG) | O(rounds) |

MosaCD: shuffled queries + non-collider-first propagation. Best F1 in 9/10 benchmarks.

But each query uses the LLM as a **binary classifier**.
128K context window. ~200 tokens used.

---

## The Gap We Identified

**Per-edge** (MosaCD): one query = one binary vote. No local consistency.
CI constraints checked *after* the LLM, not *during*.

**Whole-graph** (CausalFusion): entire DAG in context. O(V²) tokens.
LLM does what Meek rules already do perfectly.

**The missing middle**: show the LLM one node's neighborhood.
It scores all incident edges **jointly**, sees CI constraints,
reasons about local mechanism consistency.

> The LLM's comparative advantage is contextual reasoning about
> local causal mechanisms — not binary edge classification,
> not global graph editing.

---

## LOCALE Pipeline

**Phase 0**: PC-stable skeleton + separating sets *(standard, no LLM)*

**Phase 1**: Ego-graph LLM scoring
One query per node, K=10 stochastic votes with shuffled neighbor order.
LLM sees: node + all neighbors + CI constraints + cross-neighbor evidence.

**Phase 2**: CI-derived constraints via Max-2SAT (NCO variant)
Non-collider constraints are hard. LLM votes are soft.
Exact enumeration over feasible assignments per node.

**Phase 3**: Confidence-weighted dual-endpoint reconciliation
Each edge scored from both endpoints. Higher confidence wins.

**Phase 4**: Safety valve
Compare Phase 2 accuracy to Phase 1 per node. Revert where constraints hurt.
Ensures the pipeline is **monotonically non-decreasing**.

*LLM does local reasoning. Algorithm handles global consistency.*

---

## The Ego-Graph Prompt

```
CENTER NODE: DrivingSkill — "Driver's overall skill level"

NEIGHBORS (4 variables):
  1. Age — "Driver's age group"
  2. SeniorTrain — "Senior training completed"
  3. DrivQuality — "Quality of driving"
  4. DrivHist — "Driving violation history"

STATISTICAL CONSTRAINTS:
  R1. Age ⊥ DrivQuality | {DrivingSkill} — NON-COLLIDER.
      Age and DrivQuality must NOT both point into DrivingSkill.
  R2. Age ⊥ DrivHist | {DrivingSkill} — NON-COLLIDER.
  R3. SeniorTrain ⊥ DrivQuality | {DrivingSkill} — NON-COLLIDER.

TASK: Orient each edge. Use constraints, then domain knowledge.
```

**One query → 4 edge orientations.** MosaCD: 4 × 10 = 40 queries.
The LLM sees constraints and domain knowledge **simultaneously** (phi × psi).

---

## Finding 1: Ego Needs Scale

Ego-graph prompting requires sufficient model capacity.
Same edges, same skeleton, same CI evidence — only model size changes.

| Model | Per-Edge | Ego-Graph | Delta |
|-------|----------|-----------|-------|
| Qwen3.5-**4B** | 90.5% | 47.4% | **-43.2pp** |
| Qwen3.5-**9B** | 90.5% | 80.0% | -10.5pp |
| Qwen3.5-**27B** | 93.7% | 94.7% | **+1.1pp** |

Joint neighborhood reasoning is a harder task than binary classification.
Small models fail catastrophically. At **27B**, ego matches or wins.

<span class="small">Insurance network, disguised variable names, K=5 votes. XN-001/002/003.</span>

---

## Finding 2: Skeleton Is the Bottleneck

Decomposing directed-edge F1: **skeleton coverage × orientation accuracy**

| Network | Skeleton Coverage | Orientation Acc. | Directed F1 | MosaCD F1 |
|---------|-------------------|------------------|-------------|-----------|
| Insurance | 83% | **100%** | 88.4% | 87% |
| Asia | 88% | **100%** | 93.3% | 93% |
| Alarm | 88% | 89.9% | 89.9% | 93% |
| Child | 88% | 88.0% | 88.0% | 90% |
| Hepar2 | **52%** | 80.6% | 58.8% | 72% |

On edges the skeleton gets right, orientation is **at ceiling**.
The F1 gap vs MosaCD is skeleton coverage, not orientation quality.

Hepar2: 52% skeleton coverage. No orientation method can fix that.

---

## Finding 3: The NCO Discovery

Phase 2 (hard CI constraints) **hurt** on 3/6 networks. Why?

**~98% of incorrect CI-derived orientation facts are false colliders.**

| Network | CI Accuracy | False Colliders | False Non-Colliders | P2 Impact |
|---------|-------------|-----------------|---------------------|-----------|
| Insurance | 92.4% | 7 | **0** | +4.2pp |
| Alarm | 90.4% | 7 | **0** | +1.3pp |
| Child | 78.9% | 12 | **0** | +6.2pp |
| Sachs | 95.5% | 1 | **0** | -5.9pp |
| Asia | 90.0% | 1 | **0** | -16.7pp |
| Hepar2 | 65.1% | 52 | **0** | -9.9pp |

Non-collider = positive evidence (Z IS in sep set). Always reliable.
Collider = absence of evidence (Z NOT FOUND). Fails with finite samples.

---

## NCO: The Fix and Its Generality

**Fix**: use only non-collider constraints. 100% reliable.

| Network | Ego Only | + Hard Constraints | + NCO Only |
|---------|----------|--------------------|-----------:|
| Insurance | 93.1% | 97.2% | **98.6%** |
| Alarm | 88.3% | 89.6% | 89.6% |
| Sachs | 70.6% | 64.7% | **70.6%** |
| Asia | 100% | 83.3% | **100%** |
| Hepar2 | 75.7% | 65.8% | **79.3%** |
| **Aggregate** | 83.7% | 81.1% | **86.7%** |

NCO never hurts. Hard constraints hurt 3/6 networks.

This is **method-agnostic**: applies to MosaCD, PC, any CI-based method.
Validated at n=1k through n=10k. 100% false-collider rate at n ≥ 5000.

---

## Finding 4: Head-to-Head vs MosaCD (Same Model)

Fair comparison: **same Qwen3.5-27B, same skeleton, same data**.
MosaCD reimplemented with identical LLM backend.

| Network | LOCALE | MosaCD | Result |
|---------|--------|--------|--------|
| Insurance | **86.3%** | 86.3% | Tie (LOCALE **46% fewer queries**) |
| Alarm | **89.9%** | 80.9% | **LOCALE +9.0pp** |
| Child | **88.0%** | 88.0% | Tie (LOCALE **70% fewer queries**) |
| Asia | **93.3%** | 93.3% | Tie (LOCALE **29% fewer queries**) |
| Sachs | **76.5%** | 58.8% | **LOCALE +17.7pp** |

**Score: 2 wins, 3 ties, 0 losses.** Always ~50% fewer queries.
On ties, LOCALE matches MosaCD with substantially fewer LLM calls.

---

## Finding 5: Query Efficiency

Ego-graph batching: one query scores **all** incident edges.

Per-edge: one query per edge × K votes = O(E × K) queries
Ego-graph: one query per node × K votes = O(N × K) queries

Across 6 networks: **2.4-4.0x fewer queries** (58-75% savings)

Cost scales with **nodes**, not edges.
As graphs get denser, the savings grow.

At 27B, each ego query costs more tokens but produces
**d edges of information** instead of 1.
Net result: competitive accuracy at a fraction of the cost.

<span class="small">Sachs (11 nodes, 17 edges): 2.4x. Insurance (27 nodes, 52 edges): 3.8x.</span>

---

## Ablation: What Each Phase Contributes

Full pipeline: **+6.6pp** over per-edge baseline (85.6% → 92.2%)

| Phase | What It Does | Cumulative | Delta |
|-------|-------------|------------|-------|
| PE baseline | Per-edge LLM votes | 85.6% | — |
| + P1 Ego scoring | Joint neighborhood context | 87.0% | +1.4pp |
| + P2 NCO constraints | CI-feasible assignments | 88.8% | +1.9pp |
| + P3 Reconciliation | Dual-endpoint agreement | 89.7% | +0.8pp |
| + P4 Safety valve | Damage detection + revert | **92.2%** | **+2.5pp** |

**Safety valve is the largest single contributor.**
Not cleanup — core design. Detects when constraints hurt and reverts.

<span class="small">4 networks, 215 edges, orientation accuracy on skeleton edges. XN-012.</span>

---

## What Didn't Work

**Dawid-Skene reconciliation** (proposed)
Underperforms majority vote. Only 2 annotators per edge — too sparse for EM.

**Meek propagation** (proposed)
Complete no-op. Max-2SAT already orients everything. Nothing left for Meek.

**Skeleton refinement via LLM**
0 true positives across 6 networks. Most missing edges are >2 hops apart.
Hepar2 worst: 9 false positives, 0 true positives. Definitively vetoed.

**Ego at degree 3** ("valley of confusion")
Too few CI constraints to guide, enough complexity to confuse.
Per-edge wins at d=3. Ego wins at d≥4.

**Iterative BFS expansion** (in progress)
SP-style decimation: established edges feed as context into later rounds.
Initial result: single-pass K=10 (F1=0.863) > multi-round K=5x2 (F1=0.800).
Root cause: error amplification from early decimation. More votes > more context.
Still exploring: matched budgets, different thresholds, incremental seeds.

These negatives tell us **where LLMs can't help** in causal discovery.

---

## What MosaCD Got Right, Where LOCALE Adds

**MosaCD's insight confirmed**: non-collider-first propagation works.
Our NCO finding provides the **theoretical grounding** — it's not just
empirically better. We now know *why*: ~98% of CI errors are false colliders.

**What LOCALE adds:**

1. **NCO as a general principle** — method-agnostic, not MosaCD-specific
2. **F1 decomposition** — skeleton is the binding constraint (reframes the field)
3. **Same accuracy, half the queries** — 2 wins, 3 ties, 0 losses vs MosaCD (same model)
4. **Open-source viability** — 27B matches proprietary on most benchmarks
5. **Safety valve** — monotonically non-decreasing pipeline

**Where both struggle**: skeleton coverage.
Neither can overcome a bad PC skeleton. That's the real frontier.

---

## Limitations

- **Causal sufficiency** assumed — no latent confounders
- **Single model family** — only Qwen3.5 tested (no GPT-4o, Claude, Llama)
- **PC skeleton ceiling** — LOCALE cannot recover edges PC misses
- **n=1000** for most experiments — CI tests degrade on large graphs
- **Calibration** (Venn-Abers) not yet validated — needs held-out graph instances
- **Iterative expansion** initial result negative — still exploring matched-budget variants

---

## Contributions and What's Next

**Five contributions:**
1. **NCO discovery**: ~98% of CI errors are false colliders *(method-agnostic)*
2. **F1 decomposition**: skeleton, not orientation, is the binding constraint
3. **Same accuracy, half the queries**: 2 wins, 3 ties vs MosaCD on same model
4. **Open-source parity**: 27B matches proprietary models
5. **Safety valve**: monotonically non-decreasing pipeline design

**What's next:**
- Better skeletons: hybrid statistical-LLM skeleton learning (the real bottleneck)
- Cross-model validation: GPT-4o, Claude, Llama
- Calibrated selective output (Venn-Abers edge confidence)
- NCO as preprocessing for all CI-based methods

---

<!-- _class: title -->

# Thank You

### Questions?

<span class="small">Code and experiments: projects/locale/ · Qwen3.5-27B on RunPod vLLM</span>
