# Presenter Memo — LOCALE

Slide-by-slide deep background for the presenter. Each section maps to one slide.

---

## Slide 1: Title

Set the frame: "In our earlier DSC 190 presentation, we presented MosaCD and the Wan et al. survey. We identified a gap — the missing middle between per-edge and whole-graph prompting. This is what happened when we tried to build it."

**Timing**: ~30 seconds

---

## Slide 2: Recap — The Landscape

The audience already saw this. Quick recall, not re-teach. Hit the three paradigms and land on the punchline: MosaCD uses the LLM as a binary classifier with 200 tokens out of a 128K context window.

**What they know**: Wan et al. taxonomy, MosaCD's shuffled queries + non-collider-first propagation, the hallucination problem.

**What's new**: The table framing — context per query vs query count. This sets up ego-graph as the middle ground.

**Timing**: ~1.5 minutes

---

## Slide 3: The Gap

The intellectual origin story. During DSC 190 presentation prep, we noticed the per-edge/whole-graph dichotomy and asked: what about the middle?

**Key phrase**: "The LLM's comparative advantage is contextual reasoning about local causal mechanisms." This is the thesis.

**Anticipated Q**: "Why not just give the LLM more context per edge?" — Per-edge fundamentally cannot capture cross-edge consistency. CI constraints relate *pairs* of edges. You need to see multiple edges to check feasibility.

**Timing**: ~2 minutes

---

## Slide 4: Iterative BFS Expansion

This is the core design slide. The SP mapping table is the conceptual anchor.

**What to emphasize**: The decimation loop. Round 1 queries all nodes blind. Round 2+ queries frontier nodes with established context. Each round commits high-confidence edges, which become hard constraints for the next round. This is Survey Propagation: compute local marginals → decimate most biased → simplify → repeat.

**The SP table**: Walk through each row. Variables = edge orientations. Factors = ego-graph queries (the LLM IS the factor computation). Warnings = vote distributions. Decimation = commit at 70% threshold. Simplify = feed established edges into next round's prompts as facts.

**What changed from proposal**: The original proposal described this but the first implementation was single-pass. The copilot has now built the iterative version (`iterative_bfs.py`), running on Insurance as we speak.

**Anticipated Q**: "How many rounds does it take?" — Depends on the graph. Insurance (27 nodes) should converge in 2-3 rounds. Larger graphs may need more.

**Timing**: ~2.5 minutes

---

## Slide 5: The Ego-Graph Prompt (Round 2+)

This is the concrete example that makes the iterative design tangible. Show a Round 2 prompt for DrivQuality, which has one established edge from Round 1.

**What to emphasize**: The "ESTABLISHED" line. In Round 1, DrivingSkill's ego query oriented DrivingSkill→DrivQuality with 90% confidence. In Round 2, DrivQuality's prompt takes this as a given fact. The LLM no longer needs to figure out that relationship — it focuses on the remaining 2 edges.

**The key difference from single-pass**: In single-pass, DrivQuality's ego query has no context about DrivingSkill's perspective. In iterative mode, it inherits Round 1's decisions. This is like message passing: DrivingSkill's "message" about their shared edge propagates to DrivQuality's local computation.

**Max-2SAT connection**: Established edges become unary hard constraints. If DrivingSkill→DrivQuality is established, then b[DrivingSkill]=1 is fixed in DrivQuality's Max-2SAT. This reduces the search space from 2^d to 2^(d-k) where k edges are already committed.

**The punchline**: Round 1: one query → 4 edges. Round 2: context-enriched → 2 remaining edges. Established orientations propagate as facts, not suggestions.

**Anticipated Q**: "What if Round 1 commits a wrong edge?" — Confidence decay (0.9^round) and the 70% threshold filter out low-confidence edges. But yes, error propagation is a risk. The safety valve (Phase 4) catches cascading errors.

**Timing**: ~2.5 minutes

---

## Slide 6: Finding 1 — Ego Needs Scale

Critical finding. Ego-graph prompting is a *harder task* than binary classification. 4B: 47% (worse than random on some edges). Crossover at 27B.

**Why it matters**: Ego methods are only viable with capable models. But open-source 27B models now exist. The threshold was crossed in 2025-2026.

**Detail**: Insurance, disguised variable names (prevents memorization), K=5 votes.

**Anticipated Q**: "What about GPT-4o or Claude?" — Not tested yet. Future work. Point: 27B is sufficient.

**Timing**: ~2 minutes

---

## Slide 7: Finding 2 — Skeleton Is the Bottleneck

**The most important diagnostic finding.** The field has been optimizing orientation (MosaCD, CausalFusion). But orientation is at ceiling on skeleton edges. The binding constraint is skeleton coverage.

