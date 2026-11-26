# Controller Workflow — Validation

## Human app-sent single-cycle proof — PASSED (2026-11-15)

Evidence: human-pasted command outputs and role transcripts, not an independent filesystem audit. Target `/private/tmp/orchestr8-cycle-6m6wfC`; logs `/private/tmp/orchestr8-cycle-logs-CEXYTT`; iteration 001. Task SHA-256 `f5f531cbeb6b8433eee95a38b397ae6484503e88311a4f1c5ceba7521059f0a2`.

- Coordinator start succeeded, exit 0. Developer trigger succeeded, exit 0; Developer reported creation and validation of the 27-byte marker and owned report.
- Reviewer trigger succeeded, exit 0. Human explicitly observed review without manual prompt or Enter. Reviewer returned APPROVED, no findings, with independent byte/scope checks.
- Original Coordinator received the app-sent `coordinate latest` context and produced the separate final summary. Summary references published Developer/Reviewer reports, approved review and no next task.
- Final status succeeded, exit 0: COMPLETED_COORDINATOR_REVIEW, all three roles started, trigger output present. Final Git status showed only `?? SMOKE_MARKER.txt`.
- Final trigger/acceptance command logs were not pasted individually; the supplied final status, trigger text and Coordinator transcript establish progression to final coordination. The transcript includes a compound read command exiting 1; its exact failing component is unknown. Subsequent summary writing succeeded; do not describe every role command as passing.
- Final status explicitly labels the summary `present_unvalidated`. This record establishes observed single-cycle communication, not independent semantic validation of that summary, an archive rehash, absence of every prohibited historical action, or unattended/multiple-cycle behavior.

Result: the human-gated single-cycle app-sent communication proof passed on the supplied evidence. Preserve target/logs and prior failed attempts. This does not establish universal timing reliability. Earlier focused submission evidence is `/private/tmp/orchestr8-delay-is4vo5ro/result.json`, with an observed exact-marker response after the one-second settling interval.


## Human single-cycle communication proof — PASSED

Evidence source: the human's pasted CLI outputs and role responses in this coordination conversation; no independent filesystem inspection of the smoke target was performed for this record. Target: `/private/tmp/orchestr8-mvp-LCIjPe`, iteration `001`.

- Coordinator returned CONTINUE and reported its owned artifact written. Control acceptance returned success/exit 0 with `next_action: launch developer`.
- Developer launch returned success/exit 0 and native window/tab/session identifiers. Its tab received configured snapshot/report paths and waited for `do next prompt`.
- Developer reported DONE, marker creation and exact 27-byte validation including newline. Control acceptance returned success/exit 0 with `next_action: launch reviewer`.
- Reviewer reported APPROVED with no findings, independent byte/scope verification and matching Developer/report identity. Control acceptance returned success/exit 0, all three roles started, `phase: coordinator_review`, and history path `/private/tmp/orchestr8-mvp-LCIjPe/.agent/runtime/history/001`. The separate Reviewer launch output was not pasted; the completed review and acceptance establish that the workflow reached Reviewer.
- Final control status returned `state: COMPLETED_COORDINATOR_REVIEW`, all three roles started, and `next_action: inspect coordinator summary; no new cycle is authorized`.
- The pasted `coordinator_summary.md` records iteration 001 completion, task snapshot SHA-256 `098b28ed7951e9c275d8a39a23312bd63f304f774f3e740dd743d8fb77172168`, the published Developer/Reviewer reports and APPROVED verdict, with no next task proposed. Coordinator also returned COMPLETE in its conversation.
- Final `git status --short` printed only `?? SMOKE_MARKER.txt`. Runtime artifacts are ignored; this output alone is not a full runtime-integrity audit. Controller reported the archive; this record does not independently rehash it.

Result: the fresh manually gated single-cycle communication proof passed. Actual Coordinator/Developer/Reviewer report production, controller acceptance, Markdown handoffs and final Coordinator summary were observed. No manual JSON copying or permission bypass was reported. Preserve the target as evidence; do not restart or clean it merely to continue development.

Not established: controller-sent conversational triggers, unattended progression, repeated cycles, exhaustive sensitive-action approval policy, or hostile-agent isolation. Next is a bounded one-cycle app-sent-trigger task, followed by its own independent review and live proof. Historical validation blocks below describe their original evidence and limitations, not current milestone status.


