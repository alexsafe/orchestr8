# Local Workflow Controller

A small, local Coordinator → Developer → Reviewer controller for bounded coding work.

It snapshots one configured durable task authority, reserves code-change authority for Developer, records structured safe stops, and defaults to one cycle. It does not commit, push, use a network, or invoke work automatically.

## Staged Coordinator-first start (C1.2.16)

This is the only current tab path. From an iTerm2 control tab, create and activate an isolated environment, then install this checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Enable and authorize the iTerm2 Python API. The proven minimal probe remains:

```sh
orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-probe
```

It should create one default-shell tab titled `ORCHESTR8 · Host probe` and emit control JSON. It starts no Codex or role, injects no command, and creates no supervised state. `init --tabs` without a probe intentionally fails closed. Do not use a global/system install or `--break-system-packages`. If the session closes immediately or any partial tab appears, close it and use a fresh target.

The probe gates have passed. After independent review, Alex uses the staged workflow entry point from that activated `.venv` in a fresh `/private/tmp` target: initialize it, authorize a bounded durable task, and create a clean baseline commit. Then run:

```sh
smoke_dir=$(mktemp -d /private/tmp/orchestr8-c1216-XXXXXX)
cd "$smoke_dir"
orchestr8 start --tabs
```

It acquires the controller runtime lock before preflight, snapshots the approved authority, creates one `ORCHESTR8 · Coordinator · waiting for Start project…` workspace-write Codex tab, and records its native identifiers only after delivery. Alex visually verifies the tab, then sends `Start project: <human initial brief>`. Use the control terminal to inspect and accept each role output. If its artifact is not ready, `accept coordinator` is a non-mutating nonzero response: wait, then rerun it. A malformed artifact or Coordinator human-required result is terminal: `accept` prints a nonzero structured stop; `status` reports its evidence and recovery rather than an active role.

### Explicit staged cycle (C1.2.19)

After `orchestr8 start --tabs`, send `Start project: <brief>` manually in the Coordinator tab. Run `orchestr8 accept coordinator`, then `orchestr8 launch developer`. Check that the Developer tab is waiting at the Codex input prompt, then run `orchestr8 trigger developer --ready`. When its report is ready, run `orchestr8 accept developer`, then `orchestr8 launch reviewer`. Check the Reviewer tab is waiting, then run `orchestr8 trigger reviewer --ready`. After its report is ready, run `orchestr8 accept reviewer`. Check that the original Coordinator tab is waiting, then run `orchestr8 trigger coordinator --ready`; the Coordinator then writes the separate final summary. Acceptance and triggers never launch the next role. The final summary refers to the completed iteration and does not authorize another cycle. The configured current directory holds the owned `.coordinator.json`, `.developer.json`, and `.reviewer.json` reports. The controller publishes `dev_report.md` and `review_report.md`; roles do not overwrite them. After completion, Coordinator writes `coordinator_summary.md` and may separately propose complete instructions in `coordinator_proposal.md`; neither authorizes a rollover.

`--ready` records the human's readiness check; it is not technical proof that Codex is still at its input prompt. If the CLI exits or changes state between that check and delivery, text may reach an unintended prompt. The bridge sends the prompt and then a separate carriage-return input to the same session. Completion of those input requests does not prove that Codex submitted or completed the turn; `status` reports transport separately from the presence of unvalidated role output. The bridge refuses missing destinations and known shell or unknown foreground jobs; it never creates a fallback tab and suppresses iTerm broadcast.

For each stage, choose either the standalone manual phrase or one app-sent trigger; do not use both. After any prepared, uncertain, or confirmed attempt, inspect the recorded evidence and tab; do not retry the trigger or repeat the phrase blindly. The controller records one attempt per role and never automatically resends it. The initial brief remains manual. Two human-gated tasks are supported within the limits authorized at start; unattended progression is not implemented.

Developer and Reviewer initially display `ORCHESTR8 · Developer · waiting for do next prompt` and `ORCHESTR8 · Reviewer · waiting for review latest`. Acceptance and trigger commands attempt cosmetic label updates from recorded evidence; a separate label failure does not undo the command or authorize a retry. Labels may lag role activity until a controller action, and a sent trigger does not prove processing. Start and staged launch check iTerm dependencies using the bridge's Python interpreter before preparation; use the source `.venv/bin/python` for source-checkout helpers if needed.

Developer launch rechecks the snapshot and clean committed baseline. Reviewer launch preserves expected Developer changes while checking the accepted report and frozen review identity; Reviewer acceptance checks that identity again. If delivery is uncertain, do not retry: preserve the preparation evidence, inspect the tab and resolve the prior session before a fresh authorized run.

