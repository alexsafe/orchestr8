# Two-cycle live proof in iTerm2

Run only after the operator authorizes real Coordinator, Developer and Reviewer sessions in a fresh disposable project, two tasks and at most two attempts per task. The only commit is the operator's initial baseline in that project. Leave the source checkout and earlier smoke directories alone. The initial file contents below are a proposed test fixture.

## 1. Prepare the control tab

Use the same signed-in Codex and iTerm2 setup as the successful single-cycle proof. Verify that a fresh role shell can resolve both codex and the reviewed orchestr8 CLI, including ready-developer. An activated environment in the control tab alone does not establish that for a new tab. Replace `/path/to/orchestrator` with the source checkout path. In the iTerm2 control tab:

```sh
source /path/to/orchestrator/.venv/bin/activate
command -v orchestr8 codex
orchestr8 ready-developer --help
smoke_root=$(mktemp -d /private/tmp/orchestr8-two-cycle.XXXXXX)
cd "$smoke_root" && pwd -P
orchestr8 init --init-git --roles coordinator,developer,reviewer
```

Confirm the printed directory is the new smoke target. Init should create scaffolding without opening role tabs. Create the following authority **there**, before the baseline commit:

```sh
cat > docs/NEXT_PROMPT.md <<'TASK'
# Common task
Task 1 is complete when greeting.txt contains exactly two lines, hello then ready, each followed by a newline. Only greeting.txt is in implementation scope. This disposable fixture deliberately exercises a real review finding.

# Developer work
On the initial attempt create greeting.txt containing only the first line. Report the missing second line explicitly as a known issue and submit this partial implementation for review. On an approved correction, complete the missing line and verify the full original criterion. Do not commit.

# Reviewer handoff
Independently inspect the file against the two-line criterion. Report the actual result and any actionable finding. Preserve the project.

# Coordinator work
Coordinate the approved task. After a passing review of task 1, the next roadmap proposal is to create receipt.txt containing exactly one line, verified, followed by a newline, and preserve greeting.txt. Include complete Developer and Reviewer instructions for that task. After task 2 summarize and stop. Keep task 2 out of task 1 implementation.
TASK
git add -- .agent .gitignore docs
git diff --cached --stat
git commit -m 'Establish disposable two-cycle smoke baseline'
git status --short
```

Require an empty final status. Keep the control terminal transcript or copy its outputs outside the target project. Record its path and baseline HEAD (`git rev-parse HEAD`). Never save logs in the monitored project during a run.

## 2. First attempt in three persistent role tabs

Run each control command separately. Before every trigger visually verify the intended tab is idle at the input prompt. After every trigger wait for that role's output before acceptance. A successful send confirms delivery only. Do not also type the trigger phrase yourself.

1. **Control:** `orchestr8 start --tabs --task-limit 2 --attempt-limit 2`. Expect one new Coordinator tab.
2. **Coordinator tab:** type `Start project: Execute the disposable two-cycle smoke task in the approved task snapshot.` Wait for the initial Coordinator report.
3. **Control:** `orchestr8 accept coordinator`, then `orchestr8 launch developer`, then `orchestr8 trigger developer --ready`. Wait for its report. Check `cat greeting.txt` shows only hello.
4. **Control:** `orchestr8 accept developer`, then `orchestr8 launch reviewer`, then `orchestr8 trigger reviewer --ready`. Wait for the review. Run `orchestr8 accept reviewer`. Expect actionable CHANGES_REQUIRED for the missing ready line.
5. **Control:** `orchestr8 trigger coordinator --ready`. Wait for the summary, correction instructions, finding mapping, and approval hint. Run `orchestr8 status` and `orchestr8 proposal`. Save the three recorded destinations from `.agent/runtime/current/tabs.json`.

If the first review approves the file or the actual outcome differs, record the output and stop this scenario. Do not edit a report or introduce a defect mid-run.

## 3. Approve the correction and rerun task 1

Inspect the displayed proposal. Require the original two-line criterion, the specific finding and its mapped correction, and no extra work. Express the approval in Coordinator with `approve next task` per the operator workflow. The human records it in the **control tab** using the exact values just displayed. Replace every placeholder before running:

```text
orchestr8 approve-next --run-id <run-id> --iteration <iteration> --proposal-sha256 <proposal-hash> --scope-sha256 <scope-hash> --confirm-correction-scope
orchestr8 rollover-correction
orchestr8 status
```

Expect task 1, attempt 2, the same task ID and three destinations, fresh report slots, and no send from rollover. In the control tab run this sequence one command at a time. Wait for each role as in step 2. Do not launch any more tabs.

```sh
orchestr8 trigger developer --ready
orchestr8 accept developer
orchestr8 trigger reviewer --ready
orchestr8 accept reviewer
orchestr8 trigger coordinator --ready
```

Developer must obtain a successful attempt- and delivery-specific readiness result before working. Confirm greeting.txt now contains hello and ready and Reviewer approved it. Wait for Coordinator to finish its next-task proposal.

## 4. Approve task 2 and verify the budget stop

Run `orchestr8 proposal`. Inspect the new task and verify it authorizes receipt.txt and preserves greeting.txt. Express approval in Coordinator and record it in the control tab with **this proposal's** values:

```text
orchestr8 approve-next --run-id <run-id> --iteration <iteration> --proposal-sha256 <proposal-hash>
orchestr8 rollover-next-task
orchestr8 status
```

Expect a new task ID, task 2, attempt 1, the same destinations and no dispatch. Repeat the five control commands in step 3, observing each role between commands. Expect receipt.txt containing verified, an APPROVED review, and a Coordinator summary with a stop decision. Run `orchestr8 status`. Confirm there is no eligible next approval. As a negative check run `orchestr8 rollover-next-task` once. Expect structured refusal, no state advancement, and zero additional sends. A summary-only completion may refuse for lack of a proposal. Record the actual reason and use the task number and limit as separate budget evidence. Do not fabricate a third proposal or trigger another role.

## 5. Preserve and assess the evidence

Keep the disposable project and terminal output. Inspect, read-only:

```sh
git rev-parse HEAD
git status --short
cat greeting.txt receipt.txt
ls .agent/runtime/history
cat .agent/runtime/current/tabs.json
orchestr8 status
```

Pass requires three reviewed attempts (001, 002, 003) with verdicts CHANGES_REQUIRED, APPROVED, APPROVED, preserved snapshots and reports, and approval evidence for each rollover. Compare recorded destinations and trigger attempts across the coordination archives and current session: nine confirmed role sends, three per attempt, all to the original three role sessions. Verify task 2 carried greeting.txt forward and added only receipt.txt as Developer work. HEAD must still match the baseline. Record the target path, role IDs, verdicts, approval identities, final status and refusal. Mark the live proof incomplete if any expected branch or evidence is missing.

For an unexpected refusal, retained lock, uncertain delivery or missing report, preserve the target and transcript and inspect status and the intended tab. Never resend blindly, run legacy resume, clear a lock, edit runtime, or start replacement roles to finish this proof.