## MVP report-writing correction — Developer validation

- `python -m unittest tests.test_orchestrator_safety`: exit 0; 73 deterministic tests passed.
- `python -m unittest`: exit 0; 0 tests discovered; not coverage.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`: exit 0.
- `git diff --check`: exit 0.
- `python .agent/orchestrate.py start --help` and `python .agent/orchestrate.py launch --help`: each exit 0.

Fake role and native-bridge tests cover production workspace-write payloads, Developer-only code authority, protected project/runtime evidence, an aggregate fingerprint of manifest-excluded paths, published Markdown handoffs and a separate final Coordinator summary. The checks detect unexpected changes at handoffs; they do not provide hostile-agent isolation or rollback. No real role ran. Independent review and a human single-cycle smoke gate remain required.


## C1.2.19 Developer validation — manual maintenance

- `python -m unittest tests.test_orchestrator_safety`: exit 0; 70 deterministic tests passed.
- `python -m unittest`: exit 0; 0 tests discovered; this is not coverage.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`: exit 0.
- `git diff --check`: exit 0.
- `python .agent/orchestrate.py start --help`: exit 0.
- `python .agent/orchestrate.py launch --help`: exit 0.

The suite exercises the explicit staged cycle with fake delivery, recorded-window bridge behavior, role capability settings, baseline and review-diff drift, refusal and stop paths, and exactly-once archive. Independent review and a human full-cycle smoke gate remain required. Reviewer is read-only; its ability to write the owned report has not been demonstrated in a live sandbox.


## C1.2.18 human Coordinator smoke — acceptance passed; status discrepancy

The human explicitly chose to proceed before the remaining Developer-chat-report review gate closed. These observations do not change the independent review verdict.

Target: `/private/tmp/orchestr8-c1218-QudVrf`. Initialization succeeded. The human supplied a Coordinator-only durable task and started the smoke workflow. The visible Coordinator read its instructions, waited for the brief, and subsequently reported `CONTINUE` with null proposal/human fields and stated that it wrote its artifact.

The pasted control-terminal output confirms `accept coordinator` returned `outcome: success`, exit `0`, and `Developer/Reviewer staged launch is not implemented; no additional role was launched`, with next action `await a separately authorized next stage`.

The following `status` returned `outcome: success` and `phase: coordinator_initial`, but incorrectly repeated `coordinator: Start project: <human initial brief>`. It also listed all configured role labels; this is not evidence of Developer/Reviewer tabs being launched. Record this as an observed post-acceptance status/next-action discrepancy for correction and deterministic regression. Do not follow that stale brief cue.

The pre-brief not-ready/exit-2 check was requested, but its output was not supplied; do not claim that case passed in the human smoke. No full supervised cycle was performed. Preserve this target and its evidence. Next coordination work is a bounded C1.2.19 staged-launch proposal including accurate post-acceptance status; the final C1.2.18 reporting verdict remains separate.

## C1.2.18 Developer validation — manual maintenance

- `python -m unittest tests.test_orchestrator_safety`: exit 0; 59 deterministic tests passed.
- `python -m unittest`: exit 0; 0 tests discovered; this is not coverage.
- `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`: exit 0.
- `git diff --check`: exit 0.
- `python .agent/orchestrate.py start --help`: exit 0.

The explicit test module includes isolated CLI state refusals, fake Coordinator delivery, refusal and terminal persistence checks. No source runtime, actual iTerm2 or Codex role was used. Independent review remains required, followed by a human Coordinator smoke gate; Developer/Reviewer staged launching remains deferred.


Historical C1.2.1–C1.2.5 records below retain the superseded Terminal.app investigation for auditability only. C1.2.6 makes iTerm2 the sole supported automatic-tab host.

## C1.2.16.2 missing-report not-ready developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 50 tests in 4.763s`; `OK`. The active Coordinator missing-report regression returns structured nonzero not-ready output without mutating session, tabs, state, or history; a later valid report follows the normal staged path. Malformed output remains a visible nonzero terminal stop, while prior terminal/repeat-accept coverage remains intact.

`python -m unittest` — exit `0`; `Ran 0 tests`; `OK`. `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py start --help` — exit `0`. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed with `saved state belongs to a different controller configuration`; no host or role launched.

