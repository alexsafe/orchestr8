# Controller Workflow — Validation

## C1 final evidence

`python -m py_compile .agent/orchestrate.py` — exit `0`.

`python -m unittest tests.test_orchestrator_safety` — `Ran 14 tests in 2.644s`; `OK`.

`python -m unittest` — `Ran 61 tests in 2.493s`; `OK`.

`python .agent/orchestrate.py --dry-run` — exit `0`; printed the configured project root, durable authority, ordered semantic roles, and one-cycle default without dispatching a role.

`git diff --check` — exit `0`.

The controller tests use temporary roots and a deterministic local fake executable. They do not invoke Codex, network services, secrets, or live-provider checks. Coverage includes a real clean temporary-Git full cycle whose configured runtime artifacts are excluded from the user-work baseline; real dirty-Git refusal; fixed role-order rejection; default one-cycle and explicit multi-cycle execution; custom current/history/state and role-asset locations; immutable Developer/Reviewer snapshots; persisted role exit, timeout, missing-output, malformed-JSON, missing-contract, extra-field contract, and malformed-checkpoint stops; hash-bound approval evidence; configuration rejection for non-boolean or non-Developer write capability; read-only Reviewer dispatch; coordinator/developer/reviewer resume and stale-state paths; all secret exclusions in current/history manifests; locks; and immutable history.

Independent review recorded `READY WITH NON-BLOCKING CORRECTIONS` after rerunning the controller suite (`14 tests`), full suite (`61 tests`), `git diff --check`, and controller dry-run. The sole non-blocking README runtime-state path correction is applied; see `REVIEW_REPORT_controller.md`.
