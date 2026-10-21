# Local Workflow Controller

- Keep this repository a small, local sequential workflow tool.
- The configured durable task authority is the only task source for a run.
- Do not weaken task snapshots, clean-baseline checks, role capability separation, structured stops, or immutable history without deterministic tests and independent review.
- No network, remote actions, automatic commits, worktrees, or real write-capable role runs without explicit authorization.
- Tests must use deterministic fake role commands; do not require Codex or credentials.