## C1.2.16.1 terminal Coordinator-stop developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 49 tests in 4.559s`; `OK`. The deterministic regression starts the staged Coordinator, supplies schema-valid `HUMAN_REQUIRED`/`scope_expansion`, asserts a first nonzero structured terminal acceptance, terminal-first status without a role phrase, archived-once immutable evidence, removed current session/tab state, and a repeat acceptance that leaves history, state, and current evidence unchanged. Existing normal staged Coordinator acceptance remains covered.

`python -m unittest` — exit `0`; `Ran 0 tests`; `OK`. `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py start --help` — exit `0`. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed with `saved state belongs to a different controller configuration`; no host or role launched.

No iTerm2, Codex, dependency installation, network, or human rerun occurred. The observed C1.2.16 smoke target/history is preserved as evidence; independent review is required before further human work.

## C1.2.16 staged Coordinator-first start developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 48 tests in 4.517s`; `OK`. Deterministic fake-native/controller coverage verifies clean Coordinator-only start, immutable snapshot/session consistency before delivery, native ID recording only after delivery, no Developer/Reviewer specification, staged Coordinator acceptance without later launch, dirty/HEAD-less/missing-authority refusal, native app/window/tab/title/session/send failure recovery, launch-failure archival without an active tab claim, held-lock refusal before all mutation/launch, lock release for safe retry, outer malformed/failed/incomplete delivery containment, and retained probe/full-tabs-fail-closed coverage.

`python -m unittest` — exit `0`; `Ran 0 tests`; `OK`. `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`. `python .agent/orchestrate.py start --help` — exit `0`, documents the required `--tabs` flag. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed with `saved state belongs to a different controller configuration`; no host or role launched.

No dependency installation, network, iTerm2, Codex, role, or human C1.2.16 gate ran. After independent review, Alex uses an activated Orchestr8 `.venv` and fresh `/private/tmp` target, establishes a bounded authority and clean baseline, runs `orchestr8 start --tabs`, confirms one Coordinator tab, sends the human brief, and uses the control terminal only to inspect/accept Coordinator output. Developer/Reviewer launch remains unimplemented.

## C1.2.15 Coordinator Codex bootstrap probe developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 41 tests in 4.367s`; `OK`. Fake iTerm2 API/stdio bridge execution proves one no-argument default-profile tab creation, the exact Coordinator bootstrap title, one session retrieval, and exactly one shell-quoted `codex -C <project-root> -s read-only` command with one newline. It covers malformed bootstrap requests; `None` and exception failures for app discovery, active-window discovery, tab, title, session, and command delivery; outer malformed/failed/incomplete response containment; exclusive CLI modes; no-state containment; retained one-tab/layout probes; and full-tabs fail-closed behavior.

`python -m unittest` — exit `0`; `Ran 0 tests`; `OK`. `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`. `python .agent/orchestrate.py init --help` — exit `0`, lists `--tabs-coordinator-bootstrap-probe`. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed with `saved state belongs to a different controller configuration`; no host or role launched.

No dependency installation, network, iTerm2, Codex, role, or manual bootstrap probe ran. After independent review, Alex runs only this probe from an activated Orchestr8 `.venv` in a fresh `/private/tmp` target and visually confirms the Coordinator Codex UI. Bootstrap delivery is unverified controller output, not a supervised session: Alex must not send `Start project: <human initial brief>` and no Developer/Reviewer tab or workflow follows.

## C1.2.14 native three-tab layout probe developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 39 tests in 4.238s`; `OK`. The bridge executes under fake iTerm2 API objects and fake stdio, asserting three ordered no-argument default-profile tab creations and exact native titles. It covers `None` and exception failures at every creation step, title failure at every title step, malformed layout requests, outer process malformed/failed/incomplete response containment, one-tab retention, full-tabs fail-closed behavior, and no supervised state.

`python -m unittest` — exit `0`; `Ran 0 tests`; `OK`. `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`. `python .agent/orchestrate.py init --help` — exit `0`, documents `--tabs-layout-probe` and its `--tabs` requirement. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed with `saved state belongs to a different controller configuration`; no host or role launched.

No dependency installation, network, iTerm2, Codex, role, or manual layout probe ran. After independent review, Alex runs the layout probe from an activated Orchestr8 `.venv` in a fresh `/private/tmp` target.

