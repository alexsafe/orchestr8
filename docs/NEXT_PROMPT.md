# C1.2.14 Developer Prompt — Native Three-Tab Layout Probe

## Common task

Build the next isolated host-validation step after the successful one-tab native iTerm2 probe: create three persistent, native default-profile tabs in the active iTerm2 control window and stop. This is a layout probe only—do not start Codex, a role command, a shell bootstrap, or supervised workflow state.

## Developer work

The Developer executes this section only after `do next prompt`. Reviewer handoff is context, not Developer instructions.

1. Add an explicit `--tabs-layout-probe` initializer mode that requires `--tabs`. Keep existing `--tabs-probe` as the proven one-tab probe and keep ordinary full `--tabs` fail-closed.
2. Through the native iTerm2 Python API only, create exactly three default-profile tabs in the active/control window. Set native titles exactly `ORCHESTR8 · Coordinator`, `ORCHESTR8 · Developer`, and `ORCHESTR8 · Reviewer`. Do not supply a custom command or send text after creation.
3. Return control JSON with exactly three opaque tab identifiers, one window identifier, elapsed time, and a confirmed result. If any tab/session/title operation fails or returns `None`, stop before supervised state, report which layout step failed, and provide partial-tab/fresh-target recovery.
4. The layout probe must start no Codex process, role command, task, snapshot, role artifact, `tabs.json`, `supervised_session.json`, history, or phase state. Its sole outcome is visible three-tab layout evidence.
5. Add deterministic fake-API bridge tests that execute the bridge module for three ordered no-command tab creations/titles, failure at each creation/title step, malformed layout request, and no-state containment. Retain minimal-probe and full-tabs-fail-closed coverage.
6. Update only active native setup/probe documentation, validation evidence, and working state. State that Alex will run the layout probe from an activated Orchestr8 `.venv` and a fresh `/private/tmp` target after independent review. Run controller tests, default unittest, compile including bridge, diff check, help/dry-run checks; record exact results.

## Acceptance boundaries

- Do not alter authority/snapshot/baseline/history/capability policy or role instructions.
- No actual iTerm2/Codex invocation in Developer/Reviewer validation, no dependency installation/network, commits, pushes, worktrees, or product work.
- Do not design or implement Codex bootstrap in this task; it is the separate next experiment after a successful human layout probe.

## Reviewer handoff — context, not Developer instructions

Review C1.2.14 only after Developer evidence exists. Verify explicit mode/argument validation, native-only ordered three default-profile tabs/titles, no command/input/role/supervised-state effects, complete fake bridge failure coverage, current docs, and full-tabs fail-closed behavior. Run deterministic checks only; record verdict and limitations in `docs/controller/REVIEW_REPORT_controller.md`.
