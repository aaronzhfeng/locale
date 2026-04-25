---
id: XN-033
title: "Disguised robustness multi-seed: domain knowledge effect is network-dependent"
date: 2026-03-26
dag_nodes: [I02, E03]
links:
  supersedes: [XN-026]
  evidence_for: [I02]
tags: [disguised, robustness, anonymization, multi-seed]
---

# XN-033: Disguised Robustness Multi-Seed

## Objective

Re-run disguised variable experiments with correct data seeds (XN-026 used only seed=42 due to D-A02 bug). Test whether LOCALE depends on domain knowledge by anonymizing variable names (V01, V02, ...).

## Setup

- 3 networks: Insurance, Alarm, Sachs
- 3 seeds each: 0, 1, 42 (matched with real-name runs from XN-031)
- Flag: `--disguise` replaces variable names with V01, V02, ...
- Same pipeline: K=10, debiased, all-nodes, NCO Max-2SAT, confidence reconciliation
- Model: Qwen/Qwen3.5-27B-FP8, 4096 context

## Results

| Network | Real F1 | Disguised F1 | Delta | Interpretation |
|---------|---------|-------------|-------|----------------|
| Insurance | 0.858±0.005 | 0.808±0.061 | -5.0pp | Domain knowledge helps |
| Alarm | 0.793±0.111 | 0.896±0.005 | +10.3pp | Domain knowledge hurts |
| Sachs | 0.885±0.003 | 0.788±0.032 | -9.7pp | Domain knowledge helps |

### Per-seed breakdown

| Network | Seed | Real F1 | Disguised F1 | Delta |
|---------|------|---------|-------------|-------|
| Insurance | 0 | 0.860 | 0.839 | -2.2pp |
| Insurance | 1 | 0.851 | 0.723 | -12.8pp |
| Insurance | 42 | 0.863 | 0.863 | +0.0pp |
| Alarm | 0 | 0.637 | 0.901 | +26.4pp |
| Alarm | 1 | 0.889 | 0.889 | +0.0pp |
| Alarm | 42 | 0.854 | 0.899 | +4.5pp |
| Sachs | 0 | 0.889 | 0.833 | -5.6pp |
| Sachs | 1 | 0.882 | 0.765 | -11.8pp |
| Sachs | 42 | 0.882 | 0.765 | -11.8pp |

## Key Findings

1. **Domain knowledge effect is network-dependent.** On Insurance and Sachs, real variable names improve performance (LLM has useful domain priors). On Alarm, real names HURT performance (LLM has misleading priors about the alarm monitoring domain).

2. **Disguised variance is higher on Insurance.** Real-name Insurance std=0.005 vs disguised std=0.061 — the LLM is less consistent without domain anchoring. But on Alarm, disguised is MORE consistent (std=0.005 vs 0.111).

3. **NCO constraints work regardless of naming.** The pipeline still produces reasonable results with disguised names — the structural constraints (NCO + Max-2SAT) provide value independent of domain knowledge.

4. **Supersedes XN-026.** The original single-seed result (+4.7pp Insurance, 0.0pp Alarm disguised) was misleading because it only used seed=42, which happens to be the seed where Insurance shows zero delta. Multi-seed reveals the true picture is more nuanced.

## Implications for the paper

- Cannot claim "LOCALE doesn't rely on domain knowledge" — it partially does, network-dependently
- Can claim "structural constraints (NCO) provide value independent of naming" — the pipeline works with disguised names, just with reduced accuracy on some networks
- The Alarm improvement with disguised names is interesting: suggests LLM has incorrect causal priors for some domains, and anonymization forces it to rely on structure alone