## C1.2.14 human layout gate

On 2026-10-29, Alex ran `orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-layout-probe` from an activated Orchestr8 `.venv`. The control JSON reported `result: confirmed`, window `pty-56B80AE7-C477-4617-B9AF-3DF0F7F7C709`, tab IDs `14`, `15`, and `16`, and `elapsed_seconds: 0.216`. Alex visibly confirmed all three titled tabs appeared. No Codex role was started. The test target was `/Users/a_cap/work/Ainda/smoke`, which inherits a parent Git worktree and is not suitable for a later clean-baseline/workflow smoke; the host-layout observation remains valid.

## C1.2.15 human Coordinator bootstrap gate

On 2026-10-29, Alex ran `orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-coordinator-bootstrap-probe` from an activated Orchestr8 `.venv`. The control JSON reported `unverified_bootstrap_delivered`, window `pty-56B80AE7-C477-4617-B9AF-3DF0F7F7C709`, tab `17`, session `E72CE81E-0132-4AB9-A632-4890580F8A80`, and `elapsed_seconds: 0.075`. The new tab displayed interactive Codex v0.163.0 in `/Users/a_cap/work/Ainda/smoke`, read `.agent/roles/coordinator.md`, and waited for `Start project: <human initial brief>`. Alex sent no task message and no role artifact was written. This remains host/bootstrap evidence only because the target inherits a parent Git worktree.

## C1.2.13 native one-tab human gate

On 2026-10-29, Alex ran the isolated-venv native probe with iTerm2 Python API enabled. It returned `ok: true`, `reason: confirmed`, opaque window/tab identifiers, and `elapsed_seconds: 0.069`; Alex observed one created tab. Read-only inspection of the probe target found only `.agent/runtime/state.json`, without `tabs.json` or `supervised_session.json`. That target inherited `/Users/a_cap`'s parent Git worktree and is not valid for a later clean-baseline/full-workflow smoke; the host-only probe result remains valid. No Codex/role started.

## C1.2.13.1 minimal native-probe completion developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 37 tests in 4.320s`; `OK`. The bridge module executes under fake `iterm2` objects and fake stdio for no-argument default-tab/title success, `None` immediate close, title failure, lazy missing module, and malformed JSON. Outer `launch_iterm_probe()` process-boundary tests retain success, malformed response, failed response, and failed-process containment; fake-only probe tests retain one-tab/no-role/no-supervised-state and full-tabs-fail-closed containment.

`python -m unittest` — exit `0`; `Ran 0 tests`; `OK`. `python -m py_compile .agent/orchestrate.py .agent/iterm_probe.py orchestr8.py` and `git diff --check` — exit `0`. `python .agent/orchestrate.py init --help` — exit `0`, shows `--tabs-probe` requires `--tabs`. `python .agent/orchestrate.py --dry-run` — exit `2`, fail-closed with `saved state belongs to a different controller configuration`; it launched no host or role.

No dependency was installed, and no network, iTerm2, Codex, role, or manual probe ran. The real native probe remains Alex's post-review fresh-disposable-directory gate.

## C1.2.12.1 native bridge test/setup completion developer validation

Controller tests cover fake native-bridge success with opaque window/tab/session identifiers plus malformed JSON, failed response, and failed process propagation; the full `--tabs` fail-closed expectation is explicit. No test imports or installs `iterm2`.

## C1.2.11.2 complete host-probe timing diagnostics developer validation

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 35 tests in 4.271s`; `OK`. `python -m unittest` — exit `0`; `Ran 0 tests`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py init --help` — exit `0`. `python .agent/orchestrate.py --dry-run` remained fail-closed on the existing ignored-runtime configuration mismatch and launched no host or role.

The iTerm2 readiness script now uses AppleScript `current date` timing and surfaces `pre_count`, `final_count`, `attempts`, `elapsed_seconds`, and `reason` on confirmation; its failed-readiness error carries the same facts and fresh-target/partial-tab recovery. Fake-only assertions cover both source paths. No iTerm2/Codex session ran; independent review is pending.

