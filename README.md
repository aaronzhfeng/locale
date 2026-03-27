# LOCALE

**Local Oracle for Causal Alignment via Learnable Ego-graphs**

LLM-assisted causal edge orientation using ego-graph prompting, non-collider-only (NCO) constraints, and Max-2SAT optimization. Competes with MosaCD on standard Bayesian network benchmarks using an open-source 27B model.

## Status

Phase: DO (pending THINK transition). 12-seed fair comparison complete (XN-030). See `docs/project/hub.md` for the full evidence map.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install 'pgmpy<1.0.0' networkx openai numpy scipy
```

Requires a vLLM endpoint serving `Qwen/Qwen3.5-27B-FP8` with `max_model_len>=4096`. Set the endpoint URL in `experiments/mve_insurance.py:BASE_URL`.

## Project Structure

```
locale/
├── docs/
│   ├── project/           # Research tracking (hub, DAG, log, notes)
│   │   ├── hub.md         # START HERE — evidence map, state of knowledge
│   │   ├── checkpoint.md  # Working-state snapshot
│   │   ├── method_tree.jsonl  # Method evolution DAG
│   │   ├── research_log.md   # Chronological reasoning diary
│   │   ├── experiment_notes/  # XN-001 through XN-030
│   │   ├── literature_notes/  # LN-001 through LN-009
│   │   └── decisions/         # D-xxx decision memos
│   └── proposal/          # Brainstorm proposal + tracker
├── experiments/           # All experiment scripts
│   ├── mve_insurance.py   # Core LOCALE pipeline (Phase 1-3)
│   ├── mosacd_baseline.py # MosaCD re-implementation
│   ├── run_multiseed.py   # Multi-seed LOCALE runner
│   ├── run_multiseed_mosacd.py  # Multi-seed MosaCD runner
│   ├── skeleton_analysis.py     # PC alpha/coverage analysis
│   ├── nco_validation.py        # NCO false-collider validation
│   └── results/           # Experiment artifacts (JSON)
├── deliverables/          # Paper drafts, slides
└── .venv/                 # Python virtual environment
```

## Key Results (12-seed, same model, 4096 context)

| Network | LOCALE F1 | MosaCD F1 | Delta | p (Holm) |
|---------|-----------|-----------|-------|----------|
| Insurance | 0.848±0.014 | 0.757±0.087 | +9.1pp | **0.008** |
| Sachs | 0.861±0.040 | 0.557±0.067 | +30.4pp | **<0.0001** |
| Alarm | 0.842±0.066 | 0.801±0.049 | +4.0pp | 0.086 |
| Child | 0.898±0.021 | 0.871±0.037 | +2.7pp | 0.059 |
| Asia | 0.824±0.054 | 0.952±0.031 | -12.7pp | **<0.0001** |

2 significant wins, 2 directional wins, 1 significant loss (Asia — fixable via alpha=0.10 skeleton).

## Key Findings

1. **NCO (XN-022)**: 97.9% of PC CI errors are false colliders. Dropping collider constraints universally improves orientation.
2. **Context efficiency (XN-029)**: MosaCD breaks at 2048-token context; LOCALE is unaffected. Ego-graph prompts are 2-3x more compact.
3. **Stability**: LOCALE has 6x lower F1 variance than MosaCD (Insurance std 0.014 vs 0.087).
4. **F1 decomposition (XN-016)**: Skeleton coverage is the binding constraint, not orientation quality.

## Running Experiments

```bash
source .venv/bin/activate

# Single network, single seed
python experiments/mve_insurance.py --network insurance --n-samples 10000 \
  --k-passes 10 --debiased --all-nodes --no-think --seed 0 \
  --output-dir experiments/results/mve_27b_insurance_10k_k10_debiased_s0

# Multi-seed LOCALE (skips existing results)
python experiments/run_multiseed.py --seeds 0 1 2 3 4 5 6 7 8 9 10 42 \
  --networks insurance alarm sachs child asia

# Multi-seed MosaCD
python experiments/run_multiseed_mosacd.py --seeds 0 1 2 3 4 5 6 7 8 9 10 42 \
  --networks insurance alarm sachs child asia --include-seed42

# NCO validation (CPU-only, no LLM)
python experiments/nco_validation.py --networks insurance alarm sachs child asia hepar2

# Skeleton analysis (CPU-only)
python experiments/skeleton_analysis.py --mode full
```

## HF Storage

Experiment results may be stored on HuggingFace Storage Buckets. If `experiments/results/` is populated on disk, the data was restored from HF — do not regenerate.
