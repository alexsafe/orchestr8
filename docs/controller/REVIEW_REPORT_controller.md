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

## C1.2.14 independent review — native three-tab layout probe

Read-only review of C1.2.14 only. I inspected the native bridge, initializer boundary, fake-API tests, active documentation, validation evidence, and working state. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 39 tests in 4.301s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it documents `--tabs-layout-probe` and its `--tabs` requirement. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `.agent/iterm_probe.py` uses only no-argument `async_create_tab()` and ordered native `async_set_title()` calls for the exact Coordinator, Developer, Reviewer labels. It reports the window, three opaque tab identifiers, elapsed time, and confirmed result; every creation/title failure carries its layout step and partial-tab/fresh-target recovery.
- `tests/test_orchestrator_safety.py:L342-L397` executes the bridge under fake iTerm2/stdio; it verifies ordered default tabs/titles, `None` and exception creation failures, title failures at each step, malformed request handling, controller response validation, no runtime state, and full-tabs fail-closed containment.
- Active root/controller guides specify the activated isolated `.venv`, fresh `/private/tmp` target, layout-only command, no role/Codex/bootstrap/state side effects, and the manual human gate.

### C1.2.14 verdict

**READY.** The layout probe is a bounded native three-tab visibility experiment with deterministic containment. Alex's fresh `/private/tmp` iTerm2 layout probe remains the required human gate and was not performed by this review.

## C1.2.15 independent review — Coordinator Codex bootstrap probe

Read-only review of C1.2.15 only. I inspected the native bridge, initializer boundary, fake-API tests, active guides, validation evidence, and working state. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 41 tests in 4.307s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it lists `--tabs-coordinator-bootstrap-probe`. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- The bridge constructs one shell-quoted `codex -C <project-root> -s read-only <fixed prompt>\n` command, creates one default-profile native tab, sets the requested title, retrieves one session, and has one text-send call. The initializer keeps probe modes exclusive, creates no supervised state, and keeps ordinary full `--tabs` fail-closed.

### Blocking finding

`.agent/iterm_probe.py:L43-L45` and `tests/test_orchestrator_safety.py:L403-L443`: `async_get_app()`/`app.current_terminal_window` is outside a bootstrap-step guard. A native window-lookup exception falls to the generic outer `bootstrap probe failed before confirmation` response, rather than identifying the failed bootstrap window/preflight step; the test covers only `window_none`, not that exception. Wrap window discovery in a step-specific recovery response and add the corresponding fake exception regression. `VALIDATION_controller.md:L7` currently overstates this as covered.

### C1.2.15 verdict

**NOT READY.** Command delivery, exclusivity, and no-state containment are deterministic, but the required window exception containment and coverage are incomplete. No real Coordinator bootstrap probe was performed by this review.

## C1.2.15 independent review — active-window containment completion

Read-only review of the C1.2.15 remediation only. I inspected the bridge guard, fake-API/stdio regression, active evidence, and retained controller boundaries. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 41 tests in 4.348s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py init --help` — exit `0`; it lists the exclusive Coordinator bootstrap probe. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `.agent/iterm_probe.py:L69-L80` catches `async_get_app()` errors/`None` and `current_terminal_window` errors/`None` with precise bootstrap-preflight recovery. `tests/test_orchestrator_safety.py:L403-L450` executes those fake app/window failure paths and asserts the specific response plus no more than one send; existing exact one-command, no-state, outer-boundary, and full-tabs-fail-closed coverage remains green.

### C1.2.15 verdict

**READY.** The Coordinator bootstrap probe is now deterministically contained across active-window discovery and every later bridge step. Delivery remains explicitly unverified; Alex's fresh `/private/tmp` human UI gate is required and was not performed by this review.

## C1.2.16 independent review — staged Coordinator-first start

Read-only review of C1.2.16 only. I inspected the staged transaction, native bridge, controller tests, active documentation, and validation evidence. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 47 tests in 4.511s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py start --help` — exit `0`; it requires explicit `--tabs`. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `start_supervised()` snapshots authority and writes the Coordinator-initial session before native delivery, records tab/session IDs only after a validated observation, archives failed pre-delivery state, and its staged accept branch retains `coordinator_initial` without launching Developer or Reviewer. Fake bridge tests cover native failure steps and the fixed read-only command.

### Blocking finding

`.agent/orchestrate.py:L551-L555`: `start` calls `start_supervised()` without the controller lock used by normal dispatch at `L571-L572`. Two concurrent `orchestr8 start --tabs` processes can both pass the clean/no-session preflight, create two Coordinator tabs, and race to overwrite snapshot/session/tab metadata. Acquire and release the existing runtime lock around the entire staged-start transaction, with a deterministic concurrent/held-lock regression.

### C1.2.16 verdict

**NOT READY.** The staged single-role transaction is otherwise bounded and well-tested, but it lacks mutual exclusion at its workflow entry point. No human C1.2.16 gate was performed by this review.

## C1.2.16 independent review — start-lock completion

