# Local Workflow Controller

A small, local Coordinator → Developer → Reviewer controller for bounded coding work.

It snapshots one configured durable task authority, keeps Developer write access separate from a read-only Reviewer, records structured safe stops, and defaults to one cycle. It does not commit, push, use a network, or invoke work automatically.

## Native iTerm2 probe (C1.2.13)

This is the only current tab path. From an iTerm2 control tab, create and activate an isolated environment, then install this checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Enable and authorize the iTerm2 Python API, then run only the minimal probe in a fresh disposable target:

```sh
orchestr8 init --init-git --roles coordinator,developer,reviewer --tabs --tabs-probe
```

It should create one default-shell tab titled `ORCHESTR8 · Host probe` and emit control JSON. It starts no Codex or role, injects no command, and creates no supervised state. Full `--tabs` intentionally fails closed. Do not use a global/system install or `--break-system-packages`. If the session closes immediately or any partial tab appears, close it and use a fresh target.

## Initialize a project

From a controller source checkout, scaffold an existing Git project:

```sh
python .agent/orchestrate.py init --project-root /path/to/project --task-authority docs/NEXT_PROMPT.md
```

For a new directory, opt in to Git initialization (no commit is made):

```sh
python .agent/orchestrate.py init --project-root /path/to/project --task-authority docs/NEXT_PROMPT.md --init-git
```

Initialization refuses existing controller targets, task-authority path escapes, and internal symlinks in any scaffold destination or parent. A project-root symlink is resolved once to its actual root; no scaffold path may traverse an internal symlink. It preserves `AGENTS.md`, existing project files, and unrelated `.gitignore` entries; it does not invoke roles, create execution history, approve work, or commit. Configure role commands if needed, authorize a bounded task, and create an initial Git commit/`HEAD` before a write-capable cycle.

Run deterministic checks:

```sh
python -m unittest tests.test_orchestrator_safety
python .agent/orchestrate.py --dry-run
```

See `docs/controller/README.md` for configuration, safety, and recovery details.
