---
id: XN-006
title: "Blocker: saved Alarm enriched artifact does not match the claimed run"
date: 2026-03-10
dag_nodes: [I02, I03]
links:
  - target: XN-005
    type: related_to
tags: ["blocker", "audit"]
---

# XN-006: Blocker — Saved Alarm enriched artifact does not validate the claimed Alarm run

## Why this blocks interpretation

- `experiments/results/mve_27b_enriched_alarm/mve_results.json` is byte-identical to `experiments/results/mve/mve_results.json`.
- The saved metadata names the old 4B Insurance setup (`Qwen3.5-4B`, Insurance test nodes, 17 test edges), not the claimed Alarm 27B enriched run.
- `per_node`, `raw_results_a`, and `raw_results_b` all contain Insurance nodes and edge rows rather than Alarm nodes.

## Implication

The Alarm half of `XN-005` is not currently auditable from disk. The written claim says `Ego 80.0% > Vanilla PE 77.0% > Enriched PE 70.0%`, but the only saved artifact in the Alarm enriched directory is an unrelated Insurance artifact.

## Likely cause

`experiments/mve_insurance.py` computes `results_c` when `--enriched` is active, but its save path still writes only the standard A/B schema. That leaves condition identity under-specified, and it appears a stale or copied file was placed in the Alarm enriched result directory.

## Unblock

1. Save the actual Alarm 27B enriched artifact with correct network metadata and Condition C outputs or summaries.
2. Make the JSON fail loudly if `--enriched` runs but Condition C is not serialized.
3. Re-check whether Alarm still supports the written `Ego > Vanilla > Enriched` ordering once the correct file exists.
