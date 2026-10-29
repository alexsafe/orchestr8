# Controller Workflow — Implementation Plan

The controller is project-local tooling, separate from stock-assessment feature delivery. It runs short-lived coordinator, developer, and reviewer processes; the controller itself is deterministic machinery and never supplies product judgment.

## C1. Authoritative dispatch and human-stop protocol

Make the controller load a project-local configuration that names a single durable task authority, sequential roles, role instructions/commands, schemas, and state/history locations. Snapshot and hash that authority before dispatch; reject stale/mismatched current state; require a clean Git baseline before a write-capable invocation; and use structured `HUMAN_REQUIRED` categories. A coordinator proposal is non-authoritative until an explicit configured approval step changes the durable authority; otherwise stop for human approval. One bounded cycle is the default; repeated cycles require explicit invocation. Preserve secret exclusions, lock/resume behavior, and reviewer read-only access. No commits, worktrees, network, or real role invocation belong in C1.

## C1.1. Safe project initialization — accepted

Add a non-executing `init` command that scaffolds the minimal project-local configuration, contracts, neutral task authority, and runtime ignore entries for either an existing Git project or an explicitly initialized new one. It refuses collisions and path escapes, preserves existing project guidance and runtime/history artifacts, never creates a task approval/commit/snapshot, and prints the explicit steps required before C1 execution. Deterministic tests cover new/existing projects, Git baseline prerequisites, collisions, path containment, and no-role/no-execution effects.

## C1.2. Supervised iTerm2 three-tab workflow — accepted

Package a global `orchestr8` command and target-directory initialization with an explicitly validated Coordinator → Developer → Reviewer role list. Add an optional iTerm2 tab adapter that opens persistent visible role sessions after safe initialization. The control tab owns durable state and prints exact next-role cues; human-triggered role turns write fixed handoff artifacts, while control commands validate/advance them without output copy/paste or terminal keystroke injection. Preserve all C1/C1.1 authority, approval, snapshot, containment, and safe-stop protections. Model routing is deferred to a later human-selected task-profile package.

## C1.2.1. Real macOS tab-launch remediation — superseded by C1.2.6

Repair and manually verify Terminal.app AppleScript/argument encoding after the first real disposable smoke test failed to parse the generated script before role launch. Preserve C1.2's deterministic fake-launch boundary and safe no-runtime-state launch-failure behavior.

## C1.2.2. Role isolation and same-window tabs — Terminal host portion superseded by C1.2.6

Ensure shared task context cannot cause a Developer, Reviewer, or Coordinator to assume another role, and make Terminal.app create the three role sessions as titled tabs in the original control-terminal window. Deterministic tests verify script and contract boundaries; Alex performs the real UI acceptance gate.

## C1.2.3. Smoke-readiness documentation and packaging hygiene — accepted

Document a complete, safe disposable-project path to the human UI gate and ignore local editable-install metadata so it does not contaminate the controller source baseline. No controller behavior change.

## C1.2.4. Real interactive-launch compatibility — Terminal host portion superseded by C1.2.6

Use the installed interactive Codex CLI's supported arguments and an actually tab-creating Terminal.app strategy. Deterministic tests check the adapter contract; Alex reruns the disposable UI gate.

## C1.2.6. iTerm2 persistent-tab host

Retire the unsupported Terminal.app tab adapter. Use iTerm2's supported same-window `create tab with default profile command` operation for the three static role launches, retain the control-tab/state-machine model, and fail before supervised state creation when iTerm2 cannot serve as the host. Deterministic fake-runner coverage remains the only automated host coverage; Alex performs the real disposable iTerm2/Codex smoke after independent review.

## C1.2.7. iTerm2 created-tab title scope

Keep the returned iTerm2 tab and title operation inside the owning control-window scope. Set the writable tab title directly rather than dereferencing `current session of launchedTab` outside that scope. Preserve static bootstrap-only launch behavior and retry only in a new disposable directory after review.

## C1.2.8. iTerm2 return-value-free title bootstrap

Do not use iTerm2's runtime create-tab return value. Emit the exact shell-quoted OSC title escape as part of each new tab's one static bootstrap command before `exec`, preserving role labels and no-later-input policy. Close partial tabs and use a new disposable target after any failed launch.

## C1.2.13. Native iTerm2 minimal host probe

Use iTerm2's Python API for one default-profile diagnostic tab only. The bridge must fail closed before supervised state, roles, or Codex launch; deterministic tests execute it with fake API objects and fake stdio. Active documentation uses an isolated project environment and the `--tabs --tabs-probe` path only; full `--tabs` remains unavailable pending an approved design.

## C2. Exact-diff local commit gate

After an explicitly authorized `APPROVED` review, commit only the exact reviewed local diff. Refuse changed-after-review, unexpected, untracked, or secret files; archive commit SHA and message. Never push.

## C3. Isolated larger-project mode

Add opt-in branch/worktree isolation and configured path, diff, runtime, and iteration budgets. Protected-path or budget violations require human input.