## C1.2.11.1 host-probe readiness evidence developer validation

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 35 tests in 4.045s`; `OK`. `python -m unittest` — exit `0`; `Ran 0 tests`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py init --help` — exit `0`. Help shows `--tabs-probe` requires `--tabs`; subprocess coverage rejects the invalid standalone flag. `python .agent/orchestrate.py --dry-run` remained fail-closed on the existing ignored-runtime configuration mismatch and launched no host or role.

The generated iTerm2 probe script polls at most ten times with a bounded delay, returns pre-count/final-count/attempts/reason diagnostics, and times out with fresh-target recovery guidance before supervised state. Fake-only tests retain exactly-one-tab/no-role/no-supervised assertions. No iTerm2/Codex session ran; independent review is pending.

## C1.2.11 one-tab iTerm2 host-probe developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 34 tests in 4.038s`; `OK`.

The fake-only probe test asserts exactly one `ORCHESTR8 · Host probe` spec, no configured role command, local diagnostic command content, and no supervised runtime state. The probe uses the same supported iTerm2 creation/count-confirmation path but starts no role or workflow. Real probe execution remains Alex's post-review gate.

## C1.2.9.1 current smoke-recovery documentation developer evidence

`python .agent/orchestrate.py init --help` — exit `0`; `--tabs` remains iTerm2-only and does not launch a host. `rg -n -- "C1.2.8|C1.2.9|iTerm2" README.md docs/controller/README.md` confirmed the active root guide now names C1.2.9 and its iTerm2-only recovery model. `git diff --check` — exit `0`.

The root guide now records the observed C1.2.8 failure (supervised state written without persistent visible role tabs), requires C1.2.9 control-window tab-count confirmation, documents the inspectable exit shell, and requires closing partial tabs plus a fresh disposable target without advancing the failed handoff. No iTerm2/Codex session or real smoke was run. Independent review is pending.

## C1.2.9 iTerm2 visible-session confirmation developer evidence

The real C1.2.8 smoke was not successful: it wrote supervised state although role tabs did not remain visible. That target must not be reused; Alex owns a new-disposable retry after independent review.

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 33 tests in 3.973s`; `OK`. `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py init --help` — exit `0`; help remains iTerm2-only. `python .agent/orchestrate.py --dry-run` emitted the existing ignored-runtime configuration-mismatch structured stop and launched neither iTerm2 nor a role.

Each iTerm2 creation captures the tab count before creation and requires exactly one additional tab in the captured control window before the launcher returns. The one-time bootstrap emits the title, runs the configured least-privilege session command, then reports its exit status and leaves an inspection shell open. Fake-only coverage verifies count confirmation source, quoting, role sandbox, later-launch failure without supervised state, and no later injection. No iTerm2/Codex session or real smoke was run. Independent review is pending.

## C1.2.8 iTerm2 return-value-free tab-identification developer evidence

The real C1.2.7 iTerm2 smoke failed safely before `tabs.json` or `supervised_session.json` with a missing `launchedTab` title reference (`-10006`); partial role tabs may exist and must be closed. Alex owns a fresh-disposable retry after independent review.

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 32 tests in 3.887s`; `OK`. `python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py`, `git diff --check`, and `python .agent/orchestrate.py init --help` — exit `0`; help remains iTerm2-only. `python .agent/orchestrate.py --dry-run` emitted the existing ignored-runtime configuration-mismatch structured stop and launched neither iTerm2 nor a role.

The iTerm2 script no longer binds or dereferences a create-tab return value. Its exact one-time bootstrap shell command uses a shell-quoted OSC title escape, then configured session command, `-C`, role instruction, and effective sandbox. Fake-only coverage asserts title escaping and rejects `launchedTab`, `current session of launchedTab`, and `title of launchedTab`; existing three-role least-privilege and failed-launch containment remain covered. No iTerm2/Codex session or real smoke was run. Independent review is pending.

## C1.2.7 iTerm2 created-tab session-reference developer evidence

