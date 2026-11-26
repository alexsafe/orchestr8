# Developer handoff — Two human-gated task cycles in persistent role tabs

## Authorization and goal

Implement the agreed two-task-cycle workflow. The single-cycle app-sent live proof passed; see docs/controller/VALIDATION_controller.md. Preserve that behavior. This is authorized manual maintenance of the intentionally dirty Orchestr8 source checkout, not a supervised role run. No source-runtime phase, immutable maintenance snapshot or clean source baseline is required. Preserve existing changes. Do not inspect, reset or modify source .agent/runtime or existing smoke targets. Tests use disposable deterministic fixtures/fake roles. No network, dependencies, commits, worktrees or live role launches. Return Developer evidence in chat; do not independently review your own work.

The final product target is human authorization of a cycle budget, followed by automatic progression within approved scope until the budget is reached, work is complete, Coordinator needs human input, or a safety condition blocks progression. Coordinator cannot extend its own scope or budget. The explicit human gates in this task are temporary verification controls; unattended progression is not part of this implementation.

## Agreed operator model

Keep the existing persistent Coordinator, Developer and Reviewer tabs and phrases: `do next prompt`, `review latest`, `coordinate latest`. Decisions and consultation belong in Coordinator; Reviewer writes its verdict/findings and never waits for next-task approval.

Coordinator reads the completed review, proposes a bounded strategy and complete Developer instructions, and displays: `Next instructions are ready. Type approve next task to authorize them.` The human uses `approve next task` in Coordinator. No additional approval phrase is needed. Preserve explicit control-terminal operational gates and --ready confirmations for this milestone; no watcher or unattended progression.

Configured durable authority (normally docs/NEXT_PROMPT.md) always contains the latest APPROVED task. Coordinator drafts in a separate designated proposal artifact; it does not overwrite active authority, snapshots, accepted reports or history. After verified approval the controller publishes the approved task and freezes its snapshot. A changed proposal requires fresh approval. The controller owns publication and state; roles own their designated reports/proposals only.

## Decision contract

| Evidence | Coordinator proposal | Next action |
|---|---|---|
| Valid review NOT READY / existing schema equivalent with actionable findings | Correction strategy and complete replacement Developer instructions tied to findings | Wait for human approval, then another attempt of the SAME task |
| Valid APPROVED review, roadmap work remains and task budget permits | Next bounded roadmap task | Wait for human approval, then next task cycle |
| Completed scope, exhausted task budget, or human chooses stop | Completion/stop summary | No dispatch |
| Missing/inconsistent evidence, uncertain delivery, protected-file drift or other safety failure | Explain blocker and request human direction | No automatic continuation |

Do not conflate a valid negative review with a terminal safety failure. Keep existing verdict vocabulary where possible; define mappings explicitly. Unsupported/ambiguous verdicts refuse. Coordinator cannot waive findings or classify a new task as a correction to bypass the budget.

A task cycle is one approved task including its correction attempts. An attempt is one Developer → Reviewer → Coordinator pass. This milestone permits at most TWO task cycles, with a separate explicit bounded attempt limit recorded at run authorization. Every correction and next task still requires human approval. Never silently reset/extend either budget. Exhaustion requests human direction and sends nothing.

## Required implementation contracts

