# Controller C1 — Independent Review

## C1.1 independent review — Safe project initialization

### Scope

Read-only review of C1.1 only. I inspected `AGENTS.md`, `docs/NEXT_PROMPT.md`, the C1.1 diff, `.agent/orchestrate.py`, generated role/schema assets, and initialization documentation. No implementation file was modified; no Codex role, network service, commit, push, or write-capable controller cycle was invoked.

### Independent evidence

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 18 tests in 3.108s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery finds no tests).
- `git diff --check` — exit `0`.
- `python .agent/orchestrate.py --dry-run` — exit `0`; reported the configured authority, ordered roles, and `max_iterations: 1`; no role dispatch occurred.
- In an isolated existing Git repository, `init` exited `0`, created the documented config, role instructions, schemas, empty approval record, neutral authority, controller reference, and only `.agent/runtime/state.json`; neither `current` nor `history` existed. It appended only `.agent/runtime/` and `.agent/orchestrate.lock` to `.gitignore`. After a local baseline commit, the generated controller's `--dry-run` exited `0`.
- Generated configuration and all copied schemas are JSON and are accepted by the generated controller's `--dry-run`. Source inspection confirms `init` has no `run_role`, snapshot, approval, archive, commit, or push path; its only subprocess actions are Git repository checks/explicit `git init`.
- The deterministic suite covers explicit Git initialization without `HEAD`, ordinary path escapes, conflicts/idempotent refusal, preserved project files, and no runtime current/history artifacts. It does not cover symlinked scaffold parents.

### Blocking finding

`.agent/orchestrate.py:L66-L93`: `init` checks child target existence but does not resolve/contain-check every target before writing. A project with `.agent` as a symlink to an external empty directory passes the collision check; `init` exited `0` and wrote `controller_config.json`, approval record, copied script/roles/schemas, and `runtime/state.json` into that external directory. This violates the required collision/path-escape refusal and preservation guarantees.

Closure criterion: before `git init` or any scaffold write, resolve and project-root-containment-check every destination and reject symlinked/existing controller parents that could redirect a write; add a deterministic test proving the external target remains untouched and the project receives no partial scaffold.

### C1.1 verdict

**NOT READY.** Passing baseline checks and ordinary initialization behavior do not compensate for the reproduced scaffold path escape. Re-review is required after the finding is fixed and covered by a deterministic test.

## Scope and independent evidence

Fresh final review of C1 only: configuration/approval files, role contracts, `.agent/orchestrate.py`, controller documentation, `README.md`, controller tests, and the relevant diff. Unrelated stock-feature work was not reviewed or modified. No Codex role, network, provider, secret, commit, or push was invoked.

Independent commands run from the repository root:

- `python -m unittest tests.test_orchestrator_safety` — `Ran 14 tests in 2.514s`; `OK`.
- `python -m unittest` — `Ran 61 tests in 2.488s`; `OK`. This is deterministic/fixture coverage; no live validation ran.
- `git diff --check` — exit `0`.
- `python .agent/orchestrate.py --dry-run` — exit `0`; reported the configured authority, fixed semantic role order, and `max_iterations: 1`; no role was dispatched.

All C1 safety findings are closed. `validate_output()` now loads the selected role schema and enforces required properties, declared scalar/array item types, enum values, nullability, and `additionalProperties: false` (`.agent/orchestrate.py:61-79`). The 14-test controller suite exercises otherwise-valid Coordinator, Developer, and Reviewer outputs with extra fields and verifies their archived safe stops. `load_config()` requires boolean `write_capable` and the only supported allocation—Developer true, Coordinator/Reviewer false (`L35-39`); the fake command confirms Reviewer receives `read-only`. Earlier independently verified protections remain in place: immutable authority snapshots, approval-bound authority changes, pre-runtime clean baseline, fixed role ordering, safe resume/failure stops, secret exclusion, immutable history, and explicit multi-cycle behavior.

## Non-blocking correction

`README.md:37` still says runtime state is only in `.agent/state.json`; the configured implementation uses `.agent/runtime/state.json`. Correct that sentence in the next documentation-only change.

## Verdict

**READY WITH NON-BLOCKING CORRECTIONS.** C1 is accepted for its bounded controller scope. The README state-path sentence should be corrected, but it does not affect the enforced runtime behavior. No stock-feature work is implicated.

## C1.1 independent review — Safe project initialization

Reviewed C1.1 only: the durable authority, initialization implementation, generated assets, documentation, tests, and actual diff. No role, network, provider, commit, push, or write-capable controller cycle was invoked.

Independent checks:

- `python -m unittest tests.test_orchestrator_safety` — `Ran 18 tests in 3.251s`; `OK`.
- `python -m unittest` — `Ran 0 tests in 0.000s`; `OK`; the explicit module is the relevant suite.
- `git diff --check` — exit `0` before this report update.
- `python .agent/orchestrate.py --dry-run` and `python .agent/orchestrate.py init --help` — exit `0`; neither dispatched a role.

