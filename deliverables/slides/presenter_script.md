# Presenter Script — LOCALE

Per-slide speaking notes with wording suggestions and delivery tips.

---

## Slide 1: Title [0:00 — 0:30]

"Last time, we presented MosaCD and the Wan et al. survey — the landscape of LLM-assisted causal discovery. During that deep dive, we identified a gap. Today I'll show what happened when we tried to fill it."

*Don't read the slide. Move quickly.*

---

## Slide 2: Recap [0:30 — 2:00]

"Quick reminder of where we left off. There are three paradigms for using LLMs in causal discovery."

*Point to the table rows as you go:*

"Per-edge methods like MosaCD — they ask the LLM one edge at a time. 'Is it X causes Y, or Y causes X?' About 200 tokens per query, and you need 10 queries per edge for reliability."

"At the other end, whole-graph methods like CausalFusion — they put the entire DAG in the LLM's context. This works, but context grows quadratically with the number of variables."

"MosaCD gets the best results — 9 out of 10 benchmarks. But think about what's happening: the model has a 128K context window, and we're giving it 200 tokens. That's 0.15% utilization."

*Pause. Let that sink in.*

---

## Slide 3: The Gap [2:00 — 4:00]

"So here's what we noticed. Per-edge methods treat the LLM as a binary classifier. Each query is independent — the model can't check if its answers are locally consistent. MosaCD checks CI constraints after the LLM answers, not during."

"Whole-graph methods go the other extreme — the LLM sees everything and tries to do what Meek rules already do perfectly."

"The missing middle is the ego-graph. Show the LLM one node's neighborhood. All its neighbors, the CI relationships between them, and ask it to orient all incident edges jointly. The context is bounded — O(d) tokens, where d is the degree. The cost is O(n) queries instead of O(e times K)."

"This is what we built. We call it LOCALE."

*This is the thesis slide. Make sure they get it before moving on.*

---

## Slide 4: Iterative BFS Expansion [4:00 — 6:30]

"LOCALE works as an iterative expansion loop — the same pattern as Survey Propagation for SAT solving."

*Point to the bullet sequence:*

"Round 1: we query all eligible nodes with ego-graph prompts. Each node sees its neighborhood, the CI constraints, and the LLM votes on all incident edges. We solve a Max-2SAT per node — CI constraints are hard, LLM votes are soft. Then we decimate: edges where the majority vote exceeds 70% get committed."

"Round 2 and beyond: we query frontier nodes — nodes adjacent to committed edges that haven't been queried yet. Here's the key: their prompts now include the established orientations from Round 1 as given facts. The Max-2SAT solver adds these as hard unary constraints. Then we decimate again. Repeat until convergence."

*Point to the SP mapping table:*

"This maps exactly to Survey Propagation. Variables are edge orientations. Factors are ego-graph queries — the LLM is literally computing the factor. Warnings are the vote distributions. Decimation commits the most confident edges. And simplification is feeding established context into the next round."

"The LLM does local reasoning. The algorithm propagates decisions globally."

---

## Slide 5: The Ego-Graph Prompt — Round 2 [6:30 — 9:00]

"Let me make this concrete with a Round 2 example."

*Walk through the prompt:*

"This is DrivQuality in the Insurance network. It has three neighbors: DrivingSkill, RiskAversion, and Accident."

*Point to the ESTABLISHED line:*

"In Round 1, DrivingSkill's ego query established that DrivingSkill points to DrivQuality — with 90% confidence. Now in Round 2, DrivQuality's prompt treats this as a fact. See the line: 'ESTABLISHED, round 1, confidence 90%, DrivingSkill arrow DrivQuality.' The LLM doesn't need to re-derive this. It's given."

"The statistical constraints then tell the LLM: DrivingSkill and Accident are separated by DrivQuality, so they can't both be parents. Given that DrivingSkill is already established as a parent, this constrains Accident's direction."

*Point to the edges to orient:*

"Two edges to orient, not three. One is already committed. And the context from that committed edge helps the LLM reason about the remaining two."

