# Local Controller C1

The controller is repository-local orchestration tooling. It does not make product decisions, alter the durable task authority, commit, push, use a network, or run automatically.

## Current native iTerm2 probe path

This is the only active tab setup and run path. In an iTerm2 control tab, create an isolated environment and install this checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Enable and authorize the iTerm2 Python API. The proven minimal probe is:

```sh
orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-probe
```

The result is one default-shell `ORCHESTR8 · Host probe` tab and control JSON. It starts no Codex or role, injects no command, and creates no supervised state. `init --tabs` without a probe intentionally fails closed. Do not use global/system installation or `--break-system-packages`; if a session closes or leaves a partial tab, close it and use a fresh target.

The probe gates have passed. After independent review, Alex initializes a fresh `/private/tmp` target from the activated Orchestr8 `.venv`, authorizes a simple bounded durable task, creates a clean baseline commit, and then runs:

```sh
smoke_dir=$(mktemp -d /private/tmp/orchestr8-c1216-XXXXXX)
cd "$smoke_dir"
orchestr8 start --tabs
```

`start --tabs` acquires the controller runtime lock before any preflight or write; a held lock fails before snapshot, session, or tab mutation. It then requires a clean committed Git baseline, valid authority/configuration, and no current or stale supervised session. It writes immutable snapshot and Coordinator-initial session evidence before the native launch, then creates exactly one native default-profile `ORCHESTR8 · Coordinator · waiting for Start project…` tab and sends one shell-quoted configured workspace-write Codex command. Native tab/session IDs are recorded only after delivery. Alex visually confirms Codex remains interactive, sends `Start project: <human initial brief>`, then uses the control terminal only to inspect/accept the Coordinator result. A Coordinator `HUMAN_REQUIRED` acceptance is terminal: it archives once, retains `current/human_stop.json`, removes active session/tab state, prints a nonzero structured stop, and makes later `status`/`accept` refer only to that evidence. Acceptance enables an explicit Developer launch; it does not launch another role. On a refusal or interrupted delivery, preserve evidence and follow the recovery conditions below; a fresh authorized run may use the same project after those conditions are met.

### Explicit staged cycle (C1.2.19)

After `orchestr8 start --tabs`, send `Start project: <brief>` manually in the Coordinator tab. Run `orchestr8 accept coordinator`, then `orchestr8 launch developer`. Check that the Developer tab is waiting at the Codex input prompt, then run `orchestr8 trigger developer --ready`. When its report is ready, run `orchestr8 accept developer`, then `orchestr8 launch reviewer`. Check the Reviewer tab is waiting, then run `orchestr8 trigger reviewer --ready`. After its report is ready, run `orchestr8 accept reviewer`. Check that the original Coordinator tab is waiting, then run `orchestr8 trigger coordinator --ready`; the Coordinator then writes the separate final summary. Acceptance and triggers never launch the next role. The final summary refers to the completed iteration and does not authorize another cycle. The configured current directory holds the owned `.coordinator.json`, `.developer.json`, and `.reviewer.json` reports. The controller publishes `dev_report.md` and `review_report.md`; roles do not overwrite them. After completion, Coordinator writes `coordinator_summary.md` and may separately propose complete instructions in `coordinator_proposal.md`; neither authorizes a rollover.

`--ready` records the human's readiness check; it is not technical proof that Codex is still at its input prompt. If the CLI exits or changes state between that check and delivery, text may reach an unintended prompt. The bridge sends the prompt and then a separate carriage-return input to the same session. Completion of those input requests does not prove that Codex submitted or completed the turn; `status` reports transport separately from the presence of unvalidated role output. The bridge refuses missing destinations and known shell or unknown foreground jobs; it never creates a fallback tab and suppresses iTerm broadcast.

For each stage, choose either the standalone manual phrase or one app-sent trigger; do not use both. After any prepared, uncertain, or confirmed attempt, inspect the recorded evidence and tab; do not retry the trigger or repeat the phrase blindly. The controller records one attempt per role and never automatically resends it. The initial brief remains manual. Two human-gated tasks are supported within the limits authorized at start; unattended progression is not implemented.

