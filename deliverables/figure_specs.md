# LOCALE Paper — Conceptual Figure Specifications

*For image generation model. These figures are conceptual/architectural — no specific data needed.*

Paper: "LOCALE: Ego-Graph Orientation with CI Constraints for LLM-Assisted Causal Discovery"
Venue: CoLM 2026 (double-blind, 9-page main text)
Style: Academic, clean, grayscale-safe (colors OK but must be distinguishable in B&W)

---

## Figure 1: LOCALE Pipeline Overview (Section 3, Method)

**Purpose:** Show the full 4-phase pipeline at a glance. This is the most important figure — readers will look at this before reading the text.

**Content:** A left-to-right flow diagram with 4 phases:

1. **Input** (left side): An undirected skeleton graph (5-7 nodes, edges shown as plain lines). Label: "PC-stable skeleton + separating sets". Show a small example graph with nodes A, B, C, D, E connected by undirected edges.

2. **Phase 1: Ego-Graph Prompting** — Show one node (e.g., node C) highlighted as the "center." Draw a dashed circle around C and its neighbors (the ego-graph). An arrow goes from this ego-graph into an LLM icon (a box labeled "LLM" or a brain icon). Below the LLM box, show "K=10 queries" and output arrows showing directed edges (e.g., A->C, C->D) with confidence scores. Label: "Score all incident edges jointly."

3. **Phase 2: NCO Max-2SAT** — Show CI constraints being applied. Key visual: a constraint box with a red X through "Collider constraints" and a green checkmark on "Non-collider constraints." Below, show a Max-2SAT solver icon producing refined orientations. Label: "Discard 97.9% false collider constraints."

4. **Phase 3-4: Reconciliation + Safety Valve** — Show two ego-graphs (centered at u and v) with their respective orientation votes being combined via weighted voting. A filter/gate icon represents the safety valve. Output: the final directed graph with all edges oriented.

**Style:** Clean academic diagram. Use light blue/gray shading for ego-graph regions. Arrows between phases. Each phase in a rounded rectangle with a number label. The overall flow is left-to-right or top-to-bottom. Approximately 2-column width (full page width in the paper).

**Dimensions:** Width ~6.5 inches, height ~2.5 inches (landscape, fitting full column width).

---

## Figure 2: Ego-Graph vs Per-Edge Prompting (Section 3.1 or Section 1, Introduction)

**Purpose:** Visually contrast LOCALE's ego-graph prompting with MosaCD's per-edge prompting. Show why ego-graph is more context-efficient.

**Content:** Side-by-side comparison on the SAME small graph (6-7 nodes):

**Left panel — "Per-Edge (MosaCD)":**
- Show the same graph with ONE edge highlighted (e.g., A--B).
- The prompt box shows only: "Is A->B or B->A?" with minimal context.
- Label: "1 edge per query, 10 queries/edge"
- Show that for a node with degree 5, this requires 5 separate queries, each seeing only 1 edge.
- Total queries annotation: "410 queries (Insurance)"

**Right panel — "Ego-Graph (LOCALE)":**
- Show the same graph with a CENTER NODE highlighted (e.g., node C with degree 4).
- A shaded region covers C and all its neighbors, showing 4 edges simultaneously.
- The prompt box shows: "Orient ALL edges around C" with neighborhood context visible (neighbor-neighbor adjacencies, CI facts).
- Label: "All edges per query, 10 queries/node"
- Total queries annotation: "110 queries (Insurance)"
- A "58-75% fewer queries" callout.

**Key visual contrast:** Per-edge sees a single edge in isolation. Ego-graph sees the full local neighborhood -- more context, fewer queries.

**Style:** Two panels side by side with a vertical divider or "vs" label. Use the same graph in both panels so the comparison is direct. Highlight the queried elements (edge or ego-graph region) with color/shading. The prompt boxes can be stylized as chat bubbles or code blocks.

**Dimensions:** Width ~6.5 inches, height ~3 inches.

---

## Notes for Image Generation

- **Color palette:** Use a consistent 2-color scheme throughout: blue/teal for LOCALE, orange/coral for MosaCD. This should be consistent across all figures.
- **Font:** Sans-serif for figure labels, matching the paper's body font size (~8-9pt for labels, ~7pt for annotations).
- **Export format:** Vector PDF or high-resolution PNG (300+ DPI).
- **Accessibility:** All figures must be interpretable in grayscale. Use patterns (hatching, dashing) in addition to color where needed.
- **LaTeX integration:** Figures will be included via `\includegraphics` in a `\begin{figure}` environment. Width should be specified in inches or as `\columnwidth` / `\textwidth`.