The real C1.2.6 iTerm2 smoke failed safely before supervised session state with `Can’t get current session of missing value. (-1728)`. The failed disposable directory must not be reused; Alex owns a new-disposable retry after independent review.

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 32 tests in 3.913s`; `OK`.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK`. `python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

`python .agent/orchestrate.py init --help` — exit `0`, retains iTerm2-only `--tabs` help. `python .agent/orchestrate.py --dry-run` emitted the existing ignored-runtime configuration-mismatch structured stop and launched neither iTerm2 nor a role.

The locally installed iTerm2 dictionary declares `create tab with default profile` returning a tab and a writable tab `title`. The adapter now sets `title of launchedTab` inside `tell targetWindow`; fake-runner coverage asserts the title follows tab creation inside that scope and rejects `current session of launchedTab`. It retains configured static bootstrap, `-C`, least-privilege sandboxing, quoting, and failed-launch containment. No iTerm2/Codex session or real smoke was run. Independent review is pending.

## C1.2.6.1 stale Terminal CLI-claim retirement developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 32 tests in 3.893s`; `OK`.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (the explicit controller module is the full relevant suite).

`python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

`python .agent/orchestrate.py init --help` — exit `0`; `--tabs` states `open supervised iTerm2 role tabs after successful initialization`. The regression test asserts that wording and rejects the retired `Terminal role tabs` claim. The active root and controller README C1.2.6 guidance also names iTerm2 only; Terminal references are explicitly historical/superseded records.

`python .agent/orchestrate.py --dry-run` — emitted the existing ignored-runtime configuration-mismatch structured stop and launched neither iTerm2 nor a role. No human iTerm2/Codex smoke was run. Independent review is pending.

## C1.2.6 iTerm2 persistent-tab host developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 31 tests in 3.778s`; `OK` after the iTerm2 failed-launch containment test was added.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (the explicit controller module is the full relevant suite).

`python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

`python .agent/orchestrate.py --dry-run` produced the existing ignored-runtime configuration-mismatch structured stop and launched neither iTerm2 nor a role; that prior runtime state belongs to the pre-C1.2.6 configuration.

The iTerm2 adapter uses the documented `create tab with default profile command` inside `front window`, captures the returned tab, and sets the returned tab's current-session name. It sends only that static bootstrap command at tab creation. Fake tests cover Unicode/shell quoting, exact interactive `-C` and sandbox allocation without `--skip-git-repo-check`, iTerm2 source strategy, unsupported host rejection, and an iTerm2 failure leaving no supervised runtime state. iTerm2 is not installed at the usual local application paths in this environment; no iTerm2/Codex session or real smoke was run. Independent review is required before Alex retries in a new disposable directory.

## C1.2.5 Terminal tab-operation compatibility developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 29 tests in 3.798s`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

The locally inspected Terminal scripting dictionary supplies `make`, `do script`, and tab/window targets. The adapter now creates `launchedTab` directly at the end of the captured control window's tabs, targets `do script` to that tab, and titles that same tab. It has no `move launchedTab` dependency and surfaces a specific inability-to-create-tab error before supervised state creation. Fake-only coverage asserts this strategy plus interactive `-C`/sandbox arguments without `--skip-git-repo-check`. No Terminal tab or Codex session was opened, and no real smoke success is claimed. Independent review is pending before Alex retries in a new disposable directory.

## C1.2.4 real interactive-launch compatibility developer evidence

`codex --help` was inspected locally: interactive `codex` accepts `-C` and `-s`; `--skip-git-repo-check` is not an interactive option.

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 29 tests in 3.824s`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

The fake-`osascript` test confirms the interactive launch retains configured command, `-C`, and configured sandbox without `--skip-git-repo-check`; it captures the returned tab, moves it into the original front window, and assigns that same tab's title. Tests use only fakes and did not open Terminal or invoke a Codex session. The human guide now stops for unsupported CLI arguments, commands in the control tab, separate windows, or absent role tabs. No real UI success is claimed. Independent review is pending before Alex reruns the smoke gate.

## C1.2.3 smoke-readiness documentation and packaging-hygiene developer evidence

`git diff --check` — exit `0`.

The controller source `.gitignore` now narrowly excludes editable-install `*.egg-info/` metadata. The controller README documents the complete human-only disposable smoke procedure: same-window tab observation, replacement of neutral authority with labeled Common task/Developer work/Reviewer handoff sections, initial Git baseline, Coordinator acceptance, and Developer `do next prompt` handoff. No Terminal tab or Codex session was opened, and no real smoke success is claimed. Independent review is pending.

## C1.2.2 role-isolation and same-window-tabs developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 29 tests in 4.028s`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