For this milestone authorize limits at the initial start: `orchestr8 start --tabs --task-limit 2 --attempt-limit 2`. The first limit is at most two tasks; the second is the per-task attempt limit. The default for each is one. After Coordinator writes a summary and separate proposal, inspect `orchestr8 proposal`. For a correction, it displays the complete instructions, original task and `correction_scope.json`: verify each finding maps to a change, the original criteria are retained and no new scope is introduced. Record that decision with `orchestr8 approve-next --run-id <run-id> --iteration <iteration> --proposal-sha256 <sha256> --scope-sha256 <scope-sha256> --confirm-correction-scope`. For an approved next task omit the final two scope options. Then use `orchestr8 rollover-correction` or `orchestr8 rollover-next-task`; neither sends a trigger. Check the existing tab, then use `orchestr8 trigger developer --ready`; after acceptance, similarly trigger Reviewer. To stop before approval, including after a summary with no proposal, run `orchestr8 status` and copy its `stop_command`: `orchestr8 stop-proposal --run-id <run-id> --iteration <iteration>`. Stop preserves the task and evidence and refuses later approval, rollover and dispatch. Exhaustion stops progression. Preserve partial persistence evidence and do not retry blindly. This implementation has not been independently reviewed or live-proven.

For corrections, Coordinator writes `correction_scope.json` alongside the proposal. It contains the same task ID, original iteration and original task snapshot SHA-256, predecessor iteration and review-report SHA-256, `criteria_changes: []`, and a `findings` array. Each entry names a zero-based `finding_index`, SHA-256 of the exact UTF-8 finding as `finding_sha256`, and a nonempty `change` excerpt appearing verbatim in the proposed instructions. Every nonblank finding must be mapped once, and the complete original task must appear verbatim. The controller checks these references and hashes; the human judges whether the proposal stays in scope and actually addresses the findings.

The authoritative staged workflow decisions and shared role guidance are in `.agent/workflow_policy.json` (version 1). At `start`, the controller freezes its bytes and the hashes of all three configured role instruction files; staged actions refuse if the current policy, role instructions, or frozen evidence differ. Both rollover kinds carry the identity and frozen policy forward. A staged run without this identity is refused; do not repair or rebind it in place. Edit policy or role guidance only before a fresh authorized run. The legacy non-staged path also freezes the policy for new runs; older active runs without an identity are refused rather than rebound.

If rollover persistence raises an error or is interrupted, the controller retains its lock as a recovery barrier, including when the final state write may have landed. For an active or incomplete run, `status` refuses while the lock exists rather than suggesting a trigger. Preserve the lock and all artifacts, inspect the partial publication and process, and remove a lock only after verifying it is stale and deciding on human-directed recovery. Do not blindly retry rollover or dispatch.

For every rollover Developer turn, the role must run `orchestr8 ready-developer --attempt-id <attempt-id>` and receive `ready: true` before work or report creation. A standalone manual phrase uses the attempt ID in the current supervised session. A controller-sent phrase supplies the attempt and delivery IDs; pass the latter as `--delivery-id <delivery-id>`. The trigger command briefly holds the lock; wait for it to finish before checking. A retained lock, uncertain delivery, stale identity, occupied report, or failed check means no work or report; inspect the control terminal and evidence. This check is read-only and does not send or retry a trigger; it verifies a point in time and cannot prevent later external changes. Initial single-cycle turns retain their existing flow.

The other initial labels are `ORCHESTR8 · Developer · waiting for do next prompt` and `ORCHESTR8 · Reviewer · waiting for review latest`. Acceptance and trigger commands attempt cosmetic updates against the recorded window, tab and session. The separate label result cannot undo acceptance or authorize resending. Labels may lag role activity until a controller action; trigger delivery does not establish processing. Before preparation or tab creation, start and launch check iTerm dependencies using the bridge's interpreter; use the source `.venv/bin/python` for source-checkout helpers if needed.

For a separately authorized input diagnostic, see [the disposable submission smoke](SUBMISSION_SMOKE.md). It does not start a role or a controller cycle.