1. Approval provenance: bind human approval to run, task/attempt, exact proposal hash and predecessor evidence. The phrase is settled; transport authentication is not. A role-authored JSON claim that the human approved is NOT independent proof. Preserve existing explicit control-terminal gates: if the interactive bridge cannot authenticate the human message, implement an explicit human-operated control-terminal approval/advance command displaying/verifying the exact pending proposal identity. Document that the operator is recording their Coordinator decision; do not claim automatic conversational capture. No extra Reviewer decision, automatic approval or scraping. Explain the concrete operator sequence in the report. Do not introduce app-server/session architecture; report a blocker if required behavior cannot be achieved within these bounds.
2. Configured authority: adapt existing task-authority/approval protections through an explicit controller-owned renewal path, never a general bypass. Publish only the approved proposal; freeze task snapshot before Developer dispatch. Preflight stale proposal/hash, changed authority, wrong run/attempt, duplicate approval, missing predecessor and terminal/uncertain state without altering another run. Handle interrupted publication safely with preserved evidence and no automatic retry.
3. Evidence lifecycle: identify task and attempt separately. Preserve every completed attempt's immutable prompt, Developer/Reviewer evidence and decision references, including NOT READY attempts. New attempts get fresh report slots and acceptance identities. Existing latest-current paths may remain for compatibility, but controller rollover must archive/freeze predecessors first and reject late/stale artifacts. Never allow a previous report or approval to satisfy the next attempt. Specify handling of role-owned drafts, canonical published reports, final summaries and dispatch records.
4. Baseline: retain clean Git/HEAD for the initial run. Carry forward uncommitted work between approved attempts/tasks without automatic commits or resetting files. Before rollover, verify the current project matches the last recorded post-Developer identity except explicitly allowed owned artifacts. Freeze a new attempt-start identity and track that attempt's changes separately from prior changes. Unexpected edits block continuation; never silently rebaseline them. Negative review does not authorize edits by Reviewer or Coordinator.
5. Persistent tabs: reuse exact recorded window/tab/session IDs. No duplicate role launches or title-based routing. Before a new turn validate the role phase, approval, snapshot, attempt identity, prior review and appropriate baseline. Use the existing reviewed settling/transport mechanism, readiness confirmation, persisted attempt-before-send, actual iTerm statuses and no automatic resend. Do not change transport to solve lifecycle work. Closed/uncertain destinations require human recovery, not silent replacement.
6. Instructions and status: role-specific decision tables must derive from one documented authoritative policy rather than inconsistent independent copies. Clearly separate editable workflow policy, role responsibilities, approval contract, baseline contract and limits. Freeze/version effective policy for active runs so edits cannot silently alter their rules. Keep this a small local tool, not a general rule engine. Status tells operator task/attempt, review result, pending proposal/approval, exact next command and budgets without mutating evidence or implying transport is execution.
7. Generated projects inherit all contracts, schemas and assets. Preserve existing manual single-cycle behavior and capability separation. Migrate/version state explicitly or safely refuse incompatible state; do not repair existing runtime automatically.

## Acceptance evidence — write regressions before implementation where feasible

Use deterministic fake roles/native bridge APIs; no live Codex or credentials.

- Two approved tasks complete in the SAME three recorded sessions; third task cannot dispatch.
- Task 1 attempt 1 receives NOT READY, Coordinator produces a correction, human approves it, attempt 2 succeeds, and task 2 then completes. Correction retains task identity but increments attempt identity; all evidence preserved.
- Reviewer never waits for human next-task approval. Only Coordinator proposes further instructions. Role-owned approval claims alone never progress the run.
- Absent/rejected/stale/changed/wrong-run proposal approval, duplicate commands, budget exhaustion and human stop send nothing and preserve evidence appropriately.
- Uncommitted task-1 changes safely carry forward; unexpected inter-attempt edits block. Correct attribution of previous versus new project changes, including untracked files.
- Report/summary/dispatch collisions, symlinks, late role output, stale snapshot, archive conflict, interrupted publication, partial persistence and uncertain delivery cannot overwrite evidence or dispatch twice.
- No automatic commits, acceptance, role launch, budget extension or task promotion. Existing 88-test baseline regressions remain green; changes to prior expectations require explicit contract rationale.
- Initialization inheritance, documented commands, edited-policy rejection and read-only status behavior.

## Validation and required report

Run exact commands and report exits/counts:

```sh
python -m unittest tests.test_orchestrator_safety
python -m unittest
python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py
git diff --check
python .agent/orchestrate.py start --help
python .agent/orchestrate.py launch --help
python .agent/orchestrate.py trigger --help
```

Also validate every new command's help and deterministic CLI behavior. Zero tests discovered is not coverage. Provide changed files, decision/criterion mapping, exact operator sequence, self-check, known issues and remaining live gates in chat. Do not claim independent review or live success. Expected scope is controller/bridge only where needed, wrapper, role/schema/config assets, tests and active guides; explain scope expansion. Preserve all unrelated work.

Readiness vocabulary: implementation complete → independent review passed → ready for live proof → live two-cycle proof passed. Only the last establishes actual two-task behavior. After independent review, separately authorize fresh live proofs covering both the approved-next-task and NOT READY correction branches, with two-task stop and retained history. Do not run these now.

Deferred: unattended/general N-cycle automation, comprehensive sensitive-action policy, credit/allowance checks, live cosmetic-label observation, Coordinator compound-read exit-1 investigation. That exit remains an open regression candidate, not a resolved defect or blocker for this task.
