# Controller Workflow — Implementation Plan

The controller is project-local tooling, separate from stock-assessment feature delivery. The agreed target is three persistent interactive role CLI tabs communicating through explicit, validated task/report files. The controller owns routing, state and history; it never supplies product judgment. Older sections below record historical execution designs, not proof of the current live workflow.

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

## C1.2.14. Native iTerm2 three-tab layout probe

Create exactly three native default-profile tabs with fixed Coordinator, Developer, and Reviewer titles, then stop. The bridge reports one window identifier and three opaque tab identifiers, fails with the affected step plus partial-tab recovery, and never starts a command or creates workflow state. Alex validates the visible layout only after independent review in a fresh `/private/tmp` target from the activated Orchestr8 environment.

## C1.2.15. Native Coordinator Codex bootstrap probe

Create one native Coordinator tab, retrieve its session, and send one shell-quoted read-only Codex startup command with a fixed wait-for-human prompt. Report delivery as unverified and stop before any controller state or handoff. Alex visually verifies only the interactive Coordinator UI after independent review; no `Start project` message, Developer/Reviewer tab, or workflow follows in this experiment.

## C1.2.16. Staged Coordinator-first start

Provide `start --tabs` as the real workflow entry point. It requires a clean committed baseline and valid authority/configuration, snapshots the authority before delivery, and records a Coordinator-initial session and native IDs only after one successful native read-only Coordinator launch. Developer and Reviewer remain absent; accepting Coordinator reports that their staged launch is not yet implemented.

## C1.2.17. Quality gates — READY

Independent review accepted the inherited design/checklist table, Developer self-check/schema, Reviewer checklist, and report-format/inheritance tests (51 controller tests). The authorized Developer chat report completed the evidence requirement. This did not close C1.2.16.2 runtime findings.

## C1.2.18. Coordinator-stage safety — implementation reviewed; historical evidence limitation

Close the Coordinator-stage C1.2.16.2 gaps with non-mutating refusals, guarded state loading, identified-run terminalization, immutable history, structured output, and deterministic tests. Changed-task proposals require human approval and a fresh authorized run; active snapshots never change. Corrupt state is preserved without guessing, repairing or automatically archiving it; recovery requires a fresh authorized run, which may safely reuse the same project. Interrupted launch preserves evidence and requires human inspection; no automatic relaunch. The implementation was independently found satisfactory with 60 tests; its final review retained a missing Developer-chat-report requirement. Preserve that historical verdict.

The subsequent Coordinator smoke reached successful acceptance, but its result-writing mechanism was not established. No Developer/Reviewer launching was part of C1.2.18.

## C1.2.19. Developer/Reviewer staged launch — READY; manual communication proof PASSED

Human authorized proceeding on 2026-11-11 after Coordinator acceptance succeeded in the disposable smoke. Fix the stale post-acceptance status cue and implement explicit `launch developer` / `launch reviewer` commands, separated from acceptance. Each tab waits for its human phrase. Preserve Developer baseline checks, Reviewer read-only capability, the immutable task/review diff, delivery uncertainty handling, duplicate protection and one-time completion archival. Return final coordination to the existing Coordinator without another cycle. Full task and manual-maintenance/chat-report instructions are in `docs/NEXT_PROMPT.md`.

The C1.2.18 implementation was independently satisfactory; its missing Developer report remains a historical reporting-only gate. The human explicitly chose to proceed; do not rewrite the independent verdict or claim the unobserved pre-brief smoke check passed.

## Single-cycle file communication — PASSED; next is app-sent routing

The report-writing correction is independently READY with 73 deterministic tests. The human's fresh manually gated cycle in `/private/tmp/orchestr8-mvp-LCIjPe` completed iteration 001: Coordinator acceptance, Developer marker/report and acceptance, Reviewer approval/acceptance, controller-reported archive, and separate final Coordinator summary. Final status was COMPLETED_COORDINATOR_REVIEW and no new cycle authorized. See the validation record for the exact pasted evidence and limits. This closes the live report-writing blocker; it does not prove controller-sent conversation triggers.

The agreed capability policy remains: non-writing roles may write designated reports/documents, not autonomously change code. Other writes require human authorization. Production interactive workspace-write plus role ownership and handoff change checks implements this policy; it is not filesystem isolation against a hostile role.

Next bounded work: send `do next prompt`, `review latest`, and `coordinate latest` to the correct recorded interactive tabs for one authorized cycle, with explicit run/cycle and task/report paths. Validate prior evidence and approval gates; prevent wrong-tab and duplicate sends, and stop on uncertain delivery without blind retry. The approved handoff in docs/NEXT_PROMPT.md specifies explicit trigger developer/reviewer/coordinator commands with --ready human readiness confirmation. Keep explicit launch/accept gates. Implement, independently review, then perform a separate live routing proof. No app-server/non-interactive redesign or multi-cycle policy is needed for this step.

## Handoff document lifecycle — agreed direction

Use complete current-cycle documents, not a single ever-growing instruction file. Drafts may be revised before submission; accepted evidence and task snapshots are immutable. A later cycle gets its own version/iteration identity, with prior versions retained. Progress/action logs may be append-only, separate from authoritative instructions and accepted reports.