Developer launch rechecks the snapshot and clean committed baseline. Reviewer launch preserves expected Developer changes while checking the accepted report and frozen review identity; Reviewer acceptance checks that identity again. If delivery is uncertain, do not retry: preserve the preparation evidence, inspect the tab and resolve the prior session before a fresh authorized run.

Production interactive Coordinator, Developer, and Reviewer sessions use `workspace-write` so each can write its designated report. The `write_capable` configuration flag still grants code-change authority only to Developer. Coordinator and Reviewer must not autonomously edit code, task authority, approvals, state, history, published reports, or another role's evidence; other writes require explicit human authorization. The controller checks project and protected runtime evidence at handoffs. For project paths excluded from the ordinary manifest, it reads their contents to record one aggregate fingerprint without storing their individual names or contents. These checks do not provide hostile-agent isolation or automatic rollback, and actual report writing remains a human smoke gate after independent review.

### Coordinator refusal and recovery (C1.2.18)

A held lock, invalid saved state, dirty or HEAD-less baseline, duplicate start, wrong role, or absent Coordinator report produces a nonterminal structured refusal. If the report is absent, wait for the final artifact and retry `accept coordinator`. A changed-task proposal is preserved without changing the run or authority; any approved change requires a fresh authorized run. A schema-valid explicit `HUMAN_REQUIRED` decision remains terminal for a trustworthy active run.

If launch delivery is uncertain, preserve preparation evidence and inspect any partial tab before proceeding; do not relaunch automatically. Before a fresh authorized run, preserve bad evidence and history, resolve prior processes, tabs, and lock ownership, verify configuration and authority, and establish a clean committed baseline. The same project may be reused after those conditions are satisfied; do not delete a lock without verifying it is stale. An archive or evidence-write conflict can leave partial writes: preserve them and inspect the refusal before recovery.

The earlier manually gated cycle was reported as passed. App-sent triggers still require independent review and a separately authorized human single-cycle gate.

## Historical audit record: superseded AppleScript tab workflow

The material in this section records superseded C1.2 investigations only. It is not setup or run guidance.

Install from a development checkout with `python -m pip install --user -e /path/to/orchestr8`. From an existing iTerm2 control tab in the target project, use `orchestr8 init --roles coordinator,developer,reviewer --tabs`; current directory and `docs/NEXT_PROMPT.md` are the defaults. Only the documented aliases `coord`, `dev`, and `review` are accepted, and only canonical Coordinator → Developer → Reviewer order is valid.

The superseded AppleScript workflow attempted to create three role tabs during initialization. It is historical; use the explicit staged cycle above for current operation.

### Historical C1.2.9 smoke procedure

Before attempting a full role launch, use the C1.2.11 one-tab host probe from an iTerm2 control tab in a fresh target:

```sh
orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-probe
```

It must create exactly one `ORCHESTR8 · Host probe` tab in the captured control window. The tab prints timestamp, working directory, shell/PATH, local Codex availability/version status, and that no role/workflow started, then remains at an inspection prompt. It creates no `tabs.json`, `supervised_session.json`, role artifact, snapshot, or history. If it fails or creates a partial tab, close that tab and use a fresh target; never advance a workflow from the probe target.

From an existing iTerm2 control tab, create a disposable project and initialize it:

```sh
smoke_dir=$(mktemp -d /private/tmp/orchestr8-c129-XXXXXX)
cd "$smoke_dir"
orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs
```

The C1.2.8 disposable smoke did not succeed: tabs were transient or absent even though `tabs.json` and `supervised_session.json` were written. Do not reuse that directory. C1.2.9 requires iTerm2 to confirm each creation in the captured control window before supervised state exists; if any launch fails, close partial role tabs and use a new disposable target.

Before proceeding, confirm the original control tab remains in one iTerm2 window with exactly three new role tabs (four tabs total): `ORCHESTR8 · Coordinator · waiting for human brief`, `ORCHESTR8 · Developer · waiting for human approved task`, and `ORCHESTR8 · Reviewer · waiting for human Developer evidence`. If iTerm2 is unavailable, a role command appears in the control tab, a separate window remains, a role tab is absent, the count/labels differ, a missing-value error reappears, or the launcher reports a host-operation error, close partial role tabs and stop before any session state exists. Retain the console error, resolve the host issue, and rerun only from a new disposable directory after independent review. Do not edit controller runtime state, send role prompts, or claim success.

