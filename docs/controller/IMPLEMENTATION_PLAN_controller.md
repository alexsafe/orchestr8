# Controller Workflow — Implementation Plan

The controller is project-local tooling, separate from stock-assessment feature delivery. It runs short-lived coordinator, developer, and reviewer processes; the controller itself is deterministic machinery and never supplies product judgment.

## C1. Authoritative dispatch and human-stop protocol

Make the controller load a project-local configuration that names a single durable task authority, sequential roles, role instructions/commands, schemas, and state/history locations. Snapshot and hash that authority before dispatch; reject stale/mismatched current state; require a clean Git baseline before a write-capable invocation; and use structured `HUMAN_REQUIRED` categories. A coordinator proposal is non-authoritative until an explicit configured approval step changes the durable authority; otherwise stop for human approval. One bounded cycle is the default; repeated cycles require explicit invocation. Preserve secret exclusions, lock/resume behavior, and reviewer read-only access. No commits, worktrees, network, or real role invocation belong in C1.

## C1.1. Safe project initialization — accepted

Add a non-executing `init` command that scaffolds the minimal project-local configuration, contracts, neutral task authority, and runtime ignore entries for either an existing Git project or an explicitly initialized new one. It refuses collisions and path escapes, preserves existing project guidance and runtime/history artifacts, never creates a task approval/commit/snapshot, and prints the explicit steps required before C1 execution. Deterministic tests cover new/existing projects, Git baseline prerequisites, collisions, path containment, and no-role/no-execution effects.

## C2. Exact-diff local commit gate

After an explicitly authorized `APPROVED` review, commit only the exact reviewed local diff. Refuse changed-after-review, unexpected, untracked, or secret files; archive commit SHA and message. Never push.

## C3. Isolated larger-project mode

Add opt-in branch/worktree isolation and configured path, diff, runtime, and iteration budgets. Protected-path or budget violations require human input.