"This is message passing: DrivingSkill's local computation sends a message about their shared edge, and DrivQuality's computation receives it as a constraint."

*Punchline:*

"Round 1: one query, four edges. Round 2: context-enriched, two remaining edges. Established orientations propagate as facts, not suggestions."

---

## Slide 6: Finding 1 — Scale [8:30 — 10:30]

"First finding: ego-graph prompting is a harder task than binary classification. And small models can't do it."

*Point to each row:*

"At 4B parameters, ego-graph gets 47%. That's near random. The model can't handle joint neighborhood reasoning."

"At 9B, the gap is closing — 80% vs 91%."

"At 27B, crossover. Ego-graph matches or slightly beats per-edge."

"The implication: ego-graph methods only became viable recently, with models like Qwen3.5-27B. A year ago, this wouldn't have worked."

*Quick slide. Don't over-explain.*

---

## Slide 7: Finding 2 — Skeleton Bottleneck [10:30 — 13:00]

"This is the most important diagnostic finding."

*Pause for emphasis.*

"We decomposed directed-edge F1 into two factors: how many true edges the skeleton recovered, and how many of those we oriented correctly."

*Point to Insurance and Asia rows:*

"Insurance: 100% orientation accuracy on the edges the skeleton got right. Asia: 100%. The orientation layer is at ceiling. The F1 gap compared to MosaCD is entirely because the PC algorithm missed some edges."

*Point to Hepar2:*

"Hepar2 is the extreme case. Only 52% of true edges are in the skeleton. No orientation method — ours, MosaCD's, anyone's — can fix that. The skeleton is the hard ceiling."

"This reframes where the field should focus. We've been optimizing orientation layers. The bottleneck is skeleton quality."

*This is a key moment. Let the audience digest.*

---

## Slide 8: Finding 3 — NCO Discovery [13:00 — 16:00]

"When we added CI-derived hard constraints in Phase 2, something unexpected happened. It hurt on three out of six networks."

"So we diagnosed why. And we found something striking."

*Slow down here:*

"Every single incorrect CI-derived orientation fact was a false collider. The PC algorithm said 'this is a collider' when the ground truth said 'non-collider.' Not most of them — all of them. Zero false non-colliders across six networks."

*Point to the zero column:*

"Why? Non-collider evidence is positive: 'Z IS in the separating set.' You directly observe it. Collider evidence is negative: 'Z is NOT IN ANY separating set we found.' That's absence of evidence. With finite samples, you sometimes fail to find the right separating set, so you wrongly conclude collider."

"This is method-agnostic. It's not about LOCALE or MosaCD. It's about CI testing. Any method that uses collider facts from finite-sample CI tests faces this."

*Connect to MosaCD:*

"Remember MosaCD's non-collider-first propagation? This is why it works. They showed empirically that it helps and proved it under a simplified model. We found the mechanism: colliders are unreliable because they're based on absence of evidence."

---

## Slide 9: NCO Fix [16:00 — 17:30]

"The fix is simple: use only non-collider constraints. They're 100% reliable."

*Point to the table:*

"NCO never hurts. Look at the aggregate: ego alone gets 83.7%. Add hard constraints, you drop to 81.1%. Add NCO only, you get 86.7%."

"Insurance reaches 100% with the NCO pipeline. Perfect orientation on every skeleton edge."

"We validated this across sample sizes from 1,000 to 10,000. At 5,000 or more samples, the false-collider rate is 100%. At 1,000, it's 93-99%. The asymmetry is robust."

---

## Slide 10: Head-to-Head [17:30 — 19:30]

"How does LOCALE compare to MosaCD head-to-head?"

"Important context: LOCALE uses Qwen3.5-27B — an open-source model, running locally. MosaCD uses GPT-4o-mini through the API."

*Go through the table:*

"We win two, they win three. Insurance and Asia for us, Alarm, Child, and Hepar2 for them."

"I'm not going to oversell this. We don't beat MosaCD. But we're competitive — with an open-source model and two to four times fewer queries. And the Hepar2 gap is skeleton coverage, not orientation quality."