In the control tab, replace the neutral `docs/NEXT_PROMPT.md` with this tiny bounded authority. Its labeled sections are deliberate: each role executes only its owned section.

```md
# Disposable smoke task

## Common task

Create one disposable smoke marker. Do not use network, commits, or remote actions.

## Developer work

Create `SMOKE_MARKER.txt` containing exactly `developer smoke\n`. Validate it with `test "$(cat SMOKE_MARKER.txt)" = "developer smoke"`, then write only `.agent/runtime/current/.developer.json`.

## Reviewer handoff

After Developer evidence exists, inspect the marker and Developer evidence only. Do not implement. Write only `.agent/runtime/current/.reviewer.json`.
```

Create the required clean baseline before Coordinator acceptance:

```sh
git add .
git commit -m "Initialize disposable orchestr8 smoke"
```

If Git identity, the baseline commit, or `git status --short` fails, stop and resolve that prerequisite before talking to Coordinator. Do not use `orchestr8 accept coordinator` without a clean `HEAD` baseline.

Then perform the exact human-controlled handoff sequence:

1. In the Coordinator tab, send `Start project: create the disposable smoke marker`. It must write only `.agent/runtime/current/.coordinator.json`.
2. In the control tab, run `orchestr8 accept coordinator`. Expected control artifacts include `authoritative_task.md`, `task_snapshot.json`, `baseline.json`, an updated `supervised_session.json` with phase `developer`, and `state.json` recording the active iteration.
3. In the control tab, run `orchestr8 status`; it must identify Developer and the exact phrase `do next prompt`.
4. In the Developer tab, send `do next prompt`. It must implement the bounded marker task and write only `.agent/runtime/current/.developer.json`; it must not review, update a review report, or claim a verdict.

Expected Developer evidence is `SMOKE_MARKER.txt` plus a schema-valid `.developer.json`; after a later control-terminal acceptance, `dev_report.md` and `after_developer.json` are controller-owned artifacts. If any owned artifact is missing, malformed, appears in the wrong role path, the snapshot/authority is stale, or the Developer responds as Reviewer, stop. Use `orchestr8 status` in the control tab and preserve the structured stop; do not manually advance phases, edit runtime state, or claim smoke success. This is a human observation gate: deterministic tests never automate Terminal or Codex, and this guide does not assert that the procedure has been executed successfully.

## Initialize or adapt a project

Run `.venv/bin/python .agent/orchestrate.py init --project-root /path/to/project --task-authority docs/NEXT_PROMPT.md` from a controller source checkout for an existing Git project. For a new or non-Git directory, add `--init-git`; it runs `git init` only and never creates a commit. The command creates the local config, role instructions and schemas, controller script, neutral authority template, empty approval record, runtime state, runtime ignore entries, and this reference document.

Initialization validates every planned destination and its existing parent components before writing. It refuses a controller target, runtime/history directory, or requested authority that already exists, and rejects internal symlinks rather than traversing them. Authority paths must be project-relative and cannot escape the target root. A project-root symlink is resolved once to its actual root only; all scaffold destinations must remain beneath that root. It preserves `AGENTS.md`, project files, and unrelated `.gitignore` content. It never invokes a role, creates snapshots/history records, changes an existing authority, adds approval, commits, pushes, or accesses a network.

After initialization, configure role commands if necessary, replace the neutral authority through the approval process with a bounded task, create an initial Git commit/`HEAD`, then run `python .agent/orchestrate.py --dry-run`. A Git repository without `HEAD` is valid for initialization but cannot dispatch Developer.

Copy `.agent/controller_config.json` and provide project-relative paths for one human-visible `task_authority`, auditable `approval_record`, and a dedicated runtime root containing `current`, immutable `history`, and `state`. The controller excludes only that configured runtime root from the pre-dispatch Git-clean check and baseline manifest, so its own outputs cannot be mistaken for user work. Paths escaping the configured project root are rejected.