Read-only review of the C1.2.16 remediation only. I inspected the lock wrapper, staged transaction, held-lock regression, active documentation, and validation evidence. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 48 tests in 4.703s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py start --help` — exit `0`; it requires `--tabs`. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `.agent/orchestrate.py:L220-L225` acquires the runtime lock before the staged preflight and releases it in `finally` after the transaction. `tests/test_orchestrator_safety.py` verifies a held lock prevents state/current/history mutations and launch, and that a later safe retry succeeds with no leftover lock. Existing snapshot-before-delivery, Coordinator-only, native-failure, and staged-accept containment remains green.

### C1.2.16 verdict

**READY.** `start --tabs` is now mutually exclusive throughout its Coordinator-only staged transaction. Alex's fresh `/private/tmp` human Coordinator gate remains required and was not performed by this review.

## C1.2.16.1 independent review — terminal Coordinator-stop state

Read-only review of C1.2.16.1 only. I inspected terminalization, status/accept guards, deterministic regressions, active recovery guidance, and validation evidence. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 49 tests in 4.476s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py start --help` — exit `0`; it retains explicit `--tabs`. `python .agent/orchestrate.py --dry-run` exit `2`, stopped on the pre-existing ignored-runtime configuration mismatch and launched no host or role.
- `human_stop()` archives before removing current `supervised_session.json` and `tabs.json`; `state.status` becomes `HUMAN_REQUIRED`. `status` and repeated `accept` check that terminal state before reading any stale/missing session. The Coordinator `HUMAN_REQUIRED` regression verifies a nonzero structured first stop, terminal-first status, one history archive, and a repeated accept with no mutations.
- Normal staged Coordinator acceptance remains separate and leaves the phase pending without launching Developer or Reviewer.

### C1.2.16.1 verdict

**READY.** Terminal Coordinator stops now archive once, retain inspectable stop evidence, invalidate active runtime state, and reject repeat acceptance without mutation. No human rerun was performed by this review.

## C1.2.16.2 independent review — missing-report not-ready output

Read-only review of C1.2.16.2 only. I inspected the active accept/start paths, deterministic regressions, recovery documentation, and validation evidence. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 50 tests in 4.495s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py start --help` — exit `0`; it retains the explicit `--tabs` boundary. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed on the existing saved-configuration mismatch; no host or role launched.
- `.agent/orchestrate.py:L279-L292` validates the permitted active phase before treating an absent current-role artifact as non-terminal. It prints structured `HUMAN_REQUIRED` / `failed_or_incomplete_validation` not-ready JSON and returns `2` without writing state, session, tab, current, or history. `tests/test_orchestrator_safety.py:L494-L505` verifies the exact active-Coordinator timing sequence, byte-preserved state/session/tabs, absent history, later valid acceptance, and a malformed-artifact terminal result.
- `.agent/orchestrate.py:L269-L324` routes acceptance-side malformed output, stale/missing session, and Coordinator human-required results through `terminal_accept_stop()`, which renders the archived terminal evidence and returns `2`; the prior terminal-first/repeat-accept coverage remains present.

### Blocking findings

- `.agent/orchestrate.py:L249-L251`: staged Coordinator start/preflight and native-launch failures still call `human_stop()` directly and return its success code (`0`) without rendering the required structured terminal JSON. C1.2.16.2 explicitly includes launch/preflight failures that reach the controller in the common nonzero operator-facing terminal path. `tests/test_orchestrator_safety.py:L507-L537` retains assertions for exit `0` and has no rendering/exit-`2` regression for those failures.
- `README.md:L33` and `docs/controller/README.md:L31` describe only terminal Coordinator human-required output. They omit the newly required active-role missing-artifact not-ready response, its non-mutating property, and its “wait, then rerun accept” recovery. `docs/WORKING_STATE.md:L9` also still directs review of C1.2.16.1 rather than the active C1.2.16.2 review.
- `docs/controller/VALIDATION_controller.md:L5-L9` records only the 50-test result for C1.2.16.2, despite the task requiring exact compile, diff, help, and dry-run evidence for this change; the grouped values below belong to C1.2.16.1.

### C1.2.16.2 verdict

**NOT READY.** The live-role missing-report refusal is correctly non-mutating and later acceptance works, but terminal start/preflight failures still silently succeed and the active recovery/evidence record is incomplete. No human rerun was performed by this review.

## C1.2.16.2 independent review — terminal start rendering remediation

Read-only review of the C1.2.16.2 remediation only. I inspected the start and acceptance terminal paths, deterministic regressions, active documentation, and validation evidence. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 50 tests in 4.772s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py start --help` — exit `0`. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed on the existing saved-configuration mismatch; no host or role launched.
- `.agent/orchestrate.py:L249-L278` now directs staged start preflight/native-launch exceptions through `terminal_start_stop()`. The observed deterministic paths print terminal JSON containing `state`, `category`, `reason`, `stop_evidence`, and `recovery`, and return `2`. The existing active-role missing-artifact path remains non-mutating at `L285-L298`; malformed output and the prior terminal-first/repeat-accept behavior remain contained.

### Blocking findings

