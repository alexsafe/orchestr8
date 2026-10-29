# Local Controller C1

The controller is repository-local orchestration tooling. It does not make product decisions, alter the durable task authority, commit, push, use a network, or run automatically.

## Current native iTerm2 probe path

This is the only active tab setup and run path. In an iTerm2 control tab, create an isolated environment and install this checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Enable and authorize the iTerm2 Python API. In a fresh disposable target, run only:

```sh
orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-probe
```

The result is one default-shell `ORCHESTR8 · Host probe` tab and control JSON. It starts no Codex or role, injects no command, and creates no supervised state. Full `--tabs` intentionally fails closed. Do not use global/system installation or `--break-system-packages`; if a session closes or leaves a partial tab, close it and use a fresh target.

## Historical audit record: superseded AppleScript tab workflow

The material in this section records superseded C1.2 investigations only. It is not setup or run guidance.

Install from a development checkout with `python -m pip install --user -e /path/to/orchestr8`. From an existing iTerm2 control tab in the target project, use `orchestr8 init --roles coordinator,developer,reviewer --tabs`; current directory and `docs/NEXT_PROMPT.md` are the defaults. Only the documented aliases `coord`, `dev`, and `review` are accepted, and only canonical Coordinator → Developer → Reviewer order is valid.

`--tabs` requires iTerm2 on macOS; `tab_host` must be `iterm2`, and no other automatic-tab host is supported. It uses iTerm2's `create tab with default profile command` operation in the existing control window to start exactly three labeled interactive sessions after safe scaffold preflight. Coordinator and Reviewer receive `read-only`, while Developer alone receives `workspace-write`. Each tab receives its one static configured session command at creation; it never injects later keystrokes, prompts, or state-machine phrases. The control tab owns `preview`, `status`, `cycle`, `resume`, and `accept <role>`. `cycle` validates durable snapshot/report preconditions before printing the next tab and phrase; `accept` uses the C1 clean-baseline, snapshot, structured-stop, and history machinery before advancing the handoff. The exact phrases are `Start project: <human initial brief>`, `do next prompt`, `review latest`, and `coordinate latest`. Tabs and `tabs.json` are non-authoritative; immutable task snapshots, reports, hashes, approval checks, and history remain authoritative. If iTerm2 is unavailable, incompatible, or launch fails, no supervised runtime state is created; resolve the host prerequisite and retry from a new disposable directory.

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

Run `python .agent/orchestrate.py init --project-root /path/to/project --task-authority docs/NEXT_PROMPT.md` from a controller source checkout for an existing Git project. For a new or non-Git directory, add `--init-git`; it runs `git init` only and never creates a commit. The command creates the local config, role instructions and schemas, controller script, neutral authority template, empty approval record, runtime state, runtime ignore entries, and this reference document.

Initialization validates every planned destination and its existing parent components before writing. It refuses a controller target, runtime/history directory, or requested authority that already exists, and rejects internal symlinks rather than traversing them. Authority paths must be project-relative and cannot escape the target root. A project-root symlink is resolved once to its actual root only; all scaffold destinations must remain beneath that root. It preserves `AGENTS.md`, project files, and unrelated `.gitignore` content. It never invokes a role, creates snapshots/history records, changes an existing authority, adds approval, commits, pushes, or accesses a network.

After initialization, configure role commands if necessary, replace the neutral authority through the approval process with a bounded task, create an initial Git commit/`HEAD`, then run `python .agent/orchestrate.py --dry-run`. A Git repository without `HEAD` is valid for initialization but cannot dispatch Developer.

Copy `.agent/controller_config.json` and provide project-relative paths for one human-visible `task_authority`, auditable `approval_record`, and a dedicated runtime root containing `current`, immutable `history`, and `state`. The controller excludes only that configured runtime root from the pre-dispatch Git-clean check and baseline manifest, so its own outputs cannot be mistaken for user work. Paths escaping the configured project root are rejected.

Initialize `state` with at least `{"iteration": 0, "status": "READY"}`. Do not copy a previous project's current or history directory. C1 accepts only the configured list order Coordinator → Developer → Reviewer; any other order is rejected because Developer requires the immutable task snapshot and Reviewer requires Developer evidence. Their instruction assets, commands, schemas, paths, timeout, and read/write behavior are project-configured. It does not support arbitrary role graphs.

Each selected role schema is enforced as its output contract, including required fields, declared primitive/array types, nullable values, enums, and `additionalProperties: false`. Capability settings are fixed: `write_capable` must be a boolean, Developer must be `true`, and Coordinator and Reviewer must be `false`; Reviewer is always dispatched read-only.

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