*Honest framing matters here.*

---

## Slide 11: Query Efficiency [19:30 — 20:30]

"The clearest win: query efficiency. Ego-graph batching gives 2.4 to 4x fewer queries across all six networks."

"The math is straightforward: one ego query scores d edges, where d is the node degree. Per-edge scores one. As graphs get denser, the savings grow."

*Move quickly. This is a clean result.*

---

## Slide 12: Ablation [20:30 — 22:00]

"The ablation shows what each phase contributes. Full pipeline adds 6.6 percentage points over per-edge."

"The surprise: the safety valve is the largest single contributor at 2.5 points. This isn't cleanup — it's core design. It detects when the constraints damaged accuracy and reverts those edges."

"Without the safety valve, the pipeline would be unreliable. With it, it's monotonically non-decreasing — every phase either helps or does nothing, never hurts."

---

## Slide 13: Negative Results [22:00 — 24:30]

"Four things from the original proposal didn't work. I want to be upfront about this."

"Dawid-Skene reconciliation. We proposed treating the two endpoint perspectives as crowdsourcing annotations. But with only two annotators per edge, the EM algorithm can't find meaningful confusion matrices. Simple confidence-weighted majority vote works better."

"Meek propagation. The Max-2SAT solver is too powerful — it orients everything. There are no undirected edges left for Meek to propagate through. This is actually a positive finding: Phase 2 is doing its job."

"Skeleton refinement. We tried having the LLM propose missing edges. Zero true positives across all six networks. Most missing edges connect nodes more than two hops apart — unreachable by local reasoning."

"And ego at degree 3 — there's a 'valley of confusion' where per-edge is better. Too few CI constraints to guide the model, but enough complexity to confuse it."

*Frame negatives as informative, not failures.*

---

## Slide 14: Connecting Back [24:30 — 26:30]

"Let me connect this back to our DSC 190 presentation."

"MosaCD's key insight — non-collider-first propagation — is confirmed by our work. But now we know the mechanism: it works because 100% of CI errors are false colliders. That's not just an empirical observation; it's a structural property of CI testing."

"What LOCALE adds on top: NCO as a general principle that any CI-based method can use. The F1 decomposition showing the skeleton is the real bottleneck. Query efficiency through ego-graph batching. And the demonstration that open-source models are competitive."

"Where both struggle: skeleton coverage. Neither MosaCD nor LOCALE can overcome a bad PC skeleton. That's the real frontier for the field."

---

## Slide 15: Contributions [26:30 — 28:30]

"Five contributions."

*Count on fingers:*

"One: the NCO discovery. Nearly all CI errors are false colliders. Method-agnostic, immediately adoptable."

"Two: F1 decomposition showing the skeleton bottleneck. Reframes where the field should focus."

"Three: ego-graph batching for 2.4 to 4x query savings."

"Four: open-source competitiveness. 27B matches proprietary models on most benchmarks."

"Five: safety valve design for a pipeline that never hurts."

"What's next: we're building the iterative expansion — the full tree-search-style per-node exploration from the original design. Better skeletons. Cross-model validation. And calibrated selective output."

*Closing:*

"We set out to test whether ego-graph prompting could improve the accuracy-cost tradeoff. The pipeline works. But the diagnostic findings along the way — the NCO discovery, the skeleton bottleneck, the degree-3 valley — turned out to be the more interesting contribution."

---

## Slide 16: Questions [28:30+]

*Be ready for:*

- "How does this compare to CausalFusion?" — Different operating point. They edit the whole graph. Complementary, not competitive.
- "Latent confounders?" — Causal sufficiency assumed. FCI extension is future work.
- "Could NCO improve MosaCD?" — Yes. That's part of the point.
- "Why not a bigger model?" — 27B is the sweet spot for single-GPU local inference.
- "PC alpha sensitivity?" — Default 0.05, sensitivity analysis planned.

*If asked about the iterative expansion: "It's in progress. The current results are from the single-pass version. We expect the iterative version to help especially on larger graphs where context from established edges can guide remaining decisions."*