- `README.md:L33` and `docs/controller/README.md:L31` still omit the active-role missing-artifact not-ready response, its non-mutating semantics, and the required wait-then-rerun-accept recovery. `docs/WORKING_STATE.md:L9` still names C1.2.16.1 as the next review rather than C1.2.16.2.
- `docs/controller/VALIDATION_controller.md:L5-L9` still records only the C1.2.16.2 controller-suite result; the required distinct default-unittest, compile, diff, start-help, and dry-run results remain recorded under C1.2.16.1 instead.
- `tests/test_orchestrator_safety.py:L507-L537` asserts start failure exit `2` but leaves stdout uncaptured. Add deterministic assertions that both preflight and native-launch failure outputs parse as terminal JSON with all required fields, rather than relying on incidental test-run output.

### C1.2.16.2 verdict

**NOT READY.** The terminal start path is now correctly rendered and nonzero, but required recovery documentation, C1.2.16.2-specific validation evidence, and deterministic output-schema assertions are incomplete. No human rerun was performed by this review.

## C1.2.16.2 independent review — recovery/evidence remediation

Read-only review of the latest C1.2.16.2 remediation only. I inspected staged-start containment, regressions, active guides, working state, and validation evidence. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 50 tests in 4.546s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `python .agent/orchestrate.py start --help` — exit `0`. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed on the existing saved-configuration mismatch; no host or role launched.
- `README.md:L33`, `docs/WORKING_STATE.md:L5-L9`, and `docs/controller/VALIDATION_controller.md:L5-L11` now record the not-ready timing behavior, C1.2.16.2 review target, and separate complete validation block. Existing normal staged acceptance, missing-artifact non-mutation, malformed-output terminalization, and start native-launch exception containment remain present.

### Blocking findings

- `.agent/orchestrate.py:L229`: `state.json` parsing occurs before the staged-start `try` at `L230`. A malformed saved state is a preflight failure but escapes as an uncaught `JSONDecodeError`, without terminal evidence/rendering or exit `2`. Move state loading into a boundary that can safely render the structured terminal result (or provide an equivalent safe terminal path) and add the deterministic regression.
- `tests/test_orchestrator_safety.py:L507-L537`: start preflight/native-launch cases still assert only return code/history state; they do not capture, parse, and assert `state`, `category`, `reason`, `stop_evidence`, and `recovery` as the current handoff explicitly requires.
- `docs/controller/README.md:L31`: the active controller guide still omits the non-mutating missing-artifact wait/retry recovery; only `README.md` supplies it. Add the same explicit operational guidance to the controller guide.

### C1.2.16.2 verdict

**NOT READY.** The root recovery/evidence updates are in place, but malformed saved state bypasses the staged-start terminal contract and required deterministic terminal-output coverage remains incomplete. No human rerun was performed by this review.

## C1.2.17 independent review — quality gates only

Read-only review of C1.2.17 only. I inspected the task-scoped files, incremental file list, inherited-assets path, and existing runtime diff. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 50 tests in 4.957s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- The incremental modified-file list contains no `.agent/roles/developer.md`, `.agent/roles/reviewer.md`, or `.agent/schemas/developer.json`; `docs/controller/README.md` and `tests/test_orchestrator_safety.py` contain only pre-existing C1.2.14–C1.2.16-era changes, not the required C1.2.17 table or report-format coverage.
- No C1.2.17 runtime or approval-policy edits were introduced. C1.2.16.2 remains independently **NOT READY** and no changed-task behavior was selected.

### Blocking findings

- `docs/controller/README.md`: missing the required clearly separated design-only future state-machine table, its non-current-behavior warning, stable `Q01`–`Q20` identifiers, and unchanged `Q14` undecided C1.2.18 row.
- `.agent/roles/developer.md`, `.agent/roles/reviewer.md`, and `.agent/schemas/developer.json`: missing the mandated Developer self-check, independent Reviewer checklist, and required string-array `self_check` report field.
- `tests/test_orchestrator_safety.py`: missing inheritance assertions and representative validator coverage for valid `self_check`, missing/wrong/non-string `self_check`, extra fields, and retained Reviewer report usability. No C1.2.17 Developer evidence/self-check was recorded.

### C1.2.17 verdict

**NOT READY.** The handoff and deferred-scope documentation exist, but the authorized quality-gates implementation and its deterministic evidence were not delivered. C1.2.16.2 remains separately NOT READY.

## C1.2.17 independent review — quality-gates implementation

