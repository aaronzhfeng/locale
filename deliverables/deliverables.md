# Deliverables Status — LOCALE

## Slides

| Item | Status | Path |
|------|--------|------|
| Outline | Done | `slides/outline.md` |
| Slides (Marp) | Done (2 placeholder slides) | `slides/slides.md` |
| PDF | Compiled | `slides/slides.pdf` |
| PPTX | Compiled (59K, 17 slides) | `slides/slides.pptx` |
| Presenter memo | Done | `slides/presenter_memo.md` |
| Presenter script | Done | `slides/presenter_script.md` |
| make_pptx.py | Done (adapted from DSC 190) | `slides/make_pptx.py` |

### Placeholders to update
- **Slide 4** (Pipeline Overview): update once iterative BFS/SP-style expansion is built by copilot
- **Slide 5** (Ego-Graph Prompt): update with iterative expansion context ("ESTABLISHED: ...")

## Report
Not started.

## Paper (NeurIPS 2026 format, 6-page body)

| Item | Status | Path |
|------|--------|------|
| main.tex | Draft complete (6pp body + appendix) | `paper/main.tex` |
| neurips_2026.sty | Copied from template | `paper/neurips_2026.sty` |
| checklist.tex | Template (all TODOs) | `paper/checklist.tex` |
| references.bib | Stub placeholders only | `paper/references.bib` |
| citations_to_find.txt | 18 papers listed | `paper/citations_to_find.txt` |
| figures/ | Empty (scripts needed) | `paper/figures/` |
| PDF | Not compiled (no pdflatex on this machine) | — |

### Blocking items
- **Bibliography**: all 18 bib entries are PLACEHOLDER stubs. Human must verify on Google Scholar and replace. Then run `check_bib_hallucinations.py --strict` from brainstorm-00-core.
- **Compilation**: needs `pdflatex` + `bibtex` installed. Sequence: `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
- **Checklist**: NeurIPS checklist (checklist.tex) is all TODOs — must be filled before submission.
- **Figures**: no figures yet. Pipeline diagram, NCO bar chart, and context sensitivity plot would strengthen the paper.

### Data provenance
All numbers in tables trace to experiment results:
- Table 1 (12-seed F1): XN-030 experiment note
- Table 2 (NCO validation): XN-022 experiment note
- Table 3 (phase ablation): generate_paper_tables.py + phase4_results_nco.json files
- Appendix tables: XN-029 (context), XN-022 (per-network NCO), generate_paper_tables.py (queries)
