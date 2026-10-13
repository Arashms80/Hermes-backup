---
name: skill-manage-batch-semantics
description: Use when a skill_manage batch patch fails mid-batch.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, skill-manage, batching]
    related_skills: [hermes-agent-skill-authoring]
---

# skill_manage batch semantics

## When to Use
Use when a skill_manage operations batch fails mid-batch, or before batching patches across a skill's SKILL.md and references/ files.

- A batch is **per-op atomic, not all-or-nothing**: a patch that fails mid-batch leaves every earlier op applied and rolls back only the failing one onward. After a failure, re-read the touched files (skill_view) before retrying so you can see what landed — blind reissuing duplicates the applied ops.
- A `patch` without `file_path` searches SKILL.md for the old_string; a match that exists only in a references/ file fails clean with section suggestions. Always pass `file_path` for reference-file edits.
- Batch shape accepts `create | patch | write_file | remove_file`; `delete` must be a sole op — a `replace` action in the operations array is rejected.
- A new skill's frontmatter description is capped at ~60 chars (index truncates at 57 + '...'); move detail into the body.
