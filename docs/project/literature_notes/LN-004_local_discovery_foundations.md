---
id: LN-004
title: "Local-first causal discovery: GLL, IAMB, MMPC and the ego-graph precedent"
date: 2026-03-11
dag_nodes: [I00, I02]
links:
  evidence_for: [I00, I02]
tags: [local-discovery, ego-graph, scaling]
---

# LN-004: Local-First Causal Discovery Foundations

## Key Papers

### Neighborhood-bounded discovery
- **GLL** (Margaritis & Thrun 2000): discovers local Markov blanket of each variable.
- **IAMB** (Tsamardinos et al. 2003): iterative Markov blanket discovery with grow-shrink phases.
- **MMPC** (Tsamardinos et al. 2003): Max-Min Parents and Children algorithm — local neighborhood identification.
- **HITON** (Aliferis et al. 2003): local structure learning with bounded conditioning.
- **CMB** (Gao & Ji 2015): causal Markov blanket discovery.

### Local-to-global composition
- **Sequential local learning** (Bromberg et al. 2006): learns local structures then merges.
- **rPC** (spirtes 2000s): restricted PC for bounded-degree graphs.
- **lFCI** (Colombo et al.): local FCI for faster causal discovery with latent variables.

## How LOCALE Relates

LOCALE borrows the **local-first philosophy** from this literature:
1. The ego-graph is essentially the Markov neighborhood of a node in the skeleton.
2. Like MMPC/HITON, LOCALE's ego-graph queries are bounded by the node's degree.
3. Unlike traditional local methods that discover structure statistically, LOCALE uses the LLM to orient within a known neighborhood.

## What LOCALE Adds Beyond This Literature
1. **LLM as orientation oracle** on a pre-computed skeleton (not discovering the skeleton itself).
2. **Hard constraint compilation** (Max-2SAT) from CI-derived non-collider facts.
3. **Dual-endpoint reconciliation** for edges shared between two ego-graphs.
4. **Selective output with confidence** (Phase 6, if built).

## Key Precedent for Paper
The local discovery literature provides the conceptual foundation for LOCALE's design. The ego-graph is not arbitrary — it's the natural unit of local causal structure that has been shown to be effective for tractable inference across 25+ years of research.
