# Decision Memos

Created automatically by `/decision-log` for major changes (vetoes, reparents, challenged assumptions, merges).

ID convention: `D-<category_code>` (e.g., `D-A03` for decisions/A03_veto_intervention_independence.md).

Every memo must have YAML frontmatter:

```yaml
---
id: D-A03
title: "Veto intervention independence assumption"
date: 2026-02-28
dag_nodes: ["A03"]
links:
  - target: XN-002
    type: evidence_for
tags: ["veto", "assumption"]
---
```

- `dag_nodes`: the DAG node(s) this decision directly concerns
- `links`: optional typed links — `evidence_for`, `evidence_against`, `derived_from`, `related_to`, `supersedes`
- `tags`: optional free-text tags