The deterministic fake-`osascript` test inspects source that captures `front window`, creates `launchedTab` through `do script ... in targetWindow`, and assigns the title directly to that returned tab. It opens neither Terminal nor Codex. Contract-level coverage confirms each role's allowed authority sections and its sole fixed output artifact are distinct. Existing lifecycle, capability, session-state, and launch-failure tests remain green.

The C1.2.2 real UI gate is intentionally not run or claimed here. The documented human retry must verify one Terminal window with the retained control tab plus the three role tabs, correct labels, and Developer implementation behavior after `do next prompt`. Independent review is pending.

## C1.2.1 macOS tab-launch remediation developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 28 tests in 3.860s`; `OK`.

`python -m py_compile .agent/orchestrate.py orchestr8.py` and `git diff --check` — exit `0`.

The deterministic fake-`osascript` test inspects `['osascript', '-e', source]` and its `text=True, capture_output=True` invocation without opening Terminal or invoking Codex. It verifies direct Unicode `·` source, no JSON `\\u00b7` escape, quoted title/path escaping, and shell-safe session-command arguments.

Manual disposable smoke retry, executed with the installed command from `/private/tmp/orchestr8-c121-QuwSOs`:

`orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs`

completed initialization. A read-only Terminal title query then observed exactly the three new labeled tabs: `ORCHESTR8 · Coordinator · waiting for human brief`, `ORCHESTR8 · Developer · waiting for human approved task`, and `ORCHESTR8 · Reviewer · waiting for human Developer evidence`. No role phrase or later keystroke was sent. The successful path created only expected scaffold plus non-authoritative `current/tabs.json` and `supervised_session.json`; no history was created. The launch-failure deterministic regression still asserts neither `current` nor `history` is created.

Independent review is pending.

## C1.2 phrase/session-state follow-up developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 27 tests in 3.786s`; `OK`.

The controller and role contracts use only `Start project: <human initial brief>`, `do next prompt`, `review latest`, and `coordinate latest`. Deterministic coverage confirms each displayed phase maps to that vocabulary, and missing, malformed JSON, list, null, and unknown supervised sessions become archived `stale_or_mismatched_task_state` stops through accept, cycle, status, preview, or resume without role dispatch.

Independent review recorded `READY` in `docs/controller/REVIEW_REPORT_controller.md`: controller suite ran 27 tests; explicit default unittest discovery ran 0 tests; compile, diff, and safe help/preview/dry-run checks passed. No real Terminal tab, Codex role, network service, commit, push, or write-capable workflow cycle was invoked.

## C1.2 lifecycle/capability remediation developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 25 tests in 3.803s`; `OK`.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (the explicit controller module is the full relevant suite). `python -m py_compile .agent/orchestrate.py orchestr8.py`, `git diff --check`, `python orchestr8.py --help`, `python orchestr8.py preview`, and `python .agent/orchestrate.py --dry-run` also exited `0` without launching a tab or role.

The deterministic suite uses fake tab launchers only. It verifies configured `session_command` specifications and effective `read-only`, `workspace-write`, `read-only` allocation; dirty and HEAD-less supervised Coordinator acceptance stops before Developer with archived structured evidence; accepted Developer/Reviewer reports are archived; post-review status is `Coordinator: coordinate latest`; and invalid cycle artifact preconditions stop safely.

Independent review remains pending.

## C1.2 developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 23 tests in 3.523s`; `OK`.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery finds no tests; the explicit module is the full relevant suite).

`python -m py_compile .agent/orchestrate.py orchestr8.py`, `git diff --check`, `python orchestr8.py --help`, `python orchestr8.py preview`, and `python .agent/orchestrate.py --dry-run` — exit `0`. The preview/dry-run commands printed state only and did not dispatch a role.

Coverage uses temporary roots and fake launchers only: package launcher target-CWD initialization/defaults, canonical and aliased role lists, refusal of invalid order/duplicates/unknown roles, three ordered tab specs, tab-launch failure without runtime state, preview output, and Coordinator → Developer → Reviewer acceptance through fixed snapshot/report artifacts. No test opens Terminal tabs or invokes Codex.

Independent review remains pending.

## C1.1 symlink-safe remediation developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 20 tests in 3.322s`; `OK`.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (default discovery finds no tests; the explicit module is the full relevant suite).

