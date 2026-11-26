# Coordinator handover — 2026-11-17

**Historical handoff:** This document records an earlier checkpoint; for the later two-cycle live proof, see [validation evidence](VALIDATION_controller.md). Its outstanding-work statements describe that earlier point in time.

**Latest closure.** The effective-policy checkpoint below has since passed independent review and Coordinator validation (104 tests). See [the checkpoint result](POLICY_CHECKPOINT_RESULT.md). Resume at correction-to-findings and scope binding and the proposal-stage human stop. The earlier 97-test status and gap 1 below describe the starting point of the policy checkpoint.

## Role and authorization

You are the Orchestr8 Coordinator. Keep communication concise, concrete and goal-oriented. Inspect current code/diff and evidence before describing status; reports have lagged implementation. Do not implement or dispatch real roles as Coordinator. Prepare bounded Developer instructions and assess evidence. Do not issue Reviewer verdicts on its behalf.

Source checkout is intentionally dirty. Development is explicitly authorized manual maintenance outside supervised runs: no source-runtime session/snapshot or clean source baseline prerequisite. Do not read/reset/change source .agent/runtime or prior smoke targets. Preserve all existing changes. No network, dependencies, real role launches, automatic commits/worktrees without authorization. Deterministic tests use fake roles. Developer completion report is chat-only; never require a maintenance runtime artifact.

Read AGENTS.md, docs/NEXT_PROMPT.md, this file, current code/diff, latest review report and relevant tests. Do not copy this conversation into a new task or restart design.

## Agreed product target

Human authorizes a task-cycle budget. Eventually routine Developer → Reviewer → Coordinator transitions run automatically within that scope/budget; pause for Coordinator human decisions, safety failures, completion or exhausted budget. Automation is a LATER stage.

Current milestone: two human-gated tasks in the SAME three interactive tabs. Existing triggers remain do next prompt / review latest / coordinate latest. Reviewer reports and never waits for next-task approval. Coordinator reads findings and proposes a correction or next roadmap task, displays `approve next task` hint, and receives human direction. Current bridge cannot authenticate chat approval: explicit human control-terminal approve-next records approval against the exact displayed proposal identity. Do not claim role-authored approval is human provenance.

A task cycle includes its corrections. Each Developer → Reviewer → Coordinator pass is an attempt. Corrections retain task identity/increment attempt; next task increments task identity/resets attempt. Separate task/attempt limits apply. Draft proposal is separate from configured durable authority; controller publishes latest APPROVED NEXT_PROMPT and snapshot. Previous evidence immutable. Initial clean Git baseline; verified uncommitted carry-forward between attempts/tasks without automatic commits. Unexpected project drift blocks.

## Verified milestones and limits

- Single-cycle app-sent human-gated proof passed in /private/tmp/orchestr8-cycle-6m6wfC; logs /private/tmp/orchestr8-cycle-logs-CEXYTT. Evidence in VALIDATION_controller.md, based on human-pasted outputs, not an independent target audit.
- Interactive submission originally left text unsent. Controlled late Return worked; one-second settling sequence then passed focused and full-cycle live proof. Preserve exact destination, actual transport statuses, prepared attempts and no automatic resend. Transport OK is not execution acknowledgement.
- Operator labels/preflight independently reviewed (88 tests at that checkpoint). Live label observation deliberately deferred as minor polish.
- Approval/correction rollover independently READY CHECKPOINT ONLY, review report records 97 tests. Verdict EXCLUDES next-task rollover, budgets and full two-cycle scope.
- Current Developer reports 97-test full suite pass, default unittest zero discovery, compile/diff check and all relevant help checks passed. Coordinator has inspected that next-task code and integrated test exist; do not instruct Developer to implement them from scratch. Full handoff remains incomplete.

## Current implementation (verify before editing instructions)

