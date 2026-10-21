# Local Workflow Controller

A small, local Coordinator → Developer → Reviewer controller for bounded coding work.

It snapshots one configured durable task authority, keeps Developer write access separate from a read-only Reviewer, records structured safe stops, and defaults to one cycle. It does not commit, push, use a network, or invoke work automatically.

## Setup

Edit `.agent/controller_config.json` for this project, then initialize `.agent/runtime/state.json` with:

```json
{"iteration": 0, "status": "READY"}
```

Run deterministic checks:

```sh
python -m unittest tests.test_orchestrator_safety
python .agent/orchestrate.py --dry-run
```

See `docs/controller/README.md` for configuration, safety, and recovery details.