Read-only review of the C1.2.17 implementation only. I inspected the five authorized implementation files, initialization inheritance, unchanged schema validator use, role fixtures, current runtime-state contents, and the pre-existing C1.2.16 runtime diff. I did not install dependencies, open iTerm2, invoke Codex, use a network service, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 51 tests in 4.827s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`.
- `docs/controller/README.md:L132-L161` supplies a clearly separated, design-only table with stable `Q01`–`Q20` rows, non-current-behavior caveat, preserved `Q14` as `UNDECIDED — C1.2.18`, and explicit recovery-design limitations.
- `.agent/roles/developer.md:L15-L27`, `.agent/roles/reviewer.md:L15-L19`, and `.agent/schemas/developer.json` provide matching self-check/review requirements and a required string-array `self_check` while retaining `additionalProperties: false` and existing statuses.
- `tests/test_orchestrator_safety.py:L675-L695` initializes a project, verifies inherited table/warning/undecided row and both role checklists, accepts a complete Developer report with `self_check`, rejects missing/wrong/non-string/extra-field variants through the unchanged validator, and confirms the Reviewer format remains usable. Existing fake Developer fixtures include `self_check`.
- No incremental C1.2.17 changes appear in runtime/controller/approval files; the tracked runtime changes are the pre-existing C1.2.14–C1.2.16 work. The table does not claim current behavior, and C1.2.16.2 remains **NOT READY**.

### Blocking finding

`.agent/runtime/current` contains only prior `human_stop.json` evidence and no C1.2.17 `.developer.json`/Developer report. The required exact validation results, per-criterion self-check, and limitations were not recorded in the owned Developer report. The handoff simultaneously forbids role dispatch and runtime/current/history edits, so this must be resolved explicitly within the authorized reporting mechanism before the quality-gates package can be accepted; this review does not create or modify runtime evidence.

### C1.2.17 verdict

**NOT READY.** The bounded implementation and deterministic coverage are complete, but the required Developer self-check/validation/limitations evidence is absent. C1.2.16.2 remains separately NOT READY.

## C1.2.17 independent review — authorized chat completion report

The user explicitly authorized the Developer's chat completion report as the reporting mechanism for this manual-maintenance task. I verified that report against the scoped diff and independently observed validation results. No runtime artifact was created, no role was dispatched, and no implementation file was changed by this review.

Independent evidence:

- The task-scoped diff is exactly the five authorized files: `docs/controller/README.md`, `.agent/roles/developer.md`, `.agent/roles/reviewer.md`, `.agent/schemas/developer.json`, and `tests/test_orchestrator_safety.py` (367 additions, 10 deletions).
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 51 tests in 4.827s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (explicitly not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` — exit `0`.
- `git diff --check` — exit `0`, rechecked after the chat report.
- The report accurately describes the design-only matrix, retained `Q14` undecided C1.2.18 behavior, report-schema coverage, and deferred runtime hardening. The pre-existing C1.2.14–C1.2.16 runtime changes are not incremental C1.2.17 work.

### C1.2.17 verdict

**READY.** The authorized chat report supplies the required Developer self-check, validation results, and limitations; the bounded quality-gates implementation and deterministic inheritance/report-format coverage are complete. C1.2.16.2 remains separately **NOT READY** and is not affected by this verdict.

## C1.2.18 independent review — Coordinator-stage safety

Read-only review of the latest C1.2.18 increment only. I inspected the Coordinator start/accept/inspection paths, current matrix/guides/evidence, and deterministic tests. I did not inspect or alter source-checkout runtime artifacts, invoke iTerm2/Codex, use a network service, install dependencies, commit, or run a workflow role.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 52 tests in 4.521s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py start --help` — exit `0`.
- `.agent/orchestrate.py:L308-L310` and `tests/test_orchestrator_safety.py:L478-L489` correctly implement the approved changed-task refusal: exit `2`, `outcome: refusal`, and byte-preserved current/state/authority with no history archive.

### Blocking findings

- `.agent/orchestrate.py:L229`, `L286`, `L338`, and `L352`: saved-state loading remains outside any safe structural-validation boundary. Missing, unreadable, malformed, non-object, or wrong-typed state can raise or be trusted without the required non-mutating structured refusal; no corresponding tests exist.
- `.agent/orchestrate.py:L220-L251`: held-lock acquisition raises raw rather than structured refusal, while dirty/HEAD-less/pre-session/duplicate starts still invoke `terminal_start_stop()` and archive/terminalize. These must preserve existing state/current/history and never invalidate another run.
- `.agent/orchestrate.py:L293-L294`: wrong-role acceptance calls `terminal_accept_stop()` and terminalizes a healthy identified run. It must be a non-mutating permitted-role refusal.
- `.agent/orchestrate.py:L249-L251`: uncertain native delivery after preparation is treated as a terminal archive rather than preserved preparation plus human-inspection/fresh-run refusal.
- `.agent/orchestrate.py:L295-L333`: unreadable output can escape as `OSError`; terminal and nonterminal JSON lack a common stable outcome discriminator (`not_ready_result()` has none; `terminal_stop_result()` has none). Required malformed/unreadable evidence distinctions and output-contract tests are absent.
- `docs/controller/README.md:L153`, active guides, and `docs/controller/VALIDATION_controller.md` still describe Q14 as undecided and contain no C1.2.18 recovery/validation evidence. No C1.2.18 Developer chat completion report was supplied.

### C1.2.18 verdict

**NOT READY.** Changed-task refusal is correctly non-mutating, but the approved corrupt-state, non-mutating start/wrong-role, interrupted-launch, structured-output, persistence, documentation, and test coverage work remains incomplete. C1.2.16.2 therefore remains **NOT READY**.

## C1.2.18 independent re-review — completed Coordinator-stage remediation

Manual-maintenance re-review of C1.2.18 against `docs/NEXT_PROMPT.md` and every prior blocking finding. I inspected no source-checkout runtime artifacts, created none, and did not invoke a supervised session, iTerm2, Codex, network service, dependency installation, commit, or worktree.

Independent evidence:

- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 59 tests in 4.960s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py start --help` — exit `0`.
- `.agent/orchestrate.py:L220-L290` now provides structured lock/preflight/state refusals, preserves corrupt state bytes, rejects duplicate/baseline/authority starts before mutation, retains uncertain-delivery preparation without archive/relaunch, and releases only its own lock identity.
- `.agent/orchestrate.py:L332-L467` serializes acceptance, refuses wrong-role/missing-artifact/changed-task paths without mutation, distinguishes trusted active-run inconsistency for terminalization, supplies `outcome` on refusal/terminal/success, and makes terminal inspection observational.
- `.agent/orchestrate.py:L308-L319` handles collision and persistence failure as disclosed refusals rather than false terminal success. The tests cover corrupt-state variants, isolated CLI JSON refusal, held/replaced locks, duplicate start/wrong role, interrupted delivery, persistence conflicts, unreadable/schema-invalid active artifacts, repeated terminal behavior, and inherited Q14 policy.
- Root/controller recovery guides, Q14, and C1.2.18 validation evidence now document fresh-authorized-run reuse conditions, interrupted delivery, and the remaining human Coordinator smoke gate. No Developer/Reviewer launch or approval-policy expansion was added.