Initialize `state` with at least `{"iteration": 0, "status": "READY"}`. Do not copy a previous project's current or history directory. C1 accepts only the configured list order Coordinator → Developer → Reviewer; any other order is rejected because Developer requires the immutable task snapshot and Reviewer requires Developer evidence. Their instruction assets, commands, schemas, paths, timeout, and read/write behavior are project-configured. It does not support arbitrary role graphs.

Each selected role schema is enforced as its output contract, including required fields, declared primitive/array types, nullable values, enums, and `additionalProperties: false`. Code-change authority is fixed: `write_capable` must be a boolean, Developer must be `true`, and Coordinator and Reviewer must be `false`. Production interactive roles use `workspace-write` for their designated reports; diagnostic probes and the separate non-interactive path keep their existing sandbox policies.

The configured `approval_record` is a project-contained JSON file with an `approvals` array. Before accepting a changed authority after a prior completed snapshot, the controller requires an entry such as:

```json
{"prior_authority_sha256": "...", "new_authority_sha256": "...", "approved_at": "2026-10-19T00:00:00Z"}
```

It archives the matching entry as `approval_evidence.json`. The controller never edits the authority or the approval record.

## Run and recover

`python .agent/orchestrate.py` executes one cycle. Use `--multi-cycle --max-iterations N` only for deliberate repetition. `--resume` is valid only for a saved compatible phase with matching configuration and task snapshot.

The controller writes an authority copy and metadata to `current` before Developer dispatch, then archives them with reports, approval evidence, manifests, and structured stops under `history/<iteration>`. It refuses to overwrite non-empty history. Role exits, timeouts, missing/malformed output, and malformed saved checkpoints become archived `HUMAN_REQUIRED` stops. On a stop, read `current/human_stop.json` or the archived copy, resolve the issue explicitly, record approval if applicable, and start a new cycle. Do not delete a lock unless its owner has verified it is stale.

## Limits

C1 supports only a local sequential Coordinator → Developer → Reviewer flow. It has no approval UI, automated authority-update operation, commit gate, worktree isolation, remote action, or real-role test coverage. Role execution is intentionally outside deterministic verification; tests use fake commands only.


## Future state-machine design checklist

This reference is future design guidance, separate from current operational instructions. C1.2.16.2 remains NOT READY; this table does not prove current runtime behavior.

**Not executable policy, not current-behavior evidence, and not a C1.2.17 runtime acceptance suite.** JSON descriptions below are future response requirements, not changes to make now. Refusal JSON identifies the reason/category and recovery, distinguishes nonterminal refusal, and returns exit 2. Terminal JSON identifies terminal state, category, reason, persisted stop evidence and recovery. Success JSON identifies the resulting phase/status and next action. The Coordinator decisions are described above; other rows remain future design guidance.