### Blocking finding

**NOT READY.** The `init` preflight resolves only the authority path. It checks scaffold destinations lexically, so a target-project `.agent` symlink to an empty external directory passes the collision check; writes then follow it outside the requested project root (`.agent/orchestrate.py:61-93`).

Independent isolated reproduction: created a project with `.agent` symlinked to a sibling `outside` directory, then ran `init --init-git`. The command exited `0`, printed successful initialization, and created `outside/controller_config.json`; `git rev-parse --verify HEAD` returned `128`, confirming no commit. This violates containment, preservation, and no-partial-unsafe-overwrite requirements. Current tests cover `..` authority paths but not symlinked scaffold parents.

Closure criteria: before `git init` or any scaffold write, reject symlinked target paths or prove every resolved destination remains beneath the resolved project root. Add deterministic `.agent`, `docs`, and nested-parent symlink tests asserting refusal, no external writes, no target Git initialization, and preservation. Re-run the stated checks and request a new independent review.

### C1.1 verdict

**NOT READY.** C1 remains accepted; C1.1 requires symlink-safe preflight remediation.

## C1.1 remediation — fresh independent review

This read-only review covers only the symlink-safe initialization remediation. I inspected `AGENTS.md`, the current immutable C1.1 authority, implementation/diff, generated assets, tests, and initialization documentation. No implementation changes, role/Codex invocation, network access, commit, push, or write-capable controller cycle occurred.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 20 tests in 3.365s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py` — exit `0`.
- `git diff --check` — exit `0`.
- `python .agent/orchestrate.py --dry-run` — exit `0`; reported the configured authority, fixed role order, and `max_iterations: 1`, without dispatching a role.
- Fresh temporary-project checks ran `init --init-git` with `.agent`, `docs`, and `.gitignore` each symlinked externally. Each exited `2`, reported the symlinked component, left the external target empty, and left no target `.git` directory.
- A fresh project-root symlink test exited `0`; configuration and copied schemas parsed as JSON at the resolved root, `.agent/runtime/current` and `history` were absent, and `git rev-parse --verify HEAD` exited `128`, confirming explicit Git initialization did not commit.

`preflight_init_destinations()` now iterates every planned destination's existing components before the Git check or a write, and `path_exists()` detects dangling collision links. Regression tests cover `.agent`, `docs`, and project-root symlink cases; existing C1.1 tests retain collision/path-escape refusal, preservation, no-role/no-history behavior, narrow ignore additions, generated-controller dry-run after a baseline, and no-`HEAD` initialization.

### C1.1 remediation verdict

**READY.** The prior internal-symlink path-escape finding is closed with deterministic coverage. C1.1 remains bounded to non-executing project scaffolding; C2/C3 and real write-capable cycles are not reviewed or authorized.

## C1.2 independent review — Supervised macOS three-tab workflow

Read-only review of C1.2 only. I inspected the current task authority, package entry point, controller diff, role contracts, tests, and documentation. No Terminal tab, Codex role, network service, commit, push, or write-capable workflow cycle was invoked.

Independent checks:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 23 tests in 3.640s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python orchestr8.py --help`, `python orchestr8.py preview`, and `python .agent/orchestrate.py --dry-run` — exit `0`; only state/help was printed and no role was dispatched.
- The fake-launcher test opens no real Terminal tab or Codex session. Its printed accepted-phase output independently exposes a next-action defect after Reviewer acceptance: it reports `coordinator: Start project: <human initial brief>` rather than the required post-review phrase.

### Blocking findings

`.agent/orchestrate.py:L49-L54`: `launch_terminal_tab()` hard-codes `codex` and omits the configured role command and `write_capable` sandbox allocation. Coordinator and Reviewer tabs therefore are not enforced read-only, breaking C1 role capability separation. Build each interactive launch from the configured role command and enforce read-only for Coordinator/Reviewer and write capability only for Developer; add fake-launch specifications asserting this.

`.agent/orchestrate.py:L77-L96`: `supervised_accept()` advances Coordinator → Developer → Reviewer without `clean_baseline()`, baseline/after manifests, state transition updates, `human_stop()`, `finish()`, or `archive()`. A dirty or HEAD-less project can reach Developer, and accepted evidence remains mutable in `current` with no immutable iteration history. Reuse the C1 lifecycle/invariants for supervised handoffs and add deterministic dirty-baseline, no-HEAD, stop, and archive tests.

`.agent/orchestrate.py:L30,L59-L61,L95`: the controller represents both initial and post-review Coordinator as one phase, so `cycle`/`status` after Reviewer acceptance prints `Start project` instead of `coordinate latest review`; `cycle` also only prints state and does not validate/schedule a handoff. Track the Coordinator substate and emit the exact legal next phrase/artifact contract required by C1.2.

### C1.2 verdict

**NOT READY.** The visible-tab UX and deterministic fake-launch coverage exist, but the implementation weakens mandatory C1 baseline, capability, structured-stop, and immutable-history protections. Re-review after all blocking findings are closed with deterministic tests.

