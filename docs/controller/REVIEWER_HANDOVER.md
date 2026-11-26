# Reviewer handover — effective workflow policy checkpoint

**Historical handoff:** This document records an earlier checkpoint; for the later two-cycle live proof, see [validation evidence](VALIDATION_controller.md). Its outstanding-work statements describe that earlier point in time.

You are the independent Orchestr8 Reviewer. Review the current working tree now. Return findings and a bounded verdict to Coordinator in this chat. Coordinator handles human decisions and subsequent Developer instructions.

Read AGENTS.md, docs/NEXT_PROMPT.md and docs/controller/DEVELOPER_POLICY_CHECKPOINT.md. The first handoff defines the complete two-cycle objective. The checkpoint defines this review's acceptance criteria. The last verdict in docs/controller/REVIEW_REPORT_controller.md covers approval and correction rollover only. The dirty diff spans multiple milestones, and the new .agent/workflow_policy.json may be untracked. Inspect the actual files. Treat any supplied Developer report as claims to verify.

## Review work

For the recheck after the NOT READY verdict, start with the four numbered findings under “Current correction attempt” in docs/controller/DEVELOPER_POLICY_CHECKPOINT.md. Inspect the correction diff and affected callers, run the focused tests and required suite once, and retain prior evidence for unaffected behavior. Reopen another checkpoint criterion only if the correction affects it or concrete evidence shows a regression. Keep the report to a verdict, one evidence line per finding, and one validation line. Expand only for an unresolved defect or a specific blocker. Later milestone gaps stay with Coordinator.

1. Trace each decision from policy through the controller gate and the guidance delivered to each role. Inspect hard-coded mappings, status advice, initial and subsequent triggers, and the boundary between proposing and human approval. Identify any path where the controller and an operator following role instructions would make different decisions.
2. Verify policy version, content and effective role instructions bind before first delivery. Follow both rollover paths and legacy resume. Check that drift, missing identity and unsupported versions refuse before dispatch, publication or progression, with prior evidence preserved. Distinguish a rejection caused by generic project drift from a test of the policy guard itself.
3. Inspect tests/test_orchestrator_safety.py. Verify the two-task fixture carries the original identity through a correction and a next task. Check that the init test actually exercises the installed controller and all three roles' guidance in a disposable project. Distinguish assertions about file presence from assertions about behavior.
4. Independently run focused regressions and the explicit suite with python -m unittest tests.test_orchestrator_safety, plus the compile, diff and applicable CLI help checks listed in the active handoff. Use local deterministic fixtures and fake delivery only. Record exact commands, exit codes and counts. Historical red-test evidence can be attributed to the Developer if supplied. Report missing evidence explicitly.

This is manual maintenance review. Preserve the checkout. Leave production files, source .agent/runtime, prior smoke targets and historical reports untouched. No role launches, live smoke, network, commits or worktrees.

## Return to Coordinator

Lead with READY — policy checkpoint only, or NOT READY — policy checkpoint. Give file/line references, impact and the minimum correction for each finding. Map every checkpoint criterion to observed code and test evidence. If review cannot finish, identify the exact blocking command or missing evidence and which checks remain. Acknowledgement alone leaves review pending.

Keep full-feature readiness open. Correction scope and findings binding, a recorded proposal-stage human stop, the outstanding CLI and failure matrix, and independent full two-cycle review remain separate gates. Only the single-cycle path has recorded live proof.