| ID | Condition | Future classification | JSON / exit | State and session/tab metadata | History | Human recovery |
|---|---|---|---|---|---|---|
| Q01 | Held lock | non-mutating refusal | Lock refusal / 2 | Unchanged; preserve owner's lock; no launch | None | Wait; remove only after verifying stale lock |
| Q02 | Dirty baseline or missing HEAD at start | non-mutating refusal | Baseline refusal / 2 | Unchanged; no session/launch | None | Establish authorized clean committed baseline |
| Q03 | Preflight fails before session creation | non-mutating refusal | Prerequisite refusal / 2 | Unchanged; no launch | None | Correct prerequisite through existing policy |
| Q04 | Second start encounters existing run/artifacts/terminal evidence | non-mutating refusal | Existing-run refusal / 2 | Unchanged; never invalidate another run | None | Inspect and resolve existing run |
| Q05 | Saved controller state missing/corrupt; identity untrusted | non-mutating refusal | Recovery-required refusal / 2 | Preserve bytes or absence; no reconstruction/cleanup | None; no assumed archive | Dedicated C1.2.18 safe recovery design |
| Q06 | Valid start and confirmed Coordinator delivery | normal transition | Start JSON with snapshot/native IDs / 0 | Establish Coordinator-only run; no later role | None | Confirm UI and supply human brief |
| Q07 | Valid active role; artifact genuinely absent | non-mutating refusal | Not-ready JSON with expected evidence / 2 | Unchanged; role stays active | None | Wait for final artifact, then retry accept |
| Q08 | Wrong-role accept against otherwise valid run | non-mutating refusal | Permitted-role refusal / 2 | Unchanged | None | Accept permitted role when ready |
| Q09 | Valid Coordinator CONTINUE and matching authority/snapshot | normal transition | Accepted; `launch developer` pending / 0 | Mark accepted; retain phase/snapshot/tabs; no launch | None | Explicitly launch Developer |
| Q10 | Repeat unchanged accepted Coordinator result | normal transition (idempotent) | Same accepted JSON / 0 | Unchanged | None | Remain at staged boundary |
| Q11 | Identified active run; malformed/schema-invalid role artifact | terminal stop | Invalid-evidence terminal JSON / 2 | Preserve evidence; terminalize affected run; invalidate active metadata | Once, no overwrite | Inspect and resolve cause |
| Q12 | Identified active run; missing/corrupt/inconsistent required session/snapshot evidence | terminal stop | Inconsistency terminal JSON / 2 | Preserve faulty evidence; terminalize only identified run | Once, no overwrite | Resolve inconsistency |
| Q13 | Identified active run; explicit Coordinator HUMAN_REQUIRED decision | terminal stop | Reported category/reason terminal JSON / 2 | Terminalize; authority unchanged | Once, no overwrite | Resolve human decision through existing policy |
| Q14 | Coordinator proposes a changed task | non-mutating refusal | Changed-task refusal / 2 | Preserve run and snapshot; no authority promotion | None | Fresh authorized run for an approved change |
| Q15 | Native launch fails before controller session exists | non-mutating refusal | Failed-step/delivery-uncertainty refusal / 2 | No controller mutation; physical partial tab may exist | None | Inspect/close partial tabs; correct host issue |
| Q16 | Launch fails after preparation, without proven inconsistency | non-mutating refusal at failure boundary | Incomplete-preparation/delivery refusal / 2 | Preserve preparation; no further mutation or inferred activation | None | Dedicated interrupted-start recovery design |
| Q17 | Launch failure leaves identified active run with demonstrably inconsistent evidence | terminal stop | Inconsistency/delivery-uncertainty terminal JSON / 2 | Terminalize affected run only; preserve evidence | Once, no overwrite | Inspect delivery/tabs before recovery |
| Q18 | Repeat accept after terminal stop | non-mutating refusal | Existing terminal JSON / 2 | Unchanged, including leftover artifacts | None | Follow existing stop evidence |
| Q19 | Status after terminal stop | normal transition (observation) | Existing terminal JSON / 0 | Unchanged; no active-role cue | None | Inspect evidence |
| Q20 | Persistence failure/archive conflict | non-mutating refusal at failure boundary | Persistence-incomplete refusal / 2 | No false success; disclose any preceding partial writes | Never overwrite | Preserve evidence; resolve storage/recovery |
| Q21 | Accepted Coordinator, clean matching baseline | explicit Developer launch | Developer active / 0 | One workspace-write tab in recorded window | None | Send `do next prompt` |
| Q22 | Accepted Developer report and frozen review identity | explicit Reviewer launch | Reviewer active / 0 | One workspace-write tab in recorded window, with report-only write authority | None | Send `review latest` |
| Q23 | Approved Reviewer and unchanged review identity | completion | Completed / 0 | Return to existing Coordinator tab | Archive once | Send `coordinate latest` |
| Q24 | Interrupted staged delivery | refusal at failure boundary | Uncertain delivery / 2 | Preserve preparation; no automatic retry | None | Inspect prior tab and use a fresh authorized run |

A refusal at a failure boundary does not erase or deny earlier preparation writes or physical tab effects. Terminalization requires trustworthy identification of the affected active run; corrupt saved state alone does not authorize archival. Neither a second command nor a missing active-role artifact justifies terminalizing, archiving or invalidating another run.