## C1.2 lifecycle/capability remediation — independent review

Read-only review of the C1.2 remediation only. I inspected the current task authority, controller/configuration/role-contract changes, package entry point, tests, and documentation. No real Terminal tab, Codex role, network call, commit, push, or write-capable workflow cycle was invoked.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 25 tests in 3.798s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python orchestr8.py --help`, `python orchestr8.py preview`, and `python .agent/orchestrate.py --dry-run` — exit `0`; they displayed state only.
- Source/test inspection confirms configured `session_command` plus effective `read-only`, `workspace-write`, `read-only` tab allocation; supervised Coordinator now calls the clean-baseline/snapshot path, and final Reviewer acceptance archives C1 iteration evidence.

### Blocking findings

`.agent/orchestrate.py:L30,L63-L65` and `docs/controller/README.md:L9`: the control terminal emits `developer: do next`, `reviewer: do review`, and post-review `coordinator: review latest`; the required exact phrases are `do next prompt`, `review latest`, and `coordinate latest`. The visible role contracts already use the required wording, so status/cycle contradict the tabs. Update `ROLE_PHRASES` and documentation, then assert every phase's exact control output in deterministic tests.

`.agent/orchestrate.py:L89-L92,L120-L130`: `supervised_session.json` is parsed but not shape-validated. A JSON list triggers `AttributeError` at `session.get`, and a dict with `"phase": null` reaches `displayed_role(None)` in `supervised_stop`; neither is caught or archived as a structured stop. Validate the session object and phase before dereference, route malformed session state through `supervised_stop`, and add malformed-list/null-phase tests for both `accept` and `cycle`.

### C1.2 remediation verdict

**NOT READY.** Baseline, capability, and immutable-history remediation is substantively present, but exact operator guidance and fail-closed handling of corrupt supervised state remain mandatory C1.2 safety requirements.

## C1.2 phrase/session-state follow-up — independent review

Read-only review of the final C1.2 follow-up. I inspected the current task authority, implementation/configuration, role contracts, documentation, package entry point, and deterministic tests. No real Terminal tab, Codex role, network service, commit, push, or write-capable workflow cycle was invoked.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 27 tests in 3.819s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python orchestr8.py --help`, `python orchestr8.py preview`, and `python .agent/orchestrate.py --dry-run` completed without launching a tab or role; help/dry-run displayed expected metadata.
- `ROLE_PHRASES`, all role contracts, and C1.2 documentation now use the exact four required phrases: `Start project: <human initial brief>`, `do next prompt`, `review latest`, and `coordinate latest`. The deterministic suite asserts each displayed phase.
- `load_supervised_session()` validates object shape and a known string phase before dereference. `accept`, `cycle`, `status`, `preview`, and `resume` route missing, invalid-JSON, list, null, and unknown session state through archived `stale_or_mismatched_task_state` stops. Archive coverage includes the supervised session and structured stop.
- The earlier remediation remains present: configured interactive commands enforce `read-only`, `workspace-write`, `read-only`; supervised Coordinator establishes the C1 clean `HEAD` baseline and immutable snapshot; Developer/Reviewer evidence and failure paths archive under history.

### C1.2 verdict

**READY.** The C1.2 supervised workflow now preserves the reviewed C1/C1.1 safety boundaries with deterministic coverage. Real macOS/Codex tab execution remains an explicit operator action and was not exercised by this review.

## C1.2.1 independent review — macOS tab-launch remediation

Read-only review of C1.2.1 only. I inspected the current task authority, AppleScript construction and launch boundary, deterministic fake-runner test, package metadata, documentation, and actual diff. I did not open Terminal tabs, invoke Codex, use a network service, commit, or run a write-capable workflow cycle.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 28 tests in 3.801s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- The fake `osascript` runner receives exactly `['osascript', '-e', source]` with `text=True, capture_output=True`; its inspected source contains direct Unicode `·`, shell-quoted command/path arguments, and escaped AppleScript quotes, without JSON `\\u00b7` source escapes. It does not open Terminal or invoke Codex.
- Existing C1.2 lifecycle, configured capability allocation, phrase/state validation, and launch-failure tests continue to pass.
- Developer validation records a successful disposable macOS smoke observation of exactly three expected labeled tabs. This review did not repeat that real external interaction.

### Non-blocking correction

`.gitignore`: the documented editable install leaves the untracked `orchestr8.egg-info/` directory in this controller checkout. After implementation files are committed, that artifact still makes the source checkout fail the C1 clean-baseline guard. Ignore standard local packaging metadata (for example `*.egg-info/`) or document a cleanup step.

### C1.2.1 verdict

**READY WITH NON-BLOCKING CORRECTION.** The AppleScript encoding defect is addressed with deterministic source-level coverage and a recorded manual smoke observation. The unignored local packaging artifact should be corrected before relying on the controller source checkout for a clean-baseline cycle.

