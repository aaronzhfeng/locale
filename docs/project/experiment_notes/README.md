# Experiment Notes

Naming convention: `XN-NNN_descriptive_slug.md` (e.g., `XN-001_baseline_smoke_test.md`).

Every note must have YAML frontmatter:

```yaml
---
id: XN-001
title: "Baseline smoke test results"
date: 2026-02-28
dag_nodes: ["E01"]
links:
  - target: I02
    type: evidence_for
tags: ["H1", "smoke-test"]
---
```

- `dag_nodes`: which DAG nodes this note relates to (1-3 recommended)
- `links`: optional typed links — `evidence_for`, `evidence_against`, `derived_from`, `related_to`, `supersedes`
- `tags`: optional free-text tags
