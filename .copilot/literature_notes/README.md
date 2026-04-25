# Literature Notes

Naming convention: `LN-NNN_topic_slug.md` (e.g., `LN-001_attention_mechanisms.md`).

Every note must have YAML frontmatter:

```yaml
---
id: LN-001
title: "Attention mechanisms for retrieval"
date: 2026-02-27
dag_nodes: ["I00"]
links:
  - target: XN-001
    type: related_to
tags: ["attention", "retrieval"]
---
```

- `dag_nodes`: which DAG nodes this note relates to (1-3 recommended)
- `links`: optional typed links — `evidence_for`, `evidence_against`, `derived_from`, `related_to`, `supersedes`
- `tags`: optional free-text tags
