# Controller Workflow — Validation

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
