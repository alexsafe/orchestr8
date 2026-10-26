# Local Controller C1

The controller is repository-local orchestration tooling. It does not make product decisions, alter the durable task authority, commit, push, use a network, or run automatically.

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
