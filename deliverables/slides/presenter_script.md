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

## Slide 4: LOCALE Pipeline [4:00 — 6:00]

"The pipeline has four phases after the skeleton."

"Phase 1 is where the ego-graph queries happen. For each node, we construct a prompt showing all its neighbors, the CI evidence, the cross-neighbor relationships. The LLM returns structured JSON. We run K=10 stochastic passes with shuffled neighbor order — same debiasing principle as MosaCD, but at the ego level."

"Phase 2 is where the math happens. We compile CI-derived constraints into a Max-2SAT problem. Non-collider constraints become hard clauses. LLM votes become the soft objective. We enumerate over feasible assignments and pick the best one. I'll explain why we only use non-collider constraints in a few slides."

"Phase 3 reconciles the two perspectives on each edge — every edge is scored from both endpoints. Higher confidence wins."

"Phase 4 is the safety valve. It compares Phase 2 to Phase 1 per node. If constraints actually hurt accuracy, it reverts. This ensures the pipeline is monotonically non-decreasing — every phase either helps or does nothing."

"The key principle: the LLM does local reasoning. The algorithm handles global consistency."

---

## Slide 5: The Ego-Graph Prompt [6:00 — 8:30]

"Let me make this concrete. Here's what the LLM actually sees for DrivingSkill in the Insurance network."

*Walk through the prompt:*

"The center node with its description. Four neighbors, each with descriptions. Then the statistical constraints — these are the CI-derived rules."

*Point to the R1/R2/R3 rules:*

"R1 says Age and DrivQuality are conditionally independent given DrivingSkill — that makes DrivingSkill a non-collider for that triple. So Age and DrivQuality can't both be parents of DrivingSkill. The LLM sees this constraint *while* it reasons, not after."

"This is the key difference from MosaCD. MosaCD asks 'Is it Age arrow DrivingSkill, or DrivingSkill arrow Age?' One edge, binary choice, 200 tokens. We show all four neighbors, all the CI relationships, and ask for all four orientations in one query."

"One query, four edge orientations. MosaCD needs 40 queries for the same four edges."

*Pause. Let the 40x difference land.*

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

"Now the comparison that matters most. We reimplemented MosaCD's per-edge approach using the exact same LLM — Qwen3.5-27B — the same skeleton, the same data. This is a controlled, fair comparison. The only difference is the prompting strategy."

*Go through the table:*

"On Insurance, Asia, and Child — ties. Same F1. But LOCALE uses 30 to 70 percent fewer queries to get there."

"On Alarm — LOCALE wins by 9 points. On Sachs — LOCALE wins by nearly 18 points. These are the networks where MosaCD's per-edge approach struggles. Alarm has complex local structure where cross-edge consistency matters. Sachs is a protein signaling network — less familiar to the LLM, so the ego-graph context helps more."

"Two wins, three ties, zero losses. And on every single network, LOCALE uses roughly half the queries."

*Let that land. This is the headline result.*

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

"Ego at degree 3 — there's a 'valley of confusion' where per-edge is actually better. Too few CI constraints to guide, but enough complexity to confuse."

"And finally, the iterative BFS expansion — the Survey Propagation-style design from our original proposal. We built it and tested it. Initial result: single-pass with K=10 votes per node beats multi-round K=5 times 2. The root cause is error amplification — if you commit a wrong edge in Round 1, it becomes a hard constraint that corrupts Round 2. More votes per node matters more than context from neighbors. We're still exploring different configurations, but for now the simple approach wins."

*Frame negatives as informative, not failures. The iterative BFS negative is especially interesting — it tells us something about the reliability-vs-context tradeoff.*

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

"Three: same accuracy as MosaCD with half the queries. Two wins, three ties, zero losses on same-model comparison."

"Four: open-source competitiveness. 27B running locally matches proprietary API models."

"Five: safety valve design for a pipeline that never hurts."

"What's next: better skeletons — that's the real bottleneck the F1 decomposition revealed. Cross-model validation with GPT-4o and Claude. Calibrated selective output. And continued exploration of iterative expansion with matched budgets."

*Closing:*

"We set out to test whether ego-graph prompting could improve the accuracy-cost tradeoff. It does — same accuracy, half the queries. But the diagnostic findings along the way — the NCO discovery, the skeleton bottleneck, the degree-3 valley — turned out to be the more interesting contribution."

---

## Slide 16: Questions [28:30+]

*Be ready for:*

- "How does this compare to CausalFusion?" — Different operating point. They edit the whole graph. Complementary, not competitive.
- "Latent confounders?" — Causal sufficiency assumed. FCI extension is future work.
- "Could NCO improve MosaCD?" — Yes. That's part of the point.
- "Why not a bigger model?" — 27B is the sweet spot for single-GPU local inference.
- "PC alpha sensitivity?" — Default 0.05, sensitivity analysis planned.

*If asked about the iterative expansion: "We built and tested it. Initial results favor single-pass — more votes per node beats fewer votes with inter-round context. Error amplification from early decimation is the issue. We're still exploring matched-budget variants and incremental seeding, but for now brute-force reliability wins over elegant message passing."*