## C1.2.2 independent review — role isolation and same-window tabs

Read-only review of C1.2.2 only. I inspected the current task authority, role contracts, Terminal.app AppleScript construction, deterministic fake-runner tests, and documentation. No Terminal tab, Codex role, network call, commit, or write-capable workflow cycle was invoked.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 29 tests in 3.791s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- Role contracts designate Common task plus each role's owned section, explicitly mark other-role sections as context only, prohibit cross-role outputs/verdicts, and name distinct fixed JSON outputs. Contract tests assert the paths do not overlap.
- `terminal_tab_applescript()` explicitly captures `front window`, uses `do script ... in targetWindow`, captures the returned `launchedTab`, and assigns the title to that object. The fake `osascript` test verifies these properties without opening Terminal or invoking Codex.

### Non-blocking follow-ups

- The C1.2.2 manual gate is correctly not claimed by deterministic evidence. Its documented fresh-init commands leave a neutral authority and no Git `HEAD`, so add the bounded-authority/baseline steps needed to reach the Developer phase before asking the human to verify the `do next prompt` behavior.
- The prior `orchestr8.egg-info/` clean-baseline hygiene correction remains outstanding; it is still untracked after the documented editable install. Ignore `*.egg-info/` or document cleanup.

### C1.2.2 verdict

**READY WITH NON-BLOCKING CORRECTIONS.** The reviewed implementation preserves the C1/C1.1/C1.2 safeguards and has deterministic coverage. Real same-window layout and live Developer behavior remain explicit human acceptance gates.

## C1.2.3 independent review — smoke-readiness documentation and packaging hygiene

Read-only review of C1.2.3 only. I inspected the task authority, `.gitignore`, root/controller documentation, validation evidence, and changed-file scope. No Terminal tab, Codex role, network call, commit, or write-capable workflow cycle was invoked.

Independent evidence:

- `git diff --check` — exit `0`.
- `git check-ignore -v orchestr8.egg-info/PKG-INFO` resolves to `.gitignore:*.egg-info/`; the existing editable-install metadata is no longer reported by `git status --porcelain`.
- The disposable smoke guide initializes the project, requires same-window tab observation, replaces the neutral authority with labeled Common task/Developer work/Reviewer handoff sections, creates a Git baseline, then directs Coordinator acceptance before the exact Developer phrase. This matches the C1 initial-authority policy: no approval record is needed before a first accepted snapshot, while `clean_baseline()` requires the documented `HEAD` before Developer can proceed.
- The guide identifies expected artifacts and requires a structured stop rather than manual phase advancement for missing, malformed, stale, or cross-role evidence. It explicitly makes no claim of a successful UI or Codex run.

### C1.2.3 verdict

**READY.** The documentation-only change closes both prior smoke-readiness and editable-install hygiene follow-ups without changing controller behavior or weakening C1/C1.1/C1.2 protections.

## C1.2.5 independent review — Terminal tab-operation compatibility

Read-only review of C1.2.5 only. I inspected the current task authority, generated AppleScript, deterministic fake-runner coverage, documentation, and the locally installed Terminal scripting definition at `/System/Applications/Utilities/Terminal.app/Contents/Resources/Terminal.sdef`. I did not open Terminal, invoke Codex, use a network service, commit, or run a write-capable workflow cycle.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 29 tests in 3.773s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- The local Terminal definition declares standard `make` and `do script`; `do script` accepts an explicit `tab` or `window` target. The interactive command retains configured `session_command`, `-C`, and `-s`, without interactive `--skip-git-repo-check`.
- The adapter captures `front window`, targets `do script` at `launchedTab`, and does not use `move launchedTab`; fake-runner coverage exercises source construction only and opens neither Terminal nor Codex.

### Blocking finding

`.agent/orchestrate.py:L79`: `make new tab at end of tabs of targetWindow` is not grounded in the local Terminal scripting interface. The local `Terminal.sdef` declares the `window` `tab` element with `access="r"`, so it does not advertise creating/inserting tabs through standard `make`. The prior real smoke already failed with Terminal AppleEvent `-10000`; this replacement can compile while failing the same required operation at runtime. Use a same-window operation that the local dictionary explicitly supports, then add a deterministic assertion for that final strategy and repeat Alex's disposable manual gate.

### C1.2.5 verdict

**NOT READY.** The code removes the unsupported `move`, preserves the interactive flags and fail-before-state intent, but its new direct `make` operation is unsupported by the inspected local Terminal dictionary. No real UI result is claimed by this review.

## C1.2.6 independent review — iTerm2 persistent-tab host