Production interactive Coordinator, Developer, and Reviewer sessions use `workspace-write` so each can write its designated report. The `write_capable` configuration flag still grants code-change authority only to Developer. Coordinator and Reviewer must not autonomously edit code, task authority, approvals, state, history, published reports, or another role's evidence; other writes require explicit human authorization. The controller checks project and protected runtime evidence at handoffs. For project paths excluded from the ordinary manifest, it reads their contents to record one aggregate fingerprint without storing their individual names or contents. These checks do not provide hostile-agent isolation or automatic rollback, and actual report writing remains a human smoke gate after independent review.

### Coordinator refusal and recovery (C1.2.18)

A held lock, invalid saved state, dirty or HEAD-less baseline, duplicate start, wrong role, or absent Coordinator report produces a nonterminal structured refusal. If the report is absent, wait for the final artifact and retry `accept coordinator`. A changed-task proposal is preserved without changing the run or authority; any approved change requires a fresh authorized run. A schema-valid explicit `HUMAN_REQUIRED` decision remains terminal for a trustworthy active run.

If launch delivery is uncertain, preserve preparation evidence and inspect any partial tab before proceeding; do not relaunch automatically. Before a fresh authorized run, preserve bad evidence and history, resolve prior processes, tabs, and lock ownership, verify configuration and authority, and establish a clean committed baseline. The same project may be reused after those conditions are satisfied; do not delete a lock without verifying it is stale. An archive or evidence-write conflict can leave partial writes: preserve them and inspect the refusal before recovery.

The earlier manually gated cycle was reported as passed. App-sent triggers still require independent review and a separately authorized human single-cycle gate.

## Initialize a project

From a controller source checkout, scaffold an existing Git project:

```sh
.venv/bin/python .agent/orchestrate.py init --project-root /path/to/project --task-authority docs/NEXT_PROMPT.md
```

For a new directory, opt in to Git initialization (no commit is made):

```sh
.venv/bin/python .agent/orchestrate.py init --project-root /path/to/project --task-authority docs/NEXT_PROMPT.md --init-git
```

Initialization refuses existing controller targets, task-authority path escapes, and internal symlinks in any scaffold destination or parent. A project-root symlink is resolved once to its actual root; no scaffold path may traverse an internal symlink. It preserves `AGENTS.md`, existing project files, and unrelated `.gitignore` entries; it does not invoke roles, create execution history, approve work, or commit. Configure role commands if needed, authorize a bounded task, and create an initial Git commit/`HEAD` before a write-capable cycle.

Run deterministic checks:

```sh
python -m unittest tests.test_orchestrator_safety
python .agent/orchestrate.py --dry-run
```

See `docs/controller/README.md` for configuration, safety, and recovery details.

# Recording a proposed next task

After final coordination, the Coordinator may write a separate `coordinator_proposal.md` beside `coordinator_summary.md` in the current runtime directory. Run `python .agent/orchestrate.py proposal` in the control terminal to display the full proposal, its SHA-256, run identity, and completed attempt iteration. For a next task, after review use `python .agent/orchestrate.py approve-next --run-id <run-id> --iteration <iteration> --proposal-sha256 <sha256>`. A correction also requires the displayed `--scope-sha256 <scope-sha256> --confirm-correction-scope` after the human checks original criteria, every finding and proposed change, and scope. Approval records the operator's decision; it does not publish or dispatch. To stop before approval, run `orchestr8 status` and copy its `stop-proposal --run-id <run-id> --iteration <iteration>` command, prefixing it with `orchestr8`. See the controller guide for the correction mapping format.

Authorize limits at the initial start, for example `orchestr8 start --tabs --task-limit 2 --attempt-limit 2`. The task limit is at most two; the attempt limit applies separately to each task. Defaults are one task and one attempt. Limits cannot be extended within the run; older runs without recorded limits cannot roll over.

For an approved correction following `CHANGES_REQUIRED`, run `orchestr8 rollover-correction`. Following an `APPROVED` review, use `orchestr8 rollover-next-task` for an approved next-task proposal. Each checks the approval, reviewed project and applicable budget, preserves preceding evidence, publishes the approved instructions, and prepares fresh report paths in the same sessions. It sends nothing; inspect the existing Developer tab and use `orchestr8 trigger developer --ready` separately, then accept its output and explicitly trigger Reviewer. Before any rollover Developer work, the role must obtain an attempt-specific `orchestr8 ready-developer` decision; controller-sent turns also supply a delivery ID and must wait for the trigger command to release its lock. Use `orchestr8 status` for the current task, attempt, limits and next action. If rollover reports incomplete persistence, preserve the files and inspect the partial publication; do not retry or trigger a role blindly. These deterministic checks do not establish live two-task success.