`python -m py_compile .agent/orchestrate.py` and `git diff --check` — exit `0`.

`python .agent/orchestrate.py --dry-run` — exit `0`; printed the configured root, authority, role order, and one-cycle default without dispatching a role.

Regression coverage creates external directories and symlinks the requested project's `.agent` and `docs` parents to them. `init --init-git` refuses before any external write, target Git initialization, controller scaffold, or `.gitignore` change. A project-root symlink remains supported by resolving it once to the actual project root.

Independent review recorded `READY`: it reran the controller suite (`20 tests`), the explicit full relevant unittest command, compilation, diff check, and dry-run; it also independently verified `.agent`, `docs`, and `.gitignore` symlink refusal with no external write or target Git initialization. See `REVIEW_REPORT_controller.md`.

## C1.1 developer evidence

`python -m unittest tests.test_orchestrator_safety` — exit `0`; `Ran 18 tests in 3.182s`; `OK`.

`python -m unittest` — exit `0`; `Ran 0 tests in 0.000s`; `OK` (this repository does not use default unittest discovery; the explicit module above is the full relevant suite).

`git diff --check` — exit `0`.

`python -m py_compile .agent/orchestrate.py` — exit `0`.

`python .agent/orchestrate.py --dry-run` — exit `0`; printed the configured root, durable authority, ordered roles, and one-cycle default without dispatching a role.

C1.1 tests use temporary directories and cover new and existing Git targets, explicit Git initialization without a `HEAD`, collision/idempotency refusal, authority path escapes, non-Git refusal, preservation of existing project rules/files and `.gitignore` content, generated configuration/dry-run validity after a user-created baseline, and absence of role or execution-history artifacts during initialization.

Independent review remains pending.

## C1 final evidence

`python -m py_compile .agent/orchestrate.py` — exit `0`.

`python -m unittest tests.test_orchestrator_safety` — `Ran 14 tests in 2.644s`; `OK`.

`python -m unittest` — `Ran 61 tests in 2.493s`; `OK`.

`python .agent/orchestrate.py --dry-run` — exit `0`; printed the configured project root, durable authority, ordered semantic roles, and one-cycle default without dispatching a role.

`git diff --check` — exit `0`.

The controller tests use temporary roots and a deterministic local fake executable. They do not invoke Codex, network services, secrets, or live-provider checks. Coverage includes a real clean temporary-Git full cycle whose configured runtime artifacts are excluded from the user-work baseline; real dirty-Git refusal; fixed role-order rejection; default one-cycle and explicit multi-cycle execution; custom current/history/state and role-asset locations; immutable Developer/Reviewer snapshots; persisted role exit, timeout, missing-output, malformed-JSON, missing-contract, extra-field contract, and malformed-checkpoint stops; hash-bound approval evidence; configuration rejection for non-boolean or non-Developer write capability; read-only Reviewer dispatch; coordinator/developer/reviewer resume and stale-state paths; all secret exclusions in current/history manifests; locks; and immutable history.

Independent review recorded `READY WITH NON-BLOCKING CORRECTIONS` after rerunning the controller suite (`14 tests`), full suite (`61 tests`), `git diff --check`, and controller dry-run. The sole non-blocking README runtime-state path correction is applied; see `REVIEW_REPORT_controller.md`.

## Two human-gated tasks in persistent tabs — live proof passed

The operator ran the live test in `/private/tmp/orchestr8-two-cycle.t40d4X`. Coordinator inspected the saved evidence read-only. Archives 001, 002 and 003 contain the Developer report, Reviewer report and task snapshot. Task 1 received CHANGES_REQUIRED and passed on its approved second attempt. Task 2 passed on its first attempt. Both rollover approval hashes match the archived successor snapshots.

Nine confirmed role triggers used the same three session IDs throughout. Task 2 changed only receipt.txt relative to its attempt baseline. Final bytes were `hello\nready\n` and `verified\n`. Git HEAD remained at the initial baseline, 9bb74a26ae235b7223fb051a3253c658e91d21f7.

Final status showed task 2 of 2, APPROVED, a Coordinator summary and no pending proposal. The operator's extra rollover command refused because there was no proposal. No fourth attempt or additional send was recorded. The explicit exhausted-budget refusal with a third proposal is covered by the deterministic suite. This proof covers human-gated operation.