Read-only review of C1.2.6 only. I inspected the current task authority, configuration, iTerm2 adapter, role specifications, deterministic tests, documentation, and current diff. I verified the AppleScript operation against [iTerm2's scripting reference](https://iterm2.com/documentation-scripting.html), which documents `create tab with default profile command` inside `tell current window`, returning the new tab; it also documents the session `name` property. iTerm2 is not installed locally, so no local dictionary inspection or real iTerm2/Codex session was possible or attempted.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 31 tests in 3.818s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py --dry-run` did not launch iTerm2 or a role; it stopped on pre-existing runtime/configuration mismatch, as expected for that ignored state.
- The generated script captures the front iTerm2 window, creates a tab through its documented window-scoped operation, runs the sole static bootstrap at creation, and names that returned tab's current session. It neither targets the control tab nor injects later phrases/commands. The role specs preserve configured commands and `read-only`, `workspace-write`, `read-only` allocation; `tabs.json` remains non-authoritative.
- `supervised_init()` launches before creating `tabs.json` or `supervised_session.json`; failure wraps a `HUMAN_REQUIRED` structured stop. The fake runner covers host rejection and failure with no runtime state.

### Blocking finding

`.agent/orchestrate.py:L410`: `--tabs` still advertises “macOS Terminal role tabs.” This is an active product-facing claim of the retired unsupported Terminal.app workflow, contrary to C1.2.6's required iTerm2-only documentation/retirement. Change the help text to iTerm2 and add a deterministic help assertion.

### C1.2.6 verdict

**NOT READY.** The supported iTerm2 creation operation and safety boundaries are otherwise present, but the stale CLI claim must be removed before Alex's fresh-disposable iTerm2/Codex smoke gate. No real host execution was performed by this review.

## C1.2.6.1 independent review — stale Terminal CLI-claim retirement

Read-only review of C1.2.6.1 only. I inspected the current authority, changed CLI help, subprocess regression, active root/controller documentation, working-state and validation entries. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 32 tests in 3.972s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; `--tabs` states `open supervised iTerm2 role tabs after successful initialization`.
- The new regression invokes the actual `init --help` subprocess, requires the exact iTerm2 wording, and rejects `Terminal role tabs`; it is not merely a source-text assertion.
- Active README and controller C1.2.6 guidance consistently name iTerm2 as the sole automatic-tab host. Remaining Terminal references are scoped to historical/superseded audit entries or the generic statement that tests do not automate a terminal.
- The affected controller behavior is limited to CLI wording and its regression; no iTerm2 launcher, role permission, authority/snapshot, state-transition, or host-selection logic changed.

### C1.2.6.1 verdict

**READY.** The stale product-facing Terminal.app claim is retired with a meaningful deterministic guard. Alex's fresh-disposable iTerm2/Codex smoke remains the required human gate and was not performed by this review.

## C1.2.7 independent review — iTerm2 created-tab session reference

Read-only review of C1.2.7 only. I inspected the current authority, adapter, role specifications, deterministic fake-runner coverage, documentation, and the locally installed iTerm2 3.7.6 scripting definition at `/Applications/iTerm.app/Contents/Resources/iTerm2.sdef`. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 32 tests in 3.863s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it retains iTerm2-only `--tabs` wording. `python .agent/orchestrate.py --dry-run` did not launch iTerm2 or a role and stopped on the pre-existing ignored runtime/configuration mismatch.
- The installed dictionary declares `create tab with default profile` as a window operation returning `tab`; `window` responds to it. It declares writable `tab` property `title`. The revised script retains `launchedTab` and sets `title of launchedTab` inside `tell targetWindow`, rather than dereferencing `current session of launchedTab` outside that scope.
- The source-level fake-runner test requires title assignment after tab creation within the owning window scope and rejects the failed session dereference. Existing checks retain configured static bootstrap, `-C`, effective `read-only`, `workspace-write`, `read-only` allocation, safe quoting, iTerm2-only host rejection, and no-runtime-state containment for launch failure.
- The recorded C1.2.6 smoke failure (`missing value (-1728)`) is accurately retained as failed; current documentation requires a new disposable directory and does not claim a successful retry.

### C1.2.7 verdict

**READY.** The replacement title operation is supported by the installed iTerm2 dictionary and is scoped to the created tab's owning control window. Alex's fresh-disposable iTerm2/Codex smoke remains the required human gate and was not performed by this review.

## C1.2.8 independent review — iTerm2 return-value-free tab identification

Read-only review of C1.2.8 only. I inspected the current authority, iTerm2 adapter, role specifications, deterministic fake-runner coverage, documentation, and installed iTerm2 resources. I also checked iTerm2's [feature-reporting reference](https://iterm2.com/feature-reporting/), which documents OSC 0 with BEL termination as setting the window and icon titles, and its [preferences reference](https://iterm2.com/3.6/documentation-preferences-general.html), which documents per-tab handling of OSC 0/2 titles. I did not open iTerm2, invoke Codex, use a network service beyond documentation lookup, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 32 tests in 4.022s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0` with iTerm2-only `--tabs` wording. `python .agent/orchestrate.py --dry-run` did not launch iTerm2 or a role and stopped on the pre-existing ignored runtime/configuration mismatch.
- The adapter scopes `create tab with default profile command` to the captured iTerm2 control window but neither binds nor dereferences its result. Its one static, shell-quoted bootstrap changes into the target project, emits the exact OSC 0/BEL title, then `exec`s the configured command with `-C`, effective sandbox, and role instruction.
- The fake-runner test asserts shell-safe title quoting and rejects `launchedTab`, `current session of launchedTab`, and `title of launchedTab`. Existing coverage preserves configured commands, `read-only`, `workspace-write`, `read-only` allocation, iTerm2-only host rejection, and no supervised runtime state after launch failure.
- Current recovery guidance accurately records the C1.2.7 `-10006` failure, requires closing any partial role tabs, and requires a new disposable directory. It does not claim a successful retry.

### C1.2.8 verdict

**READY.** The return-value dependency is removed, and title emission uses documented iTerm2-supported OSC behavior within the new session's only bootstrap command. Alex's new-disposable iTerm2/Codex smoke remains the required human gate and was not performed by this review.

## C1.2.9 independent review — iTerm2 visible-session confirmation

Read-only review of C1.2.9 only. I inspected the current authority, iTerm2 adapter, deterministic tests, active documentation, validation evidence, and installed iTerm2 scripting definition. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 33 tests in 3.937s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0` with iTerm2-only `--tabs` wording. `python .agent/orchestrate.py --dry-run` did not launch iTerm2 or a role and stopped on the pre-existing ignored runtime/configuration mismatch.
- The installed iTerm2 definition confirms the captured window exposes `tabs` and responds to `create tab with default profile`. The adapter records that captured window's count before creation and raises unless its tab count increases by exactly one before returning. `supervised_init()` creates `tabs.json` and `supervised_session.json` only after all three launches return.
- The static bootstrap retains the configured command, project `-C`, role instruction, effective sandbox, and OSC title. It captures the command exit status, displays it, and opens an inspection shell; it neither uses a returned tab reference nor injects later workflow input. Fake coverage includes a later launch failure with no supervised runtime state.

### Blocking finding

`README.md:L13,L21`: the active root smoke guide still labels C1.2.8 as the manual gate and describes the older C1.2.7 failure. It omits the observed C1.2.8 false-success/transient-tab failure and C1.2.9's count-confirmation/recovery procedure. Update this active guide to C1.2.9, state that C1.2.8 wrote supervised state without persistent tabs, and require closing partial tabs plus a new disposable target.

### C1.2.9 verdict

**NOT READY.** The implementation and deterministic containment evidence meet the reviewed creation-confirmation and inspectable-startup boundaries, but the required active root recovery documentation remains stale. No real iTerm2/Codex retry was performed by this review.

## C1.2.9.1 independent review — current smoke-recovery documentation

Read-only review of C1.2.9.1 only. I inspected the current authority, active root/controller smoke guides, validation evidence, and working-state entries. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; `--tabs` remains iTerm2-only and does not launch a host.
- `rg -n -- "C1.2.8|C1.2.9|iTerm2" README.md docs/controller/README.md` confirms both active guides identify C1.2.9 and iTerm2 as the only automatic-tabs host.
- Root `README.md` now records the C1.2.8 false-success outcome: supervised state existed although role tabs were not persistent. It requires C1.2.9 control-window count confirmation, an inspectable shell after role-command exit, closure of partial tabs, a new disposable target, and no handoff advancement from the failed target.
- The guide makes no claim that the required human iTerm2/Codex smoke succeeded. Working state retains that post-review fresh-disposable gate.

### C1.2.9.1 verdict

**READY.** The active root recovery guide now accurately reflects C1.2.9 behavior and failure handling without changing controller behavior or safety policy. Alex's fresh-disposable iTerm2/Codex smoke remains the required human gate and was not performed by this review.

## C1.2.11 independent review — one-tab iTerm2 host probe

Read-only review of C1.2.11 only. I inspected the current authority, probe implementation, fake-runner tests, active documentation, validation evidence, and installed iTerm2 scripting interface. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 34 tests in 3.914s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it documents explicit `--tabs-probe` requiring `--tabs`. `python .agent/orchestrate.py --dry-run` did not launch iTerm2 or a role and stopped on the pre-existing ignored runtime/configuration mismatch.
- The probe generates one `ORCHESTR8 · Host probe` spec, has no configured role command, creates no `tabs.json` or `supervised_session.json`, and uses the iTerm2 window-scoped create/count path. Its static diagnostic command prints the requested host data and ends at an inspection shell; it does not dispatch a role.

### Blocking findings

`.agent/orchestrate.py:L82-L86,L125`: probe confirmation is a single immediate count comparison. It has no finite readiness wait, emits neither captured pre-count nor readiness observations/final count, elapsed time, or an exact success/failure reason to the control terminal. Add a bounded polling/timeout confirmation that returns and prints those diagnostics before reporting probe success.

`tests/test_orchestrator_safety.py:L272-L279`: probe coverage calls `supervised_init()` directly but does not exercise CLI argument validation (`--tabs-probe` without `--tabs`) or the required control diagnostics/readiness result. Add subprocess/fake-runner regressions for those behaviors.

### C1.2.11 verdict

**NOT READY.** The probe is explicit, one-tab, non-role, and non-supervised, but the required bounded readiness evidence and control-terminal diagnostics are absent. No real probe was performed by this review.

## C1.2.11.1 independent review — host-probe readiness evidence

Read-only review of C1.2.11.1 only. I inspected the current authority, generated iTerm2 script, probe control output, deterministic tests, documentation, and validation evidence. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 35 tests in 4.028s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it documents explicit `--tabs-probe` requiring `--tabs`. `python .agent/orchestrate.py --dry-run` did not launch a host or role and stopped on the pre-existing ignored runtime/configuration mismatch.
- The probe now uses a bounded ten-attempt same-window count poll with `delay 0.1`; the script returns pre-count, final count, attempt count, and confirmed reason on success. The subprocess regression rejects standalone `--tabs-probe`; one-tab/no-role/no-supervised-state coverage remains present.

### Blocking finding

`.agent/orchestrate.py:L86-L95`: readiness output lacks elapsed time, despite C1.2.11.1 requiring it and `README.md:L25` claiming it. On timeout, the error has only generic recovery text and omits pre-count, final count, attempts, elapsed time, and the exact failed readiness reason. Measure elapsed time in the bounded poll, include all observations in both success and failure output, and assert surfaced control JSON/error diagnostics with a fake runner.

### C1.2.11.1 verdict

**NOT READY.** The bounded poll and argument validation close part of the prior review, but the required elapsed/failure diagnostic evidence is still missing. No real probe was performed by this review.

## C1.2.11.2 independent review — complete host-probe timing diagnostics

Read-only review of C1.2.11.2 only. I inspected the current authority, probe script and control-output path, deterministic tests, documentation, validation evidence, and working state. I did not open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 35 tests in 4.125s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it retains explicit `--tabs-probe` validation. `python .agent/orchestrate.py --dry-run` did not launch a host or role and stopped on the pre-existing ignored runtime/configuration mismatch.
- The bounded iTerm2 script now records `current date` before polling and includes `pre_count`, `final_count`, `attempts`, `elapsed_seconds`, and `reason` in both its confirmation return and unexpected-count error, with partial-tab/fresh-target recovery. Probe and full-workflow boundaries remain unchanged.

### Blocking finding

`tests/test_orchestrator_safety.py:L216-L248,L274-L281`: diagnostics coverage remains source-text-only. The fake `osascript` runner returns empty output, the probe test supplies a bare `launched.append` launcher, and failure coverage uses only `iTerm2 unavailable`. None proves that a returned success observation reaches probe control JSON or that a failed readiness diagnostic with `pre_count`, `final_count`, `attempts`, `elapsed_seconds`, and `reason` reaches the raised control error. Add fake-runner success/failure cases with representative stdout/stderr and assert the surfaced control output/error plus absence of supervised state.

### C1.2.11.2 verdict

**NOT READY.** The implementation contains the required timing fields, but the requested meaningful fake-runner regression for surfaced success and failure diagnostics is absent. No real probe was performed by this review.

## C1.2.12 independent review — native iTerm2 Python-API host probe

Read-only review of C1.2.12 only. I inspected the native bridge, controller boundary, package metadata, tests, and active documentation. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `1`; `Ran 35 tests`; one failure.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery has no tests).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; `--tabs-probe` remains explicit. `python .agent/orchestrate.py --dry-run` did not launch a host or role and stopped on the pre-existing ignored runtime/configuration mismatch.
- `pyproject.toml` declares `iterm2>=2.7`; the bridge imports it lazily and returns an isolated-venv/API-authorization recovery message when unavailable. Normal production `--tabs` now fails closed before the retired AppleScript launcher.

### Blocking findings

`tests/test_orchestrator_safety.py:L250-L254`: the controller test suite fails. `test_unsupported_tab_host_fails_closed_before_runtime_state` now receives the new full-`--tabs` fail-closed error instead of the asserted unsupported-host error. Update the regression for the intentional policy or preserve the expected validation order, then rerun the suite.

`tests/test_orchestrator_safety.py`: no test covers `launch_iterm_probe()` or `.agent/iterm_probe.py` request/response handling. Required fake coverage for missing dependency, successful opaque window/tab/session diagnostics, malformed/failed bridge responses, one-tab/no-role/no-supervised containment, and normal `--tabs` fail-closed behavior is absent.

`README.md`, `docs/controller/README.md`, and `docs/controller/VALIDATION_controller.md`: active guidance and validation still identify the AppleScript C1.2.11.2 probe, not the required native API bridge and isolated `.venv` setup. Document `python3 -m venv .venv`, activation, `python -m pip install -e .`, API authorization, and the prohibition on global/system installation or `--break-system-packages`.

### C1.2.12 verdict

**NOT READY.** The initial bridge and dependency declaration are present, but the controller suite fails and the mandatory native-bridge test and documentation/validation work is incomplete. No real native probe was performed by this review.

## C1.2.12.1 independent review — native-bridge test/setup completion

Read-only review of C1.2.12.1 only. I inspected the bridge, controller boundary, fake tests, active documentation, and validation evidence. I did not install `iterm2`, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 36 tests in 4.063s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it documents explicit `--tabs-probe` requiring `--tabs`. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- The production full-`--tabs` branch fails closed before the retired AppleScript launcher; `--tabs --tabs-probe` constructs one `host_probe` specification with no role command and returns before runtime-state creation.

### Blocking findings

`tests/test_orchestrator_safety.py:L283-L294`: the test fakes only the outer process result for `launch_iterm_probe()`; it never loads or executes `.agent/iterm_probe.py`. Required deterministic bridge cases for lazy missing `iterm2`, native success returning opaque window/tab/session identifiers, and bridge-side failure/JSON handling are therefore untested. Add fake-module/stdio tests that execute the bridge itself, while retaining the outer malformed/process-response tests.

`README.md:L7,L25` and `docs/controller/README.md:L7-L31`: active instructions still prescribe global `--user` installation, describe the superseded AppleScript/count-confirmation probe, and direct a full three-role `--tabs` smoke despite its intentional fail-closed policy. Replace the active path with the isolated `.venv` setup, iTerm2 API authorization prerequisite, one-tab native probe, and explicit prohibition on global/system installation and `--break-system-packages`; move historical AppleScript material out of executable guidance.

`docs/controller/VALIDATION_controller.md:L5-L7`: C1.2.12.1 evidence only summarizes claimed coverage and does not record the required command results, compile including `.agent/iterm_probe.py`, help/dry-run outcome, or native setup documentation check. Update it with exact, current evidence after the regressions run.

### C1.2.12.1 verdict

**NOT READY.** The controller suite is repaired and the outer process boundary is tested, but the required bridge execution coverage and retirement of active AppleScript/global-install/full-tabs guidance are not complete. No real native probe was performed by this review.

## C1.2.13 independent review — minimal native iTerm2 tab-creation probe

Read-only review of C1.2.13 only. I inspected the bridge, controller boundary, deterministic tests, active documentation, validation evidence, and working state. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 36 tests in 4.276s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it retains explicit `--tabs-probe` validation. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `.agent/iterm_probe.py` calls `async_create_tab()` without arguments, returns a precise default-profile immediate-close result for `None`, calls `tab.async_set_title(request["title"])`, and returns opaque window/tab identifiers plus elapsed time. The production full-`--tabs` branch remains fail-closed before AppleScript launch.

### Blocking findings

`tests/test_orchestrator_safety.py:L274-L294`: the bridge module is not loaded or executed with fake `iterm2` objects. Current coverage only fakes `launch_iterm_probe()`'s outer process response. Add deterministic bridge-module tests for no-argument default-profile creation/title, `None`, title failure, missing module, and malformed request, while retaining outer containment checks.

`README.md:L9-L27` and `docs/controller/README.md:L7-L31`: the added C1.2.13 paragraph is contradicted by earlier active global `--user` installation, AppleScript diagnostic-probe, and full-three-role `--tabs` smoke instructions. Replace those active paths with the isolated-venv native one-tab probe and control-terminal-JSON expectation; retain old material only as clearly historical evidence.

`docs/controller/VALIDATION_controller.md:L5-L7` and `docs/WORKING_STATE.md:L5`: no C1.2.13 validation section records the requested deterministic bridge cases, exact command outcomes, or minimal-probe limitation; the active root working state still calls C1.2.11.2 current. Update current evidence/state after completing the regressions.

### C1.2.13 verdict

**NOT READY.** The minimal native implementation and full-tabs containment are present, but required bridge execution tests and consistent active documentation/evidence are missing. No real native probe was performed by this review.

## C1.2.13.1 independent review — minimal native-probe completion

Read-only review of C1.2.13.1 only. I inspected the bridge, fake-module/stdio harness, outer process containment, active guides, validation evidence, and working state. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 37 tests in 4.078s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it states `--tabs-probe` requires `--tabs`. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `tests/test_orchestrator_safety.py:L300-L340` executes `.agent/iterm_probe.py` under fake `iterm2` and stdio. It proves no-argument default-profile creation/title, `None` immediate-close handling, title failure, lazy missing dependency, and malformed-request responses. Outer malformed/failed-process tests and one-tab/no-role/no-supervised/full-tabs-fail-closed tests remain present.
- Active root and controller guidance specify the isolated `.venv`, API authorization, one native `--tabs --tabs-probe` path, control JSON, no injected command/Codex/role/state, and intentional full-tabs refusal. AppleScript instructions are explicitly historical only.

### C1.2.13.1 verdict

**READY.** The minimal native probe is deterministically covered and remains constrained to one default-profile tab with native title assignment, no role execution, and no supervised state. Alex's fresh disposable native iTerm2 probe remains the required human gate and was not performed by this review.