| Document | Current implementation | Required direction |
|---|---|---|
| `docs/NEXT_PROMPT.md` | Durable task authority edited/replaced through human authorization; snapshot copied into `current/authoritative_task.md` | Coordinator authors a next-task proposal; explicit approval promotes the next authority version. Never append conflicting tasks to an active snapshot. |
| `.developer.json` -> `dev_report.md` | Developer owns JSON; controller creates Markdown upon acceptance and rejects existing staged acceptance evidence | Developer supplies changes, validation and review instructions. Retain one owner/publisher per artifact; do not have role and controller overwrite the same Markdown. |
| `.reviewer.json` -> `review_report.md` | Reviewer owns JSON; controller creates Markdown upon acceptance | Reviewer supplies verdict/findings for Coordinator; freeze accepted evidence for this cycle. |
| Coordinator summary/next proposal | Coordinator report contract exists; multi-cycle proposal publication remains incomplete | Separate completed-cycle summary from proposed next instructions. A proposal does not authorize itself. |
| `history/<iteration>/` | Controller archives task, reports and state; rejects overwriting populated archives | Preserve every completed/stopped cycle. Roles never edit history directly. |

`review latest` is a trigger phrase, not a Markdown filename. The actual task and report paths must be explicit. The current Markdown reports wrap structured JSON; richer handoff prose must be supplied through a defined report contract, not assumed to exist already. Define any new draft/log paths and publisher ownership in the bounded correction before implementation.

## MVP acceptance — prove the complete single-cycle concept

Demonstrate one small authorized code task across the three interactive role tabs and final coordination, with actual file-based handoffs, accepted review, retained history and accurate status. Manual-gated communication and the app-sent single-cycle proof have passed on human-provided evidence; see the 2026-11-15 validation record. Unattended and multiple-cycle behavior remain deferred. Record which behavior each test actually establishes. Repeated cycles and unrelated enhancements must not delay this proof.

## C2. Exact-diff local commit gate

After an explicitly authorized `APPROVED` review, commit only the exact reviewed local diff. Refuse changed-after-review, unexpected, untracked, or secret files; archive commit SHA and message. Never push.

## C3. Isolated larger-project mode

Add opt-in branch/worktree isolation and configured path, diff, runtime, and iteration budgets. Protected-path or budget violations require human input.

## Later roadmap — Coordinator-led human decisions and multiple cycles

The final product target is an explicitly human-authorized cycle budget of 1, 2, 3 or N with the same persistent role tabs. Within the authorized scope and budget Orchestr8 progresses automatically until the budget is reached, work is complete, Coordinator needs human input, or a safety condition blocks progression. Coordinator cannot extend its own scope or budget. Each task cycle has its own approved task snapshot and immutable reports/history; corrections are attempts within that task cycle.

The Coordinator tab is the human consultation and approval point. It explains what happened, the decision required and the recommended next step. The controller records explicit approval and enforces it; Coordinator cannot approve its own proposal. No further role trigger is sent while a decision is pending.

Define the sensitive-action policy with the human before enabling unattended multi-cycle progression: scope changes, destructive actions, external/network actions, dependency changes, unresolved review findings and writes outside role-owned allowances are candidate categories, not a finalized permission list. Cycle authorization is never blanket approval. A next-task proposal must not silently replace the current authority or snapshot. C2/C3 remain optional and deferred.

## Operator usability follow-up — recorded 2026-11-15

The app-sent single-cycle live gate has passed; earlier “next bounded work” routing descriptions above record the prior implementation scope, not an outstanding live gate.

- Explicit controller-managed tab labels: initial `Coordinator · waiting for Start project…`, with role identity retained through running, awaiting acceptance, human-required and completed states. Chat text does not itself rename a tab. Labels must reflect controller evidence and must never serve as routing identity; retain exact session IDs. This is roadmap work, not an implemented claim.
- Environment readiness: verify the intended Python environment and iTerm dependency before preparation/launch where feasible; operator commands should use the explicit source virtualenv interpreter. Preserve uncertain-launch recovery protections.
- Provider readiness/usage: distinguish authentication/model access, API credit and subscription allowances. Surface supported checks and provider errors; report unknown where no supported balance interface exists. Do not promise available credit guarantees or expand network access without authorization.

Specify a bounded task and acceptance evidence before implementation. Keep sensitive-action policy and budgeted multiple cycles later in the roadmap.

## Active follow-up and deferred diagnostic — 2026-11-15

Authorized next task: operator clarity and launch environment preflight, bounded by docs/NEXT_PROMPT.md. Initial labels and evidence-based updates at existing commands only; no watcher/status mutation or new progression. Account readiness and cycle automation stay deferred.

Open lower-priority investigation: Coordinator compound read exited 1 during the successful `/private/tmp/orchestr8-cycle-6m6wfC` final turn. Summary writing succeeded afterward. Retain the original evidence; identify the exact command and failure before defining a deterministic regression. Do not assume optional-file absence, dismiss the failure, or claim it is fixed. This is not a blocker for the operator-clarity task.

## Active milestone — two human-gated task cycles

The preceding verification stage retains explicit control-terminal and readiness gates while proving two task cycles in the same three tabs. Reuse do next prompt / review latest / coordinate latest. Reviewer never waits for next-task approval. Coordinator prepares correction or next-roadmap instructions and hints `approve next task`; human decides there. Configured NEXT_PROMPT authority holds latest approved instructions; drafts are separate. Corrections increment attempt, not task-cycle count. Controller freezes and preserves each attempt, carries verified uncommitted work forward and enforces task/attempt budgets. Approval provenance and atomic renewal must be explicit, not inferred from role claims. These human gates are temporary verification controls, not the final automated operating model. Full bounded handoff: docs/NEXT_PROMPT.md.

Operator labels/preflight implementation has independent review (88 deterministic tests); live label observation is deferred as minor polish. This milestone supersedes the prior operator-clarity task as active work. No unattended or general N-cycle behavior is authorized.