**Numbers that matter**: Insurance and Asia have 100% orientation accuracy. F1 gap vs MosaCD is entirely skeleton misses.

**Hepar2 cautionary tale**: 52% skeleton coverage. No orientation method can fix that. Hepar2's F1 gap is about skeleton, not orientation.

**Implication**: Future work should focus on better skeletons. This reframes the research agenda.

**Anticipated Q**: "But MosaCD gets 72% on Hepar2?" — Same PC algorithm. Their propagation strategy may compensate differently, but the skeleton is still the ceiling.

**Timing**: ~2.5 minutes

---

## Slide 8: Finding 3 — The NCO Discovery

**Core contribution. Take time here.**

Every incorrect CI constraint is a false collider. Not "most" — all of them. Zero false non-colliders across 6 networks.

**The intuition**: Non-collider = "Z IS in sep set" (positive evidence, directly observed). Collider = "Z is NOT in ANY sep set" (absence of evidence). With finite samples, you fail to find the right separating set → false collider.

**Method-agnostic**: Inherent to CI testing. MosaCD's non-collider-first works *because of this*. We provide the theoretical grounding they didn't have.

**Anticipated Q from Prof. Huang**: "Is this known?" — Collider FPR > non-collider FPR is known informally. MosaCD proved it under a simplified model (Theorem 5.5). What's new: it's 100%, not just higher. Completely dominant.

**Timing**: ~3 minutes

---

## Slide 9: NCO Fix

Simple fix, dramatic impact. NCO never hurts. Hard constraints hurt 3/6 networks. Insurance reaches 100% with NCO.

**Anticipated Q**: "If you drop collider constraints, don't you lose information?" — The information was wrong 100% of the time. Better to let the LLM decide unconstrained than force a wrong constraint.

**Timing**: ~1.5 minutes

---

## Slide 10: Head-to-Head vs MosaCD

Frame as "competitive, not dominant." Score is 2-3. But operating conditions differ dramatically: open-source local vs proprietary API, 2.4-4x fewer queries.

**Don't oversell.** We don't beat MosaCD. We match it on some benchmarks with a cheaper, open-source setup.

**Timing**: ~2 minutes

---

## Slide 11: Query Efficiency

Clearest win. 2.4-4x universally. One ego query produces d edges of information vs 1 for per-edge. As graphs get denser, savings grow.

**Don't linger.** Clean result, minimal explanation needed.

**Timing**: ~1 minute

---

## Slide 12: Ablation

Safety valve is the largest single contributor (+2.5pp). Surprising — the "cleanup" phase matters more than the "core" phases. It detects when constraints hurt and reverts.

**Timing**: ~1.5 minutes

---

## Slide 13: What Didn't Work

Be honest. Four things from the proposal didn't work. This is a strength.

- **Dawid-Skene**: Only 2 annotators per edge, too sparse for EM.
- **Meek**: Max-2SAT already orients everything. Nothing left.
- **Skeleton refinement**: 0 TP across 6 networks. Most missing edges >2 hops apart.
- **Degree 3**: "Valley of confusion." Too few constraints, too much complexity.

**Timing**: ~2.5 minutes

---

## Slide 14: Connecting Back to MosaCD

Connects to DSC 190 presentation. We studied MosaCD deeply, proposed an extension, discovered *why* MosaCD's non-collider-first works. NCO provides the theoretical grounding.

**The reframing**: LOCALE's main contribution isn't "beating MosaCD" — it's diagnostic. F1 decomposition, NCO asymmetry, skeleton bottleneck. Immediately useful to the field.

**Timing**: ~2 minutes

---

## Slide 15: Contributions and What's Next

Land five contributions. First two (NCO, F1 decomposition) are most novel. Then practical contributions (queries, open-source, safety valve).

**Closing tone**: "We set out to test ego-graph prompting. The pipeline works, but the diagnostic findings turned out to be the more interesting contribution."

**Timing**: ~2 minutes

---

## Slide 16: Questions

**Anticipated Q&A:**

- "CausalFusion / CauScientist comparison?" — Different operating point. They edit the whole graph; we orient on a fixed skeleton. Complementary.
- "Latent confounders?" — Causal sufficiency assumed. FCI/PAG extension is future work.
- "NCO to improve MosaCD directly?" — Yes. That's the point. Method-agnostic.
- "Bigger model?" — 27B is the sweet spot for local inference. 70B+ needs multi-GPU.
- "PC alpha sensitivity?" — Default alpha=0.05. Sensitivity analysis planned.

**Total presentation time**: ~28 minutes + Q&A