.agent/orchestrate.py includes proposal, approve-next, rollover-correction, rollover-next-task; start --task-limit / --attempt-limit. Actionable CHANGES_REQUIRED archives evidence and returns to Coordinator; unsafe/malformed evidence still stops/refuses. Approved rollover preserves archives/project changes, publishes authority/snapshot, creates fresh slots and sends nothing. Subsequent explicit trigger reuses recorded sessions.

Integrated fake-role test covers correction of task 1, successful task 2, refusal of task 3, stale output, duplicate dispatch and change attribution; separate attempt-exhaustion test. Partial-persistence coverage exists but complete requested matrix is not demonstrated.

## Remaining full-handoff gaps (latest Developer report)

1. Effective workflow policy is not frozen/versioned for active runs; role decision tables do not derive from one authoritative policy.
2. Verdict gates choose correction vs next task, but correction intent/findings/scope binding is incomplete. Do not promise mechanical semantic proof: controller should enforce immutable task/findings references and required mappings; human explicitly confirms scope. Hash equality alone cannot prove a correction is substantively correct. Any acceptance-criterion change must be disclosed, not silently waived.
3. Complete two-cycle collision, interrupted-publication, human-stop, initialization-inheritance and edited-policy matrix remains undemonstrated. Rollover tests chiefly invoke functions; actual CLI paths need tests.
4. No dedicated recorded proposal-stage human stop. Older runs without budgets safely refuse rollover; do not auto-migrate/rebaseline them.
5. Next-task rollover, budgets and full lifecycle require independent review. Neither new branch has live proof.

## Next concrete Developer checkpoint

Do NOT resend the entire two-cycle design or implement next-task rollover again. First close gap 1: one small authoritative policy definition, effective policy identity frozen at initial start and preserved through both rollover kinds, role decision guidance derived consistently, and tests proving changed active policy cannot silently alter rules plus init inheritance. No general rule engine. Write/run failing regression, implement, run targeted and full required checks, report actual diff and remaining gaps. Then close proposal-stage stop/correction binding and the missing CLI/failure matrix. Review bounded checkpoints if useful, but final scope verdict must cover everything.

Coordinator should confirm actual progress from code/test evidence after each report. Developer final message must distinguish implemented/tested/reviewed/live-proven. Acknowledgements are not completion reports.

## Repeated Developer stopping — evidence and handling

Several turns ended normally with no implementation and no stated blocker. Local session inspection found task_complete events after ~22s and ~63s, no recorded turn errors/disconnections/approval failures in inspected turns, and no limit-reached indication. Both used gpt-6.1-terra medium. These observations do NOT prove the internal cause or a server/model defect. Fresh session alone initially did not fix it. Bounded slices subsequently produced negative-review, approval and rollover implementations.

Do not blame internet or keep rewriting product requirements. Require a concrete regression/code result or an exact blocking command/invariant. If no progress recurs, inspect actual turn diagnostics/settings instead of accepting another generic incomplete report. Do not invent root causes or change model settings without user direction.

## Repository and commit discipline

Large mixed uncommitted diff spans completed milestones and partial two-cycle changes. Last observed HEAD fba08d9 (verify current). .venv/, .DS_Store and SUBMISSION_SMOKE.md were untracked; do not use git add . or discard them. User wants periodic commits of approved completed flows. First isolate exact reviewed changes and verify commit contents; do not pretend the entire current diff is approved. No commit has been made by Coordinator.

## Deferred

- Coordinator compound read exited 1 before successful final summary in completed smoke: unknown component/cause; preserve as investigation/regression candidate, not blocker or resolved issue.
- Live cosmetic label checks.
- Provider authentication/model/credit allowance checks where supported; unknown means unknown.
- Unattended progression, general N-cycle budgets, comprehensive sensitive-action escalation policy, optional commit/worktree features.

## Readiness language

Implementation complete ≠ independently reviewed ≠ live verified. Current status: implemented two-task core with specified acceptance gaps; NOT READY for full review/live proof. Reviewer checkpoint READY must never be generalized. No new smoke is necessary until complete scope review passes.