### Blocking finding

`.agent/orchestrate.py:L371-L379`: a symlinked `.coordinator.json` passes `output.is_file()` because that predicate follows symlinks. The controller can therefore validate and accept data outside the identified current run, despite the branch claiming it rejects non-regular evidence. Reject symlinks using `lstat()`/file-mode validation before reading, terminalize only the identified run as invalid evidence, and add the deterministic regression.

The Developer chat completion report referenced by the handoff was not included in the visible review conversation. Its recorded command results match this independent run, but its criterion-by-criterion self-check and stated limitations could not be verified directly.

### C1.2.18 verdict

**NOT READY.** All previous C1.2.16.2 blocking groups are closed except active role-artifact containment: symlinked Coordinator evidence can escape the current run. The human Coordinator smoke gate remains unperformed; Developer/Reviewer launching remains out of scope.

## C1.2.18 independent re-review — Coordinator evidence symlink containment

Manual-maintenance review of the final C1.2.18 remediation. I inspected no source-checkout runtime artifact and created none. I did not invoke a supervised session, iTerm2, Codex, network service, commit, or worktree.

Independent evidence:

- `.agent/orchestrate.py:L371-L385` uses `lstat()` to reject a Coordinator-output symlink before validation, then opens a regular artifact with `O_NOFOLLOW` and verifies the opened descriptor is regular.
- `.agent/orchestrate.py:L657-L661` excludes a symlinked `.coordinator.json` from history, so terminalization cannot copy an external target.
- `tests/test_orchestrator_safety.py:L578-L606` covers both an existing external target and a dangling symlink. Each case asserts structured terminal JSON, exit `2`, no successful acceptance or later-role launch, unchanged external content, and no external-content ingestion into history. Existing regular-file acceptance coverage remains at `L475-L480`.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 60 tests in 5.000s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py start --help` — exit `0`.
- The prior C1.2.16.2 blockers are now closed in implementation and deterministic coverage: state/refusal boundaries, interrupted delivery, output contracts, persistence, documentation, and Coordinator evidence containment. No Developer/Reviewer staged launch or approval-policy change was introduced.

### Remaining blocker

The required Developer completion report was not supplied in the visible chat. Therefore its exact claimed results, criterion-by-criterion self-check, relevant Q-row mapping, and stated limitations cannot be independently verified. This manual-maintenance handoff explicitly designates that chat report as required evidence.

### C1.2.18 verdict

**NOT READY.** The final implementation and deterministic regression are satisfactory, but the mandated Developer chat completion report is absent. The human Coordinator smoke gate also remains unperformed; Developer/Reviewer launching remains out of scope.

## C1.2.19 independent review — staged Developer/Reviewer launch

Manual-maintenance review against `docs/NEXT_PROMPT.md` and the supplied Developer completion report. I inspected no source-checkout runtime artifact and created none. I did not invoke a real role, iTerm2, Codex, network service, commit, or worktree.

Independent evidence:

- `.agent/orchestrate.py:L322-L367` implements explicit, lock-protected `launch developer` and `launch reviewer` transactions with recorded-window delivery, persisted preparation, no retry, and confirmed tab/session identity before activation.
- `.agent/orchestrate.py:L342-L351` rechecks the clean Coordinator baseline for Developer and the frozen Developer report/artifact/project identity for Reviewer. `.agent/orchestrate.py:L502-L536` freezes Developer evidence before Reviewer launch and archives an approved review once before returning the `coordinate latest` cue.
- `.agent/orchestrate.py:L463-L475` applies lstat/no-follow regular-file handling to all three role artifacts; `.agent/orchestrate.py:L803-L807` prevents symlink report ingestion during archive.
- `tests/test_orchestrator_safety.py:L490-L533` exercises the full fake Coordinator → Developer → Reviewer sequence, capabilities, explicit human cues, frozen review identity, completion/archive, and repeat-command containment. `L545-L661` covers baseline/snapshot/diff drift, locks, wrong order, stale outputs, interrupted delivery, non-approved outcomes, and later-role symlinks. `L885-L914` executes the native bridge through fake iTerm2 APIs for both staged roles.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 70 tests in 9.565s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, and `python .agent/orchestrate.py launch --help` — exit `0`.

### Blocking finding

- `docs/controller/README.md:L39`: states that `--tabs` starts exactly three interactive role sessions and gives the control tab `accept <role>` workflow control. Current C1.2.19 behavior starts only Coordinator; Developer and Reviewer require explicit `launch` commands after their preceding acceptance. Update this active guide to the documented staged operator sequence so operators cannot unintentionally create three tabs or follow an obsolete control model.

### C1.2.19 verdict

**NOT READY.** The staged implementation, deterministic coverage, and supplied Developer report are otherwise satisfactory, but the active controller guide contradicts the implemented and required launch model. The human full-cycle gate remains unperformed; Reviewer report writing in a live read-only sandbox remains unproven.

## C1.2.19 independent re-review — active-guide correction

The previously blocking guide contradiction is resolved. I inspected the documentation-only correction; no source-checkout runtime artifact was inspected or created, and no real role was launched.

- `docs/controller/README.md:L31-L47` now documents one Coordinator tab from `start --tabs`, the explicit Coordinator → `launch developer` → `launch reviewer` operator sequence, all human phrases, no automatic handoff, recovery, and the read-only Reviewer limitation.
- `docs/controller/README.md:L49-L55` labels the three-tab workflow as historical rather than current operation.
- `README.md:L23-L49` matches this active sequence and correctly says `init --tabs` without a probe fails closed.
- `git diff --check` — exit `0`. The prior independent C1.2.19 validation remains passing: `tests.test_orchestrator_safety` ran 70 tests with exit `0`; compilation and both help commands exited `0`.

### C1.2.19 verdict

**READY.** The explicit staged-cycle implementation, deterministic evidence, supplied Developer report, and current operator documentation meet the C1.2.19 handoff. This permits one authorized human full-cycle gate only; it does not claim that gate passed or that the MVP is complete. Reviewer report writing in a live read-only sandbox remains unproven.

## MVP report-writing correction — independent review

Manual-maintenance review of the workspace-write/report-ownership correction in `docs/NEXT_PROMPT.md`. I inspected no source-checkout runtime artifact and created none. I did not invoke a real role, iTerm2, Codex, network service, commit, or worktree.

Independent evidence:

- `.agent/orchestrate.py:L46-L51`, `L286-L302`, and `L396-L441` select `workspace-write` only for production interactive sessions, while `load_config()` retains `write_capable` as Developer-only code-change authority.
- `.agent/orchestrate.py:L311-L385`, `L504-L564`, and `L606-L640` protect project, authority, approval, runtime, and frozen-review evidence at handoffs. Coordinator/Reviewer changes outside their owned reports refuse progression; excluded project paths contribute only an aggregate fingerprint.
- `.agent/orchestrate.py:L352-L363` and `L692-L715` isolate the post-completion Coordinator summary from the frozen archive and block it from enabling another cycle.
- `.agent/roles/coordinator.md:L7-L21` and `.agent/roles/reviewer.md:L7-L23` define exact owned reports and prohibit code, authority, approval, state, history, published-report, and cross-role-evidence writes. Root/controller guides describe the same policy and limitations.
- `tests/test_orchestrator_safety.py:L664-L750` covers configured paths, production payloads, report-only success, protected-change refusal, Markdown handoffs, and final-summary isolation; inherited safety regressions remain present.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 73 tests in 16.038s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, and `python .agent/orchestrate.py launch --help` — exit `0`.

### Remaining blocker

The required Developer completion report is not present in the visible chat. Its changed-file accounting, criterion-by-criterion self-check, and stated live-test limitations therefore cannot be independently verified through the handoff's authorized reporting mechanism.

### Verdict

**NOT READY.** The implementation and deterministic evidence are satisfactory, but the required Developer chat completion report is missing. A READY verdict would permit only the specified fresh, human-gated single-cycle communication proof; it would not claim that proof passed.

## MVP report-writing correction — authorized Developer chat report

The Developer completion report was supplied in chat and reconciled with the independent review. Its changed-file list matches the scoped controller, bridge, role-instruction, test, guide, and validation work. Its self-check accurately describes production workspace-write report delivery, retained Developer-only `write_capable` code authority, protected handoff evidence, aggregate excluded-path fingerprinting, Markdown publication, final-summary isolation, and retained safety regressions.

The report's validation results match the independent run: `tests.test_orchestrator_safety` completed 73 tests with exit `0`; explicit unittest discovery completed 0 tests with exit `0`; compilation, `git diff --check`, and both help commands exited `0`. Its limitations are accurate: workspace-write is not hostile-agent isolation or rollback, and no live role or human smoke test ran.

### Verdict

**READY.** The authorized chat report closes the reporting-evidence gap. The report-writing correction is ready for the single fresh, human-gated communication proof specified in `docs/NEXT_PROMPT.md`; it does not claim that proof or the full MVP has passed.

## Single-cycle app-sent role triggers — independent review

Manual-maintenance review against `docs/NEXT_PROMPT.md` and the supplied Developer chat report. I inspected no source-checkout runtime artifact and created none. I did not invoke a real role, iTerm2, Codex, network service, commit, or worktree.

Independent evidence:

- `.agent/orchestrate.py:L462-L536` requires human `--ready`, validates the eligible staged phase and preserved evidence, records a unique destination/payload-bound attempt before delivery, and refuses all duplicate attempts. Delivery failure or confirmation-persistence failure remains uncertain and cannot resend automatically.
- `.agent/orchestrate.py:L487-L507` creates fixed phrase-first payloads containing only iteration, snapshot, archive, and report paths; it does not inject report prose as instructions. Triggering neither accepts a report nor advances the workflow.
- `.agent/iterm_probe.py:L183-L201` resolves the recorded window, tab, and session together; refuses absent/exited destinations; creates no tab; and sends exactly one submitted payload with broadcast suppressed.
- `tests/test_orchestrator_safety.py:L780-L896` covers all three triggers, final-summary routing, preflight refusal, persistence/send/crash containment, review-identity drift, terminal containment, immutable history, and no duplicate send. `L1123-L1164` executes bridge handling with fake native APIs, including exact destination binding, known-exited rejection, Unicode/space payload transport, and suppressed broadcast.
- The Developer report accurately identifies the human-readiness and CLI-exit race limitations, retains explicit start/launch/accept gates, and does not claim live validation or multi-cycle automation.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 82 tests in 21.431s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, `python .agent/orchestrate.py launch --help`, and `python .agent/orchestrate.py trigger --help` — exit `0`.

### Verdict

**READY.** The bounded, single-cycle trigger capability meets the handoff. This permits only the separately authorized fresh live trigger smoke; transport confirmation does not prove a completed Codex turn, unattended progression and multiple cycles remain unimplemented.

## Single-cycle trigger submission correction — independent review

Read-only review of the two-step typed-input correction and supplied Developer summary. No source-checkout runtime artifact was inspected or created; no real role, iTerm2, Codex, network service, commit, or worktree was used.

Independent evidence:

- `.agent/iterm_probe.py:L183-L207` sends the fixed prompt then a separate `"\\r"` to the same exact window/tab/session, suppressing broadcast on both calls. Missing/exited targets, job changes between calls, and either send failure produce an unsuccessful transport result without any fallback.
- `.agent/orchestrate.py:L177-L186` and `L522-L534` require explicit carriage-return confirmation. Any failed text, return, or confirmation persistence is an uncertain, non-retryable attempt.
- `.agent/orchestrate.py:L766-L776` and `L823-L829` report transport separately from role-output observation: confirmed transport can coexist with `not_observed`; an existing artifact is `present_unvalidated` until explicit acceptance.
- `tests/test_orchestrator_safety.py:L872-L895` verifies ordered prompt/return delivery, failure on the return call, uncertainty, and no resend. `L1153-L1201` executes native fake-API destination, job, broadcast, Unicode, and two-call behavior.
- The Developer summary correctly limits the claim: `--ready` is human confirmation, the input API does not prove Codex submitted/completed the turn, and CLI-exit races, unattended progression, and multiple cycles remain unresolved.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 83 tests in 21.387s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, `python .agent/orchestrate.py launch --help`, and `python .agent/orchestrate.py trigger --help` — exit `0`.

### Verdict

**READY.** The transport correction meets its bounded trigger contract and preserves at-most-one automatic attempt. A fresh authorized live trigger smoke remains necessary to establish whether separate typed carriage return submits a Codex prompt; this verdict does not claim that result.

## Disposable input-submission smoke preparation — independent review

Read-only review of the diagnostic instrumentation and procedure. No live session, role, smoke target, source runtime artifact, network service, commit, or worktree was used.

Independent evidence:

- `.agent/iterm_probe.py:L183-L223` records exact destination IDs and sequential per-send monotonic start/end times and iTerm status. Missing status, non-OK status, or either send failure is returned as unsuccessful transport; it does not retry.
- The installed iTerm Python API exposes `rpc.async_send_text(connection, session, text, suppress_broadcast)` and the session wrapper delegates to it, matching the bridge's direct status-aware RPC use.
- `tests/test_orchestrator_safety.py:L1175-L1221` exercises success, missing/non-OK statuses, ordered sends, partial failure, exact destination binding, and broadcast suppression. The existing controller tests retain no-resend behavior.
- [SUBMISSION_SMOKE.md](SUBMISSION_SMOKE.md) specifies one separately authorized disposable read-only session, explicit destination discovery, a unique marker, one bridge invocation, manual observation criteria, no manual Enter/retry, and removal only when the directory is empty. It does not start a controller cycle or mutate existing smoke evidence.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 83 tests in 21.666s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, `python .agent/orchestrate.py launch --help`, and `python .agent/orchestrate.py trigger --help` — exit `0`.

### Verdict

**READY.** The disposable diagnostic preparation is safe and evidence-oriented. It authorizes no live action by itself: two `OK` send statuses acknowledge iTerm requests only; observed processing and the unique marker remain the required human evidence for submission and completion.

## Disposable input-submission smoke refinement — independent review

Reviewed the latest bridge instrumentation and disposable procedure only. No live iTerm, Codex, role, source-checkout runtime artifact, existing smoke target, network action, commit, or worktree was used.

Independent evidence:

- `.agent/iterm_probe.py:L184-L230` records exact destination IDs, one entry per text/Return RPC with monotonic start/end timestamps and native status, then waits one second and revalidates the same destination and foreground job before Return. Missing/non-OK status, wait interruption, destination disappearance, job drift, or either send failure returns unsuccessful/uncertain transport and does not retry.
- `tests/test_orchestrator_safety.py:L1177-L1229` exercises successful ordered text/settle/Return delivery, missing/non-OK status, text/Return failure, wait interruption, destination loss, job drift, exact window/tab/session binding, and broadcast suppression. The existing controller coverage continues to enforce persisted pre-attempt evidence and no automatic resend.
- [SUBMISSION_SMOKE.md](SUBMISSION_SMOKE.md) limits any future live action to one separately authorized, read-only, disposable session; requires unique-marker and visible-processing evidence; forbids manual Enter/retry; and preserves unexpected directory contents and all existing runtime/smoke evidence.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 83 tests in 22.911s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, `python .agent/orchestrate.py launch --help`, and `python .agent/orchestrate.py trigger --help` — exit `0`.

### Verdict

**READY.** The refinement is appropriately bounded and preserves no-retry semantics. The one-second delay is explicitly a diagnostic candidate, not proof of Codex readiness; a separately authorized live smoke with human observation remains required to establish submission or completion.

## Operator labels and bridge-preflight — independent review

Reviewed the supplied Developer report and current implementation in manual-maintenance mode. No real role, iTerm tab, source-checkout runtime artifact, existing smoke target, network action, commit, or worktree was used.

Independent evidence:

- `.agent/orchestrate.py:L178-L197` checks `import iterm2` with the same interpreter that invokes the bridge, before any start/launch preparation write or tab creation. A missing dependency is a structured refusal; it is not a partial launch.
- `.agent/iterm_probe.py:L184-L201` resolves the recorded window, tab, and session together before `async_set_title`. The label bridge returns only that exact destination and title, while `.agent/orchestrate.py:L186-L197` treats all cosmetic failures as separately reported status rather than workflow authority.
- `.agent/orchestrate.py:L558-L560` and `L718-L762` update labels only after the associated persisted acceptance/delivery outcome. A label failure cannot undo acceptance, advance a stage, or cause resend; `status` remains non-mutating.
- `tests/test_orchestrator_safety.py:L1235-L1302` covers exact-destination Unicode label routing, dependency preflight before writes, accepted/uncertain label failure containment, and no duplicate delivery. Initial phrase labels are asserted at `L1253-L1256`.
- Active root and controller guides distinguish current labels from historical smoke instructions, describe lag/failure semantics, and direct source-checkout helpers through the source virtual environment.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 88 tests in 24.225s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py start --help`, `python .agent/orchestrate.py launch --help`, and `python .agent/orchestrate.py trigger --help` — exit `0`.

