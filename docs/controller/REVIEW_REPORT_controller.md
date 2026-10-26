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
