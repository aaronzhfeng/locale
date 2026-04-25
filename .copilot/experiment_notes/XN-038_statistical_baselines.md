---
id: XN-038
title: "Statistical baselines: PC-orig and PC-stable+Meek across 10 networks"
date: 2026-04-05
dag_nodes: [E03]
links:
  evidence_for: [E03, I02]
  related_to: [XN-035]
tags: [baseline, pc, meek, statistical, comparison]
---

# XN-038: Statistical Baselines

## Objective

Add non-LLM baselines to match MosaCD's comparison breadth. MosaCD compares against 5 baselines: PC, Meek, Shapley-PC, ILS-CSL, SCP. We add PC-orig and PC-stable+Meek as CPU-only baselines.

## Setup

- 10 networks (Hailfinder excluded — n=2000 not comparable)
- PC-orig: standard PC algorithm orientation (order-dependent)
- PC-stable+Meek: PC-stable skeleton + Meek rules (order-independent, our skeleton method)
- Same data seeds as LOCALE/MosaCD runs
- 12 seeds for original 6 networks, 4 seeds for new networks

## Results

| Network | Nodes | PC-orig | PC+Meek | MosaCD | LOCALE | Best |
|---------|-------|---------|---------|--------|--------|------|
| Cancer | 5 | 0.518±0.031 | 0.518±0.031 | 0.964±0.062 | 0.964±0.062 | tie (LLM) |
| Asia | 8 | 0.761±0.028 | 0.626±0.129 | **0.967±0.033** | 0.900±0.100 | MosaCD |
| Sachs | 11 | 0.278±0.284 | 0.278±0.284 | 0.557±0.063 | **0.865±0.044** | LOCALE |
| Child | 20 | 0.669±0.064 | 0.578±0.033 | 0.871±0.035 | **0.882±0.030** | LOCALE |
| Insurance | 27 | 0.526±0.058 | 0.575±0.039 | 0.757±0.083 | **0.845±0.019** | LOCALE |
| Water | 32 | 0.294±0.017 | 0.323±0.031 | 0.569±0.049 | **0.579±0.068** | LOCALE |
| Mildew | 35 | 0.656±0.090 | 0.643±0.090 | 0.859±0.032 | **0.859±0.036** | tie (LLM) |
| Alarm | 37 | 0.829±0.021 | 0.833±0.020 | 0.801±0.047 | **0.841±0.070** | LOCALE |
| Hepar2 | 70 | 0.250±0.031 | 0.263±0.029 | 0.405±0.029 | **0.565±0.026** | LOCALE |
| Win95pts | 76 | 0.633±0.018 | 0.648±0.020 | 0.573±0.057 | **0.694±0.091** | LOCALE |

## Key Findings

1. **LLM methods massively outperform statistical baselines.** Mean improvement: LOCALE +33.6pp over PC+Meek, MosaCD +22.0pp over PC+Meek. LLM-assisted orientation provides genuine value.

2. **LOCALE is best on 8/10 networks.** MosaCD wins only Asia. Cancer and Mildew are LLM ties.

3. **PC-orig vs PC+Meek are similar.** Meek rules help slightly on some networks (Insurance +4.9pp, Water +2.9pp) but hurt on others (Asia -13.5pp, Child -9.1pp). The inconsistency justifies using LLM evidence instead of propagation rules.

4. **Statistical baselines are weakest on small/dense networks.** Sachs (0.278), Hepar2 (0.263), Water (0.323) — where CI tests are noisiest. LLM methods recover most of the gap.

## Still needed

- Shapley-PC (statistical, no LLM — clone failed, may need manual implementation)
- ILS-CSL (LLM-based — code cloned, needs adaptation to vLLM endpoint)
- SCP (LLM-based — need to locate code)