### Verdict

**READY.** The bounded label and dependency-preflight change meets its contract without weakening stage, evidence, or at-most-one-delivery safeguards. A separately authorized live label observation remains required; labels are cosmetic and do not prove role processing.

## Approval recording and correction rollover checkpoint — independent review

Reviewed only the approval-recording and approved-`CHANGES_REQUIRED` correction-rollover checkpoint. Next-task rollover, run-budget policy, and complete two-cycle behavior are explicitly outside this verdict. No live role, iTerm tab, source runtime artifact, smoke target, network action, commit, or worktree was used.

Independent evidence:

- `.agent/orchestrate.py:L415-L466` derives the proposal identity from protected completed-iteration evidence, archive state/review, tab evidence, and regular-file summary/proposal content. `approve_proposal` requires exact run ID, iteration, and proposal digest; exclusive no-follow creation prevents overwrite or symlink ingestion, records no dispatch, authority publication, or state transition, and refreshes the completion guard.
- `.agent/orchestrate.py:L477-L530` rederives and compares the complete approval record, requires actionable `CHANGES_REQUIRED`, validates the completed archive, accepted Coordinator evidence, review/project/excluded-path identity, and recorded tab identities. It carries the same task ID into a new attempt while creating fresh report-slot names.
- The original completed attempt remains immutable at `history/<iteration>`; the pre-rollover coordination evidence is renamed into a distinct `history/<iteration>-coordination` target. Exclusive rollover markers and target checks refuse duplicates. A persistence failure leaves evidence for inspection, blocks retry, and cannot authorize a Developer trigger.
- `tests/test_orchestrator_safety.py:L594-L717` covers absent/symlink/stale/changed/wrong/duplicate proposal approval, predecessor drift, no approval dispatch, successful no-dispatch correction rollover, project drift, partial persistence, duplicate refusal, fresh report paths, and reuse of the recorded Developer/Reviewer destinations.
- `python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 97 tests in 32.370s`; `OK`.
- `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (not coverage).
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, `python .agent/orchestrate.py proposal --help`, `python .agent/orchestrate.py approve-next --help`, and `python .agent/orchestrate.py rollover-correction --help` — exit `0`.

### Verdict

**READY — checkpoint only.** Approval binding, carry-forward checks, archive preservation, partial-persistence containment, duplicate protection, and recorded-session reuse meet the requested checkpoint. This does not declare next-task rollover, budgets, an integrated two-cycle workflow, or any live behavior ready.
