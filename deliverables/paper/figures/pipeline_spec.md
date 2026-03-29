# LOCALE Pipeline Architecture — Figure Generation Spec

## Layout
Horizontal left-to-right flow diagram with 5 stages (Phase 0-4). Clean, academic style suitable for a NeurIPS-format paper. White background, no gradients. Use a muted color palette (light blues, grays, one accent color for highlights).

## Stages (left to right)

### Phase 0: Skeleton (leftmost)
- **Input**: Box labeled "Observational Data (X)" with a small table icon
- **Process**: Rounded rectangle labeled "PC-stable (α=0.05)"
- **Output**: Small undirected graph icon (5-6 nodes with undirected edges)
- **Label below**: "Skeleton Ĝ + Separating Sets"
- Arrow flows right to Phase 1

### Phase 1: Ego-Graph Scoring
- **Visual**: Show a zoomed-in ego graph — one center node (colored, e.g., blue) connected to 4 neighbors (gray), with edges among neighbors shown as dashed lines. Small text annotations show CI facts.
- **Process**: Rectangle labeled "LLM (Qwen 27B)" with "K=10 shuffled votes" below
- **Output**: Arrow labels on edges showing "→" or "←" with small confidence numbers
- **Key detail**: Show that ONE query covers ALL edges around the center node (fan-out visual)
- Arrow flows right to Phase 2

### Phase 2: NCO Constraint Compilation
- **Visual**: Split into two parts:
  - Top: Small diagram showing an unshielded triple (A—B—C) with "w ∈ Sep" → "non-collider ✓" (green check)
  - Bottom: Same triple with "w ∉ Sep" → "collider ✗" (red X, crossed out/faded)
- **Process**: Rectangle labeled "Weighted Max-2SAT"
- **Annotation**: "NCO: keep only non-collider constraints (97.9% of errors are false colliders)"
- Arrow flows right to Phase 3

### Phase 3: Reconciliation
- **Visual**: Show edge {u,v} receiving votes from two ego graphs (one centered at u, one at v). Two small fan icons converging on the edge.
- **Process**: Rectangle labeled "Confidence-weighted majority vote"
- **Output**: Edge with final direction arrow and confidence score
- Arrow flows right to Phase 4

### Phase 4: Safety Valve (rightmost)
- **Visual**: A gate/filter icon (like a valve or checkpoint)
- **Logic**: "Accept iff F1 ≥ Phase 1 F1"
- **Output**: Final oriented graph — same 5-6 node graph from Phase 0 but now with directed arrows
- **Label below**: "Selectively Oriented Graph"

## Style Notes
- Use consistent node sizes (~8mm circles)
- Phase labels (P0, P1, P2, P3, P4) in small rounded badges above each stage
- Connecting arrows between phases should be thick (1.5pt), dark gray
- Internal arrows within a phase should be thinner (0.75pt)
- Font: sans-serif, ~8pt for labels, ~6pt for annotations
- Total width: fill \linewidth (about 5.5 inches)
- Total height: about 2.5 inches (keep compact)
- Color coding:
  - Phase boxes: light blue fill (#E8F0FE), dark blue border (#1A73E8)
  - NCO highlight: green for non-collider (#34A853), red for collider (#EA4335)
  - Center node in ego graph: accent blue (#1A73E8)
  - Neighbor nodes: light gray (#E0E0E0)

## Key Message
The figure should visually communicate:
1. The pipeline flows left-to-right through 5 stages
2. Phase 1's ego-graph covers MULTIPLE edges per query (vs per-edge methods)
3. Phase 2 filters out unreliable collider constraints (the "crossed out" visual)
4. Phase 4 is a safety check, not a processing step

## Output Format
- PDF or SVG, width 5.5in, height ~2.5in
- Save as `pipeline.pdf` in the same directory
