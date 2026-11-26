from __future__ import annotations

import contextlib
import builtins
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("orchestrator", ROOT / ".agent" / "orchestrate.py")
assert SPEC and SPEC.loader
ORCHESTRATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORCHESTRATOR)

def fake_trigger_iterm(app, response_status=None):
    async def send(connection, session_id, value, suppress_broadcast):
        application = await app(connection)
        session = next(s for w in application.terminal_windows for t in w.tabs for s in t.sessions if s.session_id == session_id)
        await session.async_send_text(value, suppress_broadcast=suppress_broadcast)
        status = response_status(value) if response_status else 0
        message = types.SimpleNamespace(status=status, HasField=lambda name: status is not None)
        return types.SimpleNamespace(send_text_response=message, HasField=lambda name: True)
    status_enum = types.SimpleNamespace(Name=lambda value: {0:"OK", 1:"SESSION_NOT_FOUND"}[value])
    return types.SimpleNamespace(async_get_app=app, run_until_complete=lambda main: __import__("asyncio").run(main(None)), rpc=types.SimpleNamespace(async_send_text=send), api_pb2=types.SimpleNamespace(SendTextResponse=types.SimpleNamespace(OK=0, Status=status_enum)))


class OrchestratorSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.label_patch = mock.patch.object(ORCHESTRATOR, "update_role_label", return_value={"status":"updated"}); self.label_mock = self.label_patch.start()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve(); self.agent = self.root / ".runtime"
        (self.root / ".agent").mkdir(); (self.root / ".agent" / "workflow_policy.json").write_bytes((ROOT / ".agent" / "workflow_policy.json").read_bytes())
        self.old_config, self.old_argv, self.old_clean = ORCHESTRATOR.CONFIG_PATH, sys.argv, ORCHESTRATOR.clean_baseline
        (self.root / "tasks").mkdir(); (self.root / "tasks" / "authority.md").write_text("task-one\n")
        self.write_json(self.root / "approvals.json", {"approvals": []})
        for role in ("coordinator", "developer", "reviewer"):
            path = self.root / "assets" / f"{role}.md"; path.parent.mkdir(exist_ok=True); path.write_text(role)
            (self.root / "contracts").mkdir(exist_ok=True); (self.root / "contracts" / f"{role}.json").write_text((ROOT / ".agent" / "schemas" / f"{role}.json").read_text())
        self.fake = self.root / "custom-bin" / "fake.py"; self.fake.parent.mkdir()
        self.fake.write_text(
            "import json,sys,time\nfrom pathlib import Path\n"
            "out=Path(sys.argv[sys.argv.index('-o')+1]); role=out.stem[1:]; mode=(out.parent/'mode').read_text() if (out.parent/'mode').exists() else ''\n"
            "(out.parent/'calls').open('a').write(role+'|sandbox='+sys.argv[sys.argv.index('-s')+1]+'|'+sys.argv[-1]+'\\n---\\n')\n"
            "if mode==role+'-exit': raise SystemExit(7)\n"
            "if mode==role+'-timeout': time.sleep(2)\n"
            "if mode==role+'-missing': raise SystemExit(0)\n"
            "if mode==role+'-json': out.write_text('{bad'); raise SystemExit(0)\n"
            "if mode==role+'-contract': out.write_text('{}'); raise SystemExit(0)\n"
            "base={'human_category':None}; p={'coordinator':dict(base,status='CONTINUE',summary='go',next_prompt=None,human_reason=None),'developer':dict(base,status='DONE',summary='done',files_changed=[],validation=[],known_issues=[],commit_or_diff_reference=None,self_check=[]),'reviewer':dict(base,verdict='APPROVED',summary='ok',findings=[],evidence=[],human_reason=None)}\n"
            "if mode==role+'-extra': p[role]['unexpected']='nope'\n"
            "if mode==role+'-escalation': p[role].update(verdict='APPROVED',human_reason='unexpected diff',human_category='unsafe_or_unexpected_diff')\n"
            "out.write_text(json.dumps(p[role]))\n"
        )
        self.write_config(); ORCHESTRATOR.CONFIG_PATH = self.agent / "controller.json"; ORCHESTRATOR.clean_baseline = lambda root, history: ("test-head", {})

    def tearDown(self) -> None:
        self.label_patch.stop()
        ORCHESTRATOR.CONFIG_PATH, sys.argv, ORCHESTRATOR.clean_baseline = self.old_config, self.old_argv, self.old_clean
        self.temp.cleanup()

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))

    def write_config(self, *, paths: dict | None = None, timeout: int = 1) -> None:
        paths = paths or {"current": ".runtime/current", "history": ".runtime/history", "state": ".runtime/state.json"}
        roles = []
        for name, writable in (("coordinator", False), ("developer", True), ("reviewer", False)):
            roles.append({"name": name, "instruction": f"assets/{name}.md", "command": [sys.executable, str(self.fake)], "session_command": ["fake-session", name], "schema": f"contracts/{name}.json", "write_capable": writable})
        self.write_json(self.agent / "controller.json", {"tab_host":"iterm2", "task_authority": "tasks/authority.md", "approval_record": "approvals.json", "paths": paths, "role_timeout_seconds": timeout, "roles": roles})
        self.write_json(self.root / paths["state"], {"iteration": 0, "max_iterations": 5, "status": "READY"})

    def locations(self):
        config, root = ORCHESTRATOR.load_config(); return config, root, ORCHESTRATOR.locations(root, config)

    def current(self) -> Path:
        return self.locations()[2][2]

    def write_correction_scope(self, args, change: str) -> str:
        root, config, authority, approval, current, history, state_path = args
        state = json.loads(state_path.read_text()); iteration = state["iteration"]; origin = iteration - state["attempt"] + 1
        archived = history / f"{iteration:03d}"; session = json.loads((archived / "supervised_session.json").read_text())
        review = json.loads((archived / session.get("report_slots", {}).get("reviewer", ".reviewer.json")).read_text())
        original = (history / f"{origin:03d}" / "authoritative_task.md").read_text()
        (current / "coordinator_proposal.md").write_text(original + "\n" + change + "\n")
        mapping = [{"finding_index":i, "finding_sha256":ORCHESTRATOR.digest(finding.encode()), "change":change} for i,finding in enumerate(review["findings"]) if finding.strip()]
        scope = {"task_id":state["task_id"], "original_snapshot_sha256":ORCHESTRATOR.digest(original.encode()), "original_iteration":origin, "predecessor_iteration":iteration, "review_sha256":ORCHESTRATOR.digest((archived / "review_report.md").read_bytes()), "criteria_changes":[], "findings":mapping}
        self.write_json(current / "correction_scope.json", scope)
        return original + "\n" + change + "\n"

    def state(self) -> dict:
        return json.loads(self.locations()[2][4].read_text())

    def write_legacy_state(self, state_path: Path, current: Path, config: dict, state: dict) -> None:
        identity, policy = ORCHESTRATOR.effective_policy(self.root, config)
        current.mkdir(parents=True, exist_ok=True)
        (current / "workflow_policy.json").write_bytes(policy); self.write_json(current / "effective_policy.json", identity)
        state["effective_policy"] = identity; self.write_json(state_path, state)

    def run_controller(self, *args: str) -> None:
        sys.argv = ["orchestrate.py", *args]
        self.assertEqual(ORCHESTRATOR.main(), 0)

    def set_mode(self, mode: str) -> None:
        self.current().mkdir(parents=True, exist_ok=True); (self.current() / "mode").write_text(mode)

    def assert_stop(self, category: str) -> None:
        self.assertEqual(self.state()["status"], "HUMAN_REQUIRED")
        history = self.locations()[2][3] / "001" / "human_stop.json"
        stop = json.loads(history.read_text()); self.assertEqual(stop["category"], category, stop)

    def test_complete_cycle_uses_custom_paths_assets_and_same_snapshot(self) -> None:
        self.write_config(paths={"current": "run-data/live", "history": "run-data/archive", "state": "run-data/state.json"})
        ORCHESTRATOR.clean_baseline = self.old_clean
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True); subprocess.run(["git", "add", "."], cwd=self.root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=self.root, check=True)
        self.run_controller()
        config, _, (_, _, current, history, _) = self.locations()
        calls = (current / "calls").read_text()
        self.assertIn("developer|", calls); self.assertIn("reviewer|", calls); self.assertEqual((history / "001" / "task_snapshot.json").is_file(), True)
        self.assertIn("task-one", calls)
        self.assertIn("developer|sandbox=workspace-write", calls); self.assertIn("reviewer|sandbox=read-only", calls)
        self.assertEqual(config["roles"][1]["instruction"], "assets/developer.md")

    def test_missing_authority_stops_and_archives(self) -> None:
        (self.root / "tasks" / "authority.md").unlink(); self.run_controller(); self.assert_stop("stale_or_mismatched_task_state")

    def test_dirty_git_baseline_is_real_behavior(self) -> None:
        ORCHESTRATOR.clean_baseline = self.old_clean
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True); subprocess.run(["git", "add", "."], cwd=self.root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=self.root, check=True)
        (self.root / "dirty").write_text("x"); self.run_controller(); self.assert_stop("unsafe_or_unexpected_diff")

    def test_role_failures_persist_for_exit_timeout_missing_json_and_contract(self) -> None:
        for suffix in ("exit", "timeout", "missing", "json", "contract"):
            with self.subTest(suffix=suffix):
                self.set_mode(f"developer-{suffix}"); self.run_controller(); self.assert_stop("indeterminate_write_invocation")
                stop = json.loads((self.locations()[2][3] / "001" / "human_stop.json").read_text())
                self.assertEqual(stop["phase"], "developer")
                self.tearDown(); self.setUp()

    def test_extra_output_fields_fail_closed_for_each_role(self) -> None:
        expected = {"coordinator": "failed_or_incomplete_validation", "developer": "indeterminate_write_invocation", "reviewer": "failed_or_incomplete_validation"}
        for name, category in expected.items():
            with self.subTest(role=name):
                self.set_mode(f"{name}-extra"); self.run_controller(); self.assert_stop(category)
                self.tearDown(); self.setUp()

    def test_capability_configuration_rejects_invalid_roles(self) -> None:
        for role_name, value in (("coordinator", True), ("reviewer", True), ("developer", "yes")):
            with self.subTest(role=role_name, value=value):
                config = json.loads((self.agent / "controller.json").read_text())
                next(role for role in config["roles"] if role["name"] == role_name)["write_capable"] = value
                self.write_json(self.agent / "controller.json", config)
                with self.assertRaisesRegex(RuntimeError, "write-capable|malformed"):
                    ORCHESTRATOR.load_config()
                self.tearDown(); self.setUp()

    def test_malformed_saved_developer_checkpoint_stops_and_never_repeats(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        (current / ".developer.json").write_text("{bad")
        self.write_legacy_state(state_path, current, config, {"iteration": 0, "active_iteration": 1, "phase": "developer", "config_sha256": config["_sha256"], "task_snapshot_sha256": meta["sha256"]})
        self.run_controller("--resume"); self.assert_stop("indeterminate_write_invocation"); self.assertFalse((current / "calls").exists())

    def test_developer_and_reviewer_resume_paths(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        self.write_json(current / ".developer.json", {"status":"DONE","summary":"done","files_changed":[],"validation":[],"known_issues":[],"self_check":[],"commit_or_diff_reference":None,"human_category":None})
        self.write_legacy_state(state_path, current, config, {"iteration":0,"active_iteration":1,"phase":"developer","config_sha256":config["_sha256"],"task_snapshot_sha256":meta["sha256"]})
        self.run_controller("--resume"); self.assertEqual(self.state()["status"], "READY")
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED","summary":"ok","findings":[],"evidence":[],"human_reason":None,"human_category":None})
        self.write_legacy_state(state_path, current, config, {"iteration":0,"active_iteration":1,"phase":"reviewer","config_sha256":config["_sha256"],"task_snapshot_sha256":meta["sha256"]})
        self.run_controller("--resume"); self.assertEqual(self.state()["status"], "READY")

    def test_approval_record_refuses_then_archives_matching_approval(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); old = ORCHESTRATOR.digest(b"old")
        self.write_json(state_path, {"iteration":0,"status":"READY","last_authority_sha256":old})
        self.run_controller(); self.assert_stop("stale_or_mismatched_task_state")
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); old = ORCHESTRATOR.digest(b"old"); new = ORCHESTRATOR.digest(authority.read_bytes())
        self.write_json(approval, {"approvals":[{"prior_authority_sha256":old,"new_authority_sha256":new,"approved_at":"2026-10-19T00:00:00Z"}]})
        self.write_json(state_path, {"iteration":0,"status":"READY","last_authority_sha256":old}); self.run_controller()
        evidence = json.loads((history / "001" / "approval_evidence.json").read_text()); self.assertEqual(evidence["approval"]["new_authority_sha256"], new)

    def test_stale_current_and_snapshot_stop(self) -> None:
        self.current().mkdir(parents=True); (self.current() / "next_prompt.md").write_text("old"); self.run_controller(); self.assert_stop("stale_or_mismatched_task_state")

    def test_stale_coordinator_and_reviewer_checkpoints_stop_safely(self) -> None:
        current = self.current(); current.mkdir(parents=True)
        (current / ".coordinator.json").write_text("{bad")
        config, _, (_, _, _, _, state_path) = self.locations()
        self.write_legacy_state(state_path, current, config, {"iteration":0,"active_iteration":1,"phase":"coordinator","config_sha256":config["_sha256"]})
        self.run_controller("--resume"); self.assert_stop("failed_or_incomplete_validation")
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        self.write_legacy_state(state_path, current, config, {"iteration":0,"active_iteration":1,"phase":"reviewer","config_sha256":config["_sha256"],"task_snapshot_sha256":meta["sha256"]})
        authority.write_text("changed")
        self.run_controller("--resume"); self.assert_stop("stale_or_mismatched_task_state")

    def test_secret_sanitation_current_and_history_all_patterns(self) -> None:
        current = self.current(); history = self.locations()[2][3]; current.mkdir(parents=True); (history / "001").mkdir(parents=True)
        payload = {"ok":"x", ".env":"x", ".env.local":"x", "secrets/value":"x", "token.key":"x"}
        self.write_json(current / "baseline.json", payload); self.write_json(history / "001" / "after_developer.json", payload)
        ORCHESTRATOR.sanitize_existing(current, history)
        self.assertEqual(json.loads((current / "baseline.json").read_text()), {"ok":"x"}); self.assertEqual(json.loads((history / "001" / "after_developer.json").read_text()), {"ok":"x"})

    def test_lock_and_multi_cycle_cli_contract(self) -> None:
        lock = ORCHESTRATOR.acquire_lock(self.agent)
        with self.assertRaisesRegex(RuntimeError, "lock exists"): ORCHESTRATOR.acquire_lock(self.agent)
        lock.unlink(); sys.argv = ["orchestrate.py", "--max-iterations", "2"]
        with self.assertRaises(SystemExit) as error: ORCHESTRATOR.main()
        self.assertEqual(error.exception.code, 2)

    def test_fixed_role_order_is_enforced_and_multi_cycle_executes(self) -> None:
        config = json.loads((self.agent / "controller.json").read_text()); config["roles"][0], config["roles"][1] = config["roles"][1], config["roles"][0]
        self.write_json(self.agent / "controller.json", config)
        with self.assertRaisesRegex(RuntimeError, "role order"): ORCHESTRATOR.load_config()
        self.tearDown(); self.setUp(); self.run_controller(); self.run_controller("--multi-cycle", "--max-iterations", "2")
        self.assertEqual(self.state()["iteration"], 3)

    def test_supervised_role_parsing_tabs_and_handoff_artifacts(self) -> None:
        self.assertEqual(ORCHESTRATOR.parse_roles("coord,dev,review"), ["coordinator", "developer", "reviewer"])
        for value in ("developer,coordinator,reviewer", "coord,dev,dev", "coord,unknown,review"):
            with self.assertRaises(RuntimeError): ORCHESTRATOR.parse_roles(value)
        config, root, (authority, approval, current, history, state_path) = self.locations(); launched = []
        ORCHESTRATOR.supervised_init(root, config, current, True, launched.append)
        self.assertEqual([item["role"] for item in launched], ["coordinator", "developer", "reviewer"])
        self.assertEqual(launched[0]["cwd"], str(root)); self.assertEqual([item["sandbox"] for item in launched], ["read-only", "workspace-write", "read-only"]); self.assertFalse((current / "calls").exists())
        self.write_legacy_state(state_path, current, config, json.loads(state_path.read_text()))
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"go","next_prompt":None,"human_reason":None,"human_category":None})
        ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator")
        session = json.loads((current / "supervised_session.json").read_text()); self.assertEqual(session["phase"], "developer")
        self.write_json(current / ".developer.json", {"status":"DONE","summary":"done","files_changed":[],"validation":[],"known_issues":[],"self_check":[],"commit_or_diff_reference":None,"human_category":None})
        ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer")
        self.assertIn(session["task_snapshot_sha256"], (current / "task_snapshot.json").read_text()); self.assertTrue((current / "dev_report.md").is_file())
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED","summary":"ok","findings":[],"evidence":[],"human_reason":None,"human_category":None})
        ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer")
        self.assertTrue((current / "review_report.md").is_file()); self.assertTrue((history / "001" / "review_report.md").is_file())
        self.assertEqual(json.loads((current / "supervised_session.json").read_text())["phase"], "coordinator_review")

    def test_supervised_tab_launch_failure_creates_no_runtime_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations()
        def fail(_: dict) -> None: raise RuntimeError("fake launcher failed")
        with self.assertRaisesRegex(RuntimeError, "stopped safely"): ORCHESTRATOR.supervised_init(root, config, current, True, fail)
        self.assertFalse(current.exists())

    def test_iterm_tab_applescript_uses_fake_runner_and_unicode_safe_source(self) -> None:
        spec = {
            "role": "reviewer", "title": 'ORCHESTR8 · Reviewer · quote "title"',
            "cwd": '/tmp/project · with "quotes"',
            "instruction": '/tmp/role · "reviewer".md',
            "command": ['fake session', '--profile=unit test', 'quote"argument'],
            "sandbox": "read-only",
        }
        calls = []
        def fake_osascript(arguments, **kwargs):
            calls.append((arguments, kwargs)); return subprocess.CompletedProcess(arguments, 0, "", "")
        spec["host"] = "iterm2"; ORCHESTRATOR.launch_iterm_tab(spec, fake_osascript, platform="darwin")
        self.assertEqual(len(calls), 1)
        arguments, kwargs = calls[0]; self.assertEqual(arguments[:2], ["osascript", "-e"])
        self.assertEqual(kwargs, {"text": True, "capture_output": True})
        source = arguments[2]
        self.assertIn('ORCHESTR8 · Reviewer', source); self.assertNotIn(r"\u00b7", source)
        self.assertIn('\'fake session\' \'--profile=unit test\' \'quote\\"argument\'', source)
        self.assertIn('\\"quotes\\"', source); self.assertIn('\\"reviewer\\"', source)
        self.assertIn(" -C ", source); self.assertIn(" -s read-only ", source)
        self.assertNotIn("--skip-git-repo-check", source)
        self.assertIn('tell application "iTerm2"', source); self.assertIn("set targetWindow to front window", source)
        self.assertIn("create tab with default profile command", source); self.assertIn("tell targetWindow", source)
        self.assertIn("set tabCountBefore to count of tabs", source)
        self.assertIn("repeat 10 times", source); self.assertIn("delay 0.1", source)
        self.assertIn("readinessStartedAt to current date", source); self.assertIn("elapsed_seconds=", source)
        self.assertIn("iTerm2 tab readiness failed pre_count=", source); self.assertIn("close partial probe tabs", source)
        bootstrap = ORCHESTRATOR.interactive_session_command(spec)
        self.assertIn("printf '\\033]0;%s\\007' 'ORCHESTR8 · Reviewer · quote \"title\"'", bootstrap)
        self.assertIn("launch_status=$?", bootstrap); self.assertIn("inspection shell remains open", bootstrap)
        self.assertNotIn("launchedTab", source); self.assertNotIn("current session of launchedTab", source); self.assertNotIn("title of launchedTab", source)
        self.assertNotIn("Terminal", source); self.assertNotIn("do script", source); self.assertNotIn("move launchedTab", source)
        self.assertNotIn("selected tab of front window", source)

    def test_unsupported_tab_host_fails_closed_before_runtime_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations(); config["tab_host"] = "terminal"
        with self.assertRaisesRegex(RuntimeError, "full --tabs launch is unavailable"):
            ORCHESTRATOR.supervised_init(root, config, current, True)
        self.assertFalse(current.exists())

    def test_iterm_launch_failure_creates_no_supervised_runtime_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations(); calls = []
        def failed_osascript(arguments, **kwargs):
            calls.append((arguments, kwargs)); return subprocess.CompletedProcess(arguments, 1, "", "iTerm2 unavailable")
        def launcher(spec): ORCHESTRATOR.launch_iterm_tab(spec, failed_osascript, platform="darwin")
        with self.assertRaisesRegex(RuntimeError, "stopped safely.*iTerm2 tab launch failed"):
            ORCHESTRATOR.supervised_init(root, config, current, True, launcher)
        self.assertEqual(len(calls), 1); self.assertFalse(current.exists())

    def test_later_iterm_launch_failure_leaves_no_supervised_runtime_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations(); launched = []
        def launcher(spec):
            launched.append(spec["role"])
            if spec["role"] == "developer": raise RuntimeError("iTerm2 tab confirmation failed")
        with self.assertRaisesRegex(RuntimeError, "stopped safely.*confirmation failed"):
            ORCHESTRATOR.supervised_init(root, config, current, True, launcher)
        self.assertEqual(launched, ["coordinator", "developer"]); self.assertFalse(current.exists())

    def test_tabs_probe_creates_one_non_role_tab_without_supervised_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations(); launched = []
        ORCHESTRATOR.supervised_init(root, config, current, True, launched.append, tabs_probe=True)
        self.assertEqual(len(launched), 1); spec = launched[0]
        self.assertEqual(spec["title"], "ORCHESTR8 · Host probe"); self.assertTrue(spec["probe"]); self.assertEqual(spec["command"], [])
        command = ORCHESTRATOR.interactive_session_command(spec)
        self.assertIn("No role or workflow was started.", command); self.assertIn("command -v codex", command)
        self.assertFalse(current.exists())

    def test_native_probe_bridge_validates_success_and_failures(self) -> None:
        spec = {"host":"iterm2", "probe":True, "title":"ORCHESTR8 · Host probe", "cwd":"/tmp/probe", "instruction":"", "command":[], "sandbox":"read-only"}
        calls = []
        def success(arguments, **kwargs):
            calls.append((arguments, kwargs)); return subprocess.CompletedProcess(arguments, 0, '{"ok":true,"host":"iterm2","window":"w","tab":"t","session":"s","elapsed_seconds":0.1,"reason":"confirmed"}', "")
        result = ORCHESTRATOR.launch_iterm_probe(spec, success)
        self.assertEqual(result["tab"], "t"); self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0][1]["input"]), {"title":"ORCHESTR8 · Host probe", "mode":"default_profile_tab_only"})
        for completed, message in ((subprocess.CompletedProcess([], 0, "not-json", ""), "malformed diagnostics"), (subprocess.CompletedProcess([], 0, '{"ok":false,"reason":"API disabled"}', ""), "API disabled"), (subprocess.CompletedProcess([], 1, "", "bridge failed"), "native iTerm2 probe failed")):
            with self.subTest(message=message):
                def fake(*_args, response=completed, **_kwargs): return response
                with self.assertRaisesRegex(RuntimeError, message): ORCHESTRATOR.launch_iterm_probe(spec, fake)

    def test_native_probe_module_uses_default_tab_and_structured_failures(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"
        def run(fake_iterm, request='{ "mode": "default_profile_tab_only", "title": "ORCHESTR8 · Host probe" }'):
            original_module, original_stdin = sys.modules.get("iterm2"), sys.stdin; output = io.StringIO()
            sys.modules["iterm2"] = fake_iterm; sys.stdin = io.StringIO(request)
            try:
                with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
            finally:
                sys.stdin = original_stdin
                if original_module is None: del sys.modules["iterm2"]
                else: sys.modules["iterm2"] = original_module
            return json.loads(output.getvalue())
        class Tab:
            tab_id = "tab"; titled = None
            async def async_set_title(self, title): self.titled = title
        class Window:
            window_id = "window"
            async def async_create_tab(self): return tab
        tab = Tab(); window = Window()
        async def get_app(_): return types.SimpleNamespace(current_terminal_window=window)
        def complete(main): return __import__("asyncio").run(main(None))
        fake = types.SimpleNamespace(async_get_app=get_app, run_until_complete=complete)
        success = run(fake); self.assertTrue(success["ok"]); self.assertEqual(tab.titled, "ORCHESTR8 · Host probe")
        window.async_create_tab = lambda: (_ for _ in ()).throw(RuntimeError("unused"))
        async def none(): return None
        window.async_create_tab = none; self.assertIn("closed immediately", run(fake)["reason"])
        class BrokenTab(Tab):
            async def async_set_title(self, title): raise RuntimeError("title failed")
        async def broken_create(): return BrokenTab()
        window.async_create_tab = broken_create; self.assertIn("title failed", run(fake)["reason"])
        self.assertIn("malformed native probe request", run(fake, "{")["reason"])
        original_import, original_stdin = builtins.__import__, sys.stdin
        def missing_iterm2(name, *args, **kwargs):
            if name == "iterm2": raise ImportError("fake missing module")
            return original_import(name, *args, **kwargs)
        output = io.StringIO(); builtins.__import__ = missing_iterm2; sys.stdin = io.StringIO('{"mode":"default_profile_tab_only","title":"ORCHESTR8 · Host probe"}')
        try:
            with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
        finally:
            builtins.__import__ = original_import; sys.stdin = original_stdin
        self.assertIn("module unavailable", json.loads(output.getvalue())["reason"])

    def test_native_layout_probe_module_creates_only_three_titled_default_tabs(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"
        titles = ["ORCHESTR8 · Coordinator", "ORCHESTR8 · Developer", "ORCHESTR8 · Reviewer"]
        request = json.dumps({"mode":"layout_default_profile_tabs", "titles":titles})
        def run(create_failure=None, create_error=None, title_failure=None, malformed=False):
            created, output, original_module, original_stdin = [], io.StringIO(), sys.modules.get("iterm2"), sys.stdin
            class Tab:
                def __init__(self, step): self.step, self.tab_id = step, f"tab-{step}"
                async def async_set_title(self, title):
                    if self.step == title_failure: raise RuntimeError(f"title-{self.step}")
                    self.title = title
            class Window:
                window_id = "window-1"
                async def async_create_tab(self):
                    step = len(created) + 1
                    if step == create_error: raise RuntimeError(f"create-{step}")
                    if step == create_failure: return None
                    tab = Tab(step); created.append(tab); return tab
            async def get_app(_): return types.SimpleNamespace(current_terminal_window=Window())
            def complete(main): return __import__("asyncio").run(main(None))
            sys.modules["iterm2"] = types.SimpleNamespace(async_get_app=get_app, run_until_complete=complete)
            sys.stdin = io.StringIO("{}" if malformed else request)
            try:
                with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
            finally:
                sys.stdin = original_stdin
                if original_module is None: del sys.modules["iterm2"]
                else: sys.modules["iterm2"] = original_module
            return json.loads(output.getvalue()), created
        response, created = run()
        self.assertTrue(response["ok"]); self.assertEqual(response["window"], "window-1"); self.assertEqual(response["tabs"], ["tab-1", "tab-2", "tab-3"]); self.assertEqual(response["result"], "confirmed")
        self.assertEqual([tab.title for tab in created], titles)
        for step in range(1, 4):
            with self.subTest(kind="creation", step=step):
                response, created = run(create_failure=step)
                self.assertFalse(response["ok"]); self.assertIn(f"layout step {step}", response["reason"]); self.assertIn("partial tabs", response["reason"]); self.assertEqual(len(created), step - 1)
            with self.subTest(kind="creation error", step=step):
                response, created = run(create_error=step)
                self.assertFalse(response["ok"]); self.assertIn(f"layout step {step}", response["reason"]); self.assertIn("partial tabs", response["reason"]); self.assertEqual(len(created), step - 1)
            with self.subTest(kind="title", step=step):
                response, created = run(title_failure=step)
                self.assertFalse(response["ok"]); self.assertIn(f"layout step {step}", response["reason"]); self.assertIn("partial tabs", response["reason"]); self.assertEqual(len(created), step)
        response, _ = run(malformed=True); self.assertIn("malformed native probe request", response["reason"])

    def test_layout_probe_controller_boundary_and_no_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations(); calls = []
        expected = {"ok":True, "window":"w", "tabs":["a", "b", "c"], "elapsed_seconds":0.1, "result":"confirmed"}
        ORCHESTRATOR.supervised_init(root, config, current, True, calls.append, tabs_layout_probe=True)
        self.assertEqual(len(calls), 1); self.assertTrue(calls[0]["layout_probe"]); self.assertEqual(calls[0]["command"], []); self.assertEqual(calls[0]["titles"], ["ORCHESTR8 · Coordinator", "ORCHESTR8 · Developer", "ORCHESTR8 · Reviewer"]); self.assertFalse(current.exists())
        def success(arguments, **kwargs):
            self.assertEqual(json.loads(kwargs["input"]), {"mode":"layout_default_profile_tabs", "titles":["ORCHESTR8 · Coordinator", "ORCHESTR8 · Developer", "ORCHESTR8 · Reviewer"]})
            return subprocess.CompletedProcess(arguments, 0, json.dumps(expected), "")
        self.assertEqual(ORCHESTRATOR.launch_iterm_layout_probe({}, success), expected)
        for completed, message in ((subprocess.CompletedProcess([], 1, "", "bridge failed"), "native iTerm2 layout probe failed"), (subprocess.CompletedProcess([], 0, "not-json", ""), "malformed diagnostics"), (subprocess.CompletedProcess([], 0, '{"ok":false,"reason":"step failed"}', ""), "step failed"), (subprocess.CompletedProcess([], 0, '{"ok":true,"window":"w","tabs":["a"],"elapsed_seconds":0,"result":"confirmed"}', ""), "incomplete confirmation"), (subprocess.CompletedProcess([], 0, '{"ok":true,"window":"w","tabs":["a","a","c"],"elapsed_seconds":0,"result":"confirmed"}', ""), "incomplete confirmation")):
            with self.subTest(message=message):
                with self.assertRaisesRegex(RuntimeError, message): ORCHESTRATOR.launch_iterm_layout_probe({}, lambda *_args, response=completed, **_kwargs: response)

    def test_native_coordinator_bootstrap_probe_delivers_one_safe_command(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"
        request = json.dumps({"mode":"coordinator_bootstrap", "cwd":"/tmp/project with spaces"})
        expected_command = "codex -C '/tmp/project with spaces' -s read-only 'Read .agent/roles/coordinator.md. Write no artifact. Wait for a human Start project: <human initial brief> message.'\n"
        def run(app_none=False, app_error=False, window_none=False, window_error=False, create_none=False, create_error=False, title_error=False, session_none=False, session_error=False, send_error=False, malformed=False):
            output, original_module, original_stdin, sent = io.StringIO(), sys.modules.get("iterm2"), sys.stdin, []
            class Session:
                session_id = "session-1"
                async def async_send_text(self, command):
                    sent.append(command)
                    if send_error: raise RuntimeError("send failed")
            class Tab:
                tab_id = "tab-1"
                async def async_set_title(self, title):
                    self.title = title
                    if title_error: raise RuntimeError("title failed")
                @property
                def current_session(self):
                    if session_error: raise RuntimeError("session failed")
                    return None if session_none else Session()
            class Window:
                window_id = "window-1"
                async def async_create_tab(self):
                    if create_error: raise RuntimeError("create failed")
                    return None if create_none else tab
            tab = Tab()
            class App:
                @property
                def current_terminal_window(self):
                    if window_error: raise RuntimeError("window failed")
                    return None if window_none else Window()
            async def get_app(_):
                if app_error: raise RuntimeError("app failed")
                return None if app_none else App()
            def complete(main): return __import__("asyncio").run(main(None))
            sys.modules["iterm2"] = types.SimpleNamespace(async_get_app=get_app, run_until_complete=complete)
            sys.stdin = io.StringIO("{}" if malformed else request)
            try:
                with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
            finally:
                sys.stdin = original_stdin
                if original_module is None: del sys.modules["iterm2"]
                else: sys.modules["iterm2"] = original_module
            return json.loads(output.getvalue()), tab, sent
        response, tab, sent = run()
        self.assertTrue(response["ok"]); self.assertEqual((response["window"], response["tab"], response["session"]), ("window-1", "tab-1", "session-1")); self.assertEqual(response["result"], "unverified_bootstrap_delivered")
        self.assertEqual(tab.title, "ORCHESTR8 · Coordinator · bootstrap probe"); self.assertEqual(sent, [expected_command]); self.assertNotIn("--skip-git-repo-check", sent[0])
        for kwargs, step in (({"app_none":True}, "app discovery"), ({"app_error":True}, "app discovery"), ({"window_none":True}, "preflight"), ({"window_error":True}, "active-window discovery"), ({"create_none":True}, "tab creation"), ({"create_error":True}, "tab creation"), ({"title_error":True}, "title"), ({"session_none":True}, "session retrieval"), ({"session_error":True}, "session retrieval"), ({"send_error":True}, "command delivery")):
            with self.subTest(step=step, kwargs=kwargs):
                response, _, sent = run(**kwargs)
                self.assertFalse(response["ok"]); self.assertIn(step, response["reason"]); self.assertIn("partial tabs", response["reason"]); self.assertLessEqual(len(sent), 1)
        response, _, _ = run(malformed=True); self.assertIn("malformed native probe request", response["reason"])

    def test_coordinator_bootstrap_controller_boundary_and_no_state(self) -> None:
        config, root, (_, _, current, _, _) = self.locations(); calls = []
        expected = {"ok":True, "window":"w", "tab":"t", "session":"s", "elapsed_seconds":0.1, "result":"unverified_bootstrap_delivered"}
        ORCHESTRATOR.supervised_init(root, config, current, True, calls.append, tabs_coordinator_bootstrap_probe=True)
        self.assertEqual(len(calls), 1); self.assertTrue(calls[0]["coordinator_bootstrap_probe"]); self.assertEqual(calls[0]["command"], []); self.assertEqual(calls[0]["sandbox"], "read-only"); self.assertFalse(current.exists())
        def success(arguments, **kwargs):
            self.assertEqual(json.loads(kwargs["input"]), {"mode":"coordinator_bootstrap", "cwd":"/tmp/project"})
            return subprocess.CompletedProcess(arguments, 0, json.dumps(expected), "")
        self.assertEqual(ORCHESTRATOR.launch_iterm_coordinator_bootstrap_probe({"cwd":"/tmp/project"}, success), expected)
        for completed, message in ((subprocess.CompletedProcess([], 1, "", "bridge failed"), "native Coordinator bootstrap probe failed"), (subprocess.CompletedProcess([], 0, "not-json", ""), "malformed diagnostics"), (subprocess.CompletedProcess([], 0, '{"ok":false,"reason":"send failed"}', ""), "send failed"), (subprocess.CompletedProcess([], 0, '{"ok":true,"window":"w","tab":"t","elapsed_seconds":0,"result":"unverified_bootstrap_delivered"}', ""), "incomplete delivery")):
            with self.subTest(message=message):
                with self.assertRaisesRegex(RuntimeError, message): ORCHESTRATOR.launch_iterm_coordinator_bootstrap_probe({"cwd":"/tmp/project"}, lambda *_args, response=completed, **_kwargs: response)

    def test_staged_coordinator_start_snapshots_before_one_native_delivery(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); launched = []
        observation = {"window":"window-1", "tab":"tab-1", "session":"session-1", "elapsed_seconds":0.1, "result":"coordinator_delivery_confirmed"}
        self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda spec: launched.append(spec) or observation), 0)
        self.assertEqual(len(launched), 1); self.assertEqual(launched[0]["role"], "coordinator"); self.assertEqual(launched[0]["command"], ["fake-session", "coordinator"]); self.assertEqual(launched[0]["sandbox"], "workspace-write")
        self.assertFalse(any(item["role"] in ("developer", "reviewer") for item in launched))
        state, session, tabs = self.state(), json.loads((current / "supervised_session.json").read_text()), json.loads((current / "tabs.json").read_text())
        self.assertEqual(state["phase"], "coordinator_initial"); self.assertEqual(session["phase"], "coordinator_initial"); self.assertEqual(session["task_snapshot_sha256"], state["task_snapshot_sha256"]); self.assertEqual(session["tab"], {"window":"window-1", "tab":"tab-1", "session":"session-1"})
        self.assertEqual(tabs["roles"][0]["session"], "session-1"); self.assertEqual(ORCHESTRATOR.validate_snapshot(root, authority, current, config, state), "task-one\n")
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"ok","next_prompt":None,"human_reason":None,"human_category":None})
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        self.assertEqual(self.state()["phase"], "coordinator_initial"); self.assertEqual(json.loads((current / "supervised_session.json").read_text())["state"], "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING")
        for view in ("status", "preview", "resume", "cycle"):
            rendered = io.StringIO()
            with contextlib.redirect_stdout(rendered):
                if view == "cycle": result = ORCHESTRATOR.supervised_cycle(root, config, authority, current, history, state_path)
                else: result = ORCHESTRATOR.supervised_view(root, config, current, history, state_path, view)
            self.assertEqual(result, 0); response = json.loads(rendered.getvalue())
            self.assertEqual(response["state"], "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING"); self.assertEqual(response["roles_started"], ["coordinator"])
            self.assertEqual(response["next_action"], "launch developer"); self.assertNotIn("Start project", rendered.getvalue())
        saved = {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}; state_before = state_path.read_bytes()
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        self.assertEqual(saved, {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}); self.assertEqual(state_before, state_path.read_bytes()); self.assertEqual(len(launched), 1)

    def test_complete_explicit_staged_cycle_with_frozen_review_identity(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.clean_baseline = self.old_clean
        (root / ".gitignore").write_text(".runtime/\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True)
        initial = {"window":"w", "tab":"t1", "session":"s1", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        calls = []
        def deliver(spec):
            calls.append(spec)
            return {"window":"w", "tab":"t"+str(len(calls)+1), "session":"s"+str(len(calls)+1), "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: initial), 0)
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE", "summary":"go", "next_prompt":None, "human_reason":None, "human_category":None})
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        self.assertEqual(json.loads(captured.getvalue())["next_action"], "launch developer"); self.assertEqual(calls, [])
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", deliver), 0)
        self.assertEqual(calls[0]["sandbox"], "workspace-write"); self.assertEqual(calls[0]["window"], "w")
        view = io.StringIO()
        with contextlib.redirect_stdout(view): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(view.getvalue())["trigger_status"], "awaiting_trigger"); self.assertIn("trigger developer --ready", json.loads(view.getvalue())["next_action"])
        (root / "created.txt").write_text("developer result")
        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":["created.txt"], "validation":[], "self_check":["scope: pass"], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
        self.assertEqual(json.loads(captured.getvalue())["next_action"], "launch reviewer"); self.assertIn("self_check", (current / "dev_report.md").read_text()); self.assertEqual(len(calls), 1)
        view = io.StringIO()
        with contextlib.redirect_stdout(view): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(view.getvalue())["next_action"], "launch reviewer")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", deliver), 0)
        self.assertEqual(calls[1]["sandbox"], "workspace-write"); self.assertEqual(calls[1]["window"], "w")
        view = io.StringIO()
        with contextlib.redirect_stdout(view): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(view.getvalue())["trigger_status"], "awaiting_trigger"); self.assertIn("trigger reviewer --ready", json.loads(view.getvalue())["next_action"])
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":["checked"], "human_reason":None, "human_category":None})
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 0)
        self.assertEqual(json.loads(captured.getvalue())["next_action"], "coordinator: coordinate latest"); self.assertTrue((history / "001" / "review_identity.json").is_file()); self.assertTrue((history / "001" / "review_report.md").is_file())
        before = {p: p.read_bytes() for p in history.rglob("*") if p.is_file()}; status = io.StringIO()
        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(status.getvalue())["trigger_status"], "awaiting_trigger"); self.assertIn("trigger coordinator --ready", json.loads(status.getvalue())["next_action"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 2)
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", deliver), 2)
        self.assertEqual(before, {p: p.read_bytes() for p in history.rglob("*") if p.is_file()}); self.assertEqual(len(calls), 2)

    def prepare_staged_fixture(self, attempt_limit=2, cli_config=False, real_instructions=False):
        config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.clean_baseline = self.old_clean
        if cli_config: (root / ".agent" / "controller_config.json").write_bytes((root / ".runtime" / "controller.json").read_bytes())
        if real_instructions: (root / "assets" / "developer.md").write_bytes((ROOT / ".agent" / "roles" / "developer.md").read_bytes())
        (root / ".gitignore").write_text(".runtime/\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True)
        delivery = {"window":"w", "tab":"t1", "session":"s1", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery, task_limit=2, attempt_limit=attempt_limit), 0)
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE", "summary":"go", "next_prompt":None, "human_reason":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        return config, root, authority, approval, current, history, state_path

    def test_legacy_policy_edit_during_developer_refuses_before_publication(self):
        original = ORCHESTRATOR.run_role; calls = []
        def run(root, current, config, name, prompt):
            calls.append(name); result = original(root, current, config, name, prompt)
            if name == "developer": (root / ".agent" / "workflow_policy.json").write_text("changed policy")
            return result
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(ORCHESTRATOR, "run_role", side_effect=run), mock.patch.object(sys, "argv", ["orchestrate.py"]):
            self.assertEqual(ORCHESTRATOR.main(), 2)
        current = self.current()
        self.assertEqual(calls, ["coordinator", "developer"]); self.assertEqual(self.state()["phase"], "developer")
        self.assertFalse((current / "dev_report.md").exists()); self.assertFalse((current / "after_developer.json").exists()); self.assertTrue((current / ".developer.json").is_file())

    def test_policy_rejects_independent_contradictory_guidance(self):
        config, root, _ = self.locations(); policy_path = root / ".agent" / "workflow_policy.json"
        policy = json.loads(policy_path.read_text()); policy["guidance"] = {"stop":"send anyway"}; self.write_json(policy_path, policy)
        with self.assertRaisesRegex(RuntimeError, "unsupported workflow policy fields"):
            ORCHESTRATOR.effective_policy(root, config)

    def test_active_run_policy_edit_refuses_developer_acceptance(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        def launch(spec):
            return {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
        (root / "assets" / "coordinator.md").write_text("changed workflow guidance")
        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":["assets/coordinator.md"], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        before = state_path.read_bytes(), authority.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 2)
        self.assertEqual((state_path.read_bytes(), authority.read_bytes()), before)
        self.assertFalse((current / "dev_report.md").exists())

    def test_actionable_negative_review_returns_to_coordinator_without_dispatch(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        launched = []
        def launch(spec):
            launched.append(spec)
            return {"window":"w", "tab":"t" + str(len(launched) + 1), "session":"s" + str(len(launched) + 1), "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
        review = {"verdict":"CHANGES_REQUIRED", "summary":"correction needed", "findings":["correct the defect"], "evidence":["observed"], "human_reason":None, "human_category":None}
        self.write_json(current / ".reviewer.json", review); original_authority = authority.read_bytes(); out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 0)
        self.assertEqual(json.loads(out.getvalue())["phase"], "coordinator_review")
        self.assertIn("correct the defect", (history / "001" / "review_report.md").read_text())
        self.assertEqual(json.loads((history / "001" / ".reviewer.json").read_text()), review)
        self.assertEqual(authority.read_bytes(), original_authority); self.assertEqual(len(launched), 2)
        archived = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 2)
        self.assertEqual(archived, {p:p.read_bytes() for p in history.rglob("*") if p.is_file()})
        sent = []
        def send(spec):
            sent.append(spec)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, send), 0)
        self.assertEqual((sent[0]["window"], sent[0]["tab"], sent[0]["session"]), ("w", "t1", "s1"))
        self.assertTrue(sent[0]["payload"].startswith("coordinate latest "))
        self.assertEqual(json.loads(sent[0]["payload"].split(": ", 1)[1])["proposal_decision"], "correction")
        self.assertEqual(archived, {p:p.read_bytes() for p in history.rglob("*") if p.is_file()})
        # A negative review does not authorize project edits while Coordinator
        # considers a correction; the reviewed project identity stays binding.
        (root / "unexpected-untracked.txt").write_text("inter-attempt edit")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 2)
        self.assertEqual(archived, {p:p.read_bytes() for p in history.rglob("*") if p.is_file()})

    def test_coordinator_cannot_inject_human_approval_during_delivery(self):
        args, identity = self.prepare_approved_correction(approve=False)
        root, config, authority, approval, current, history, state_path = args
        names = ("coordinator_summary.md", "coordinator_proposal.md", "correction_scope.json")
        draft = {name:(current / name).read_bytes() for name in names}
        for name in names: (current / name).unlink()
        before = authority.read_bytes(); sent = []
        def sender(spec):
            for name, data in draft.items(): (current / name).write_bytes(data)
            self.write_json(current / "proposal_approval.json", ORCHESTRATOR.proposal_approval_record(identity))
            sent.append(spec)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "coordinator", True, sender), 2)
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, lambda _: self.fail("unexpected dispatch")), 2)
        self.assertEqual(len(sent), 1); self.assertEqual(authority.read_bytes(), before)

    def test_coordinator_drafts_allow_explicit_human_approval(self):
        args, _ = self.prepare_approved_correction(approve=False)
        root, config, authority, approval, current, history, state_path = args
        names = ("coordinator_summary.md", "coordinator_proposal.md", "correction_scope.json")
        draft = {name:(current / name).read_bytes() for name in names}
        for name in names: (current / name).unlink()
        def sender(spec):
            for name, data in draft.items(): (current / name).write_bytes(data)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "coordinator", True, sender), 0)
        self.assertFalse((current / "proposal_approval.json").exists())
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        shown = json.loads(out.getvalue())
        cli = ["orchestrate.py", "approve-next", "--run-id", shown["run_id"], "--iteration", str(shown["iteration"]), "--proposal-sha256", shown["proposal_sha256"], "--scope-sha256", shown["scope_sha256"], "--confirm-correction-scope"]
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", cli): self.assertEqual(ORCHESTRATOR.main(), 0)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
        self.assertEqual(ORCHESTRATOR.digest(authority.read_bytes()), shown["proposal_sha256"])

    def test_legacy_resume_cannot_consume_staged_reviewer_turn(self):
        args, _ = self.prepare_approved_correction()
        root, config, authority, approval, current, history, state_path = args
        def sender(spec): return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["developer"], {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
        before = {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()}; saved = state_path.read_bytes(), authority.read_bytes(), approval.read_bytes(); out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(sys, "argv", ["orchestrate.py", "--resume"]), mock.patch.object(ORCHESTRATOR, "run_role", side_effect=AssertionError("unexpected role")) as run:
            self.assertEqual(ORCHESTRATOR.main(), 2)
        self.assertIn("staged", json.loads(out.getvalue())["reason"].lower()); run.assert_not_called()
        self.assertEqual((state_path.read_bytes(), authority.read_bytes(), approval.read_bytes()), saved)
        self.assertEqual(before, {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()})

    def test_approved_review_with_escalation_cannot_advance(self):
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        def launch(spec): return {"window":"w", "tab":"t2" if spec["role"] == "developer" else "t3", "session":"s2" if spec["role"] == "developer" else "s3", "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
            self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"unsafe", "findings":[], "evidence":[], "human_reason":"unexpected diff", "human_category":"unsafe_or_unexpected_diff"})
        before = authority.read_bytes(); out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 2)
        self.assertEqual(json.loads(out.getvalue())["category"], "unsafe_or_unexpected_diff")
        self.assertEqual(authority.read_bytes(), before)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_next_task(root, config, authority, approval, current, history, state_path), 2)

    def test_legacy_review_escalation_stops_before_publication(self):
        self.set_mode("reviewer-escalation"); before = (self.root / "tasks" / "authority.md").read_bytes()
        self.run_controller()
        self.assert_stop("unsafe_or_unexpected_diff")
        self.assertEqual((self.root / "tasks" / "authority.md").read_bytes(), before)
        self.assertFalse((self.current() / "review_report.md").exists())
        self.assertEqual(json.loads((self.locations()[2][3] / "001" / ".reviewer.json").read_text())["human_category"], "unsafe_or_unexpected_diff")

    def test_valid_approved_review_sends_next_task_guidance(self):
        args = self.prepare_staged_fixture()
        config, root, authority, approval, current, history, state_path = args
        ordered = (root, config, authority, approval, current, history, state_path)
        def launch(spec): return {"window":"w", "tab":"t2" if spec["role"] == "developer" else "t3", "session":"s2" if spec["role"] == "developer" else "s3", "result":"role_delivery_confirmed"}
        sent = []
        def sender(spec):
            sent.append(spec)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
            self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*ordered, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
            self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":[], "human_reason":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*ordered, "reviewer"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*ordered, "coordinator", True, sender), 0)
        fields = json.loads(sent[0]["payload"].split(": ", 1)[1])
        self.assertEqual(fields["proposal_decision"], "next_task")
        self.assertIn("bounded next task", fields["policy_guidance"])

    def test_previously_archived_contradictory_review_cannot_authorize_proposal(self):
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        def launch(spec): return {"window":"w", "tab":"t2" if spec["role"] == "developer" else "t3", "session":"s2" if spec["role"] == "developer" else "s3", "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
            self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
            self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"unsafe", "findings":[], "evidence":[], "human_reason":"unexpected diff", "human_category":"unsafe_or_unexpected_diff"})
            # Simulate a completed checkpoint accepted by the older implementation.
            with mock.patch.object(ORCHESTRATOR, "review_escalation", return_value=None):
                self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 0)
        sent = []
        def sender(spec):
            sent.append(spec)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, sender), 0)
        fields = json.loads(sent[0]["payload"].split(": ", 1)[1])
        self.assertEqual(fields["proposal_decision"], "stop")
        self.assertNotIn("ask for human approval", fields["policy_guidance"])
        (current / "coordinator_summary.md").write_text("proposal\n"); (current / "coordinator_proposal.md").write_text("next task\n")
        saved = authority.read_bytes(), state_path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.pending_proposal(root, config, authority, approval, current, history, state_path), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), saved)
        self.assertFalse((current / "proposal_approval.json").exists())

    def test_review_escalation_checks_each_field_and_preserves_valid_verdicts(self):
        for verdict in ("APPROVED", "CHANGES_REQUIRED"):
            self.assertIsNone(ORCHESTRATOR.review_escalation({"verdict":verdict, "summary":"review", "human_reason":None, "human_category":None}))
            self.assertEqual(ORCHESTRATOR.review_escalation({"verdict":verdict, "summary":"review", "human_reason":None, "human_category":"unsafe_or_unexpected_diff"}), ("unsafe_or_unexpected_diff", "review"))
            self.assertEqual(ORCHESTRATOR.review_escalation({"verdict":verdict, "summary":"review", "human_reason":"needs human", "human_category":None}), ("unresolved_requirement", "needs human"))
        self.assertEqual(ORCHESTRATOR.review_escalation({"verdict":"HUMAN_REQUIRED", "summary":"review", "human_reason":None, "human_category":None}), ("unresolved_requirement", "review"))

    def check_recording_refuses_archive_change(self, command):
        args, identity = self.prepare_approved_correction(approve=False)
        root, config, authority, approval, current, history, state_path = args
        archived = history / "001" / "dev_report.md"
        before_authority, before_state = authority.read_bytes(), state_path.read_bytes()
        original_fsync = os.fsync
        def mutate_after_write(fd):
            original_fsync(fd)
            archived.write_text("tampered archived Developer report\n")
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR.os, "fsync", side_effect=mutate_after_write), mock.patch.object(ORCHESTRATOR, "deliver_iterm_trigger", side_effect=AssertionError("unexpected dispatch")):
            if command == "approve":
                result = ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"], identity["scope_sha256"], True)
            else:
                result = ORCHESTRATOR.stop_proposal(*args, identity["run_id"], identity["iteration"])
        self.assertEqual(result, 2)
        self.assertEqual(archived.read_text(), "tampered archived Developer report\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
            with self.assertRaises(RuntimeError):
                ORCHESTRATOR.verify_completion_guard(root, current, history, state_path, ORCHESTRATOR.load_supervised_session(current))
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), (before_authority, before_state))

    def test_approval_refuses_archive_change_during_recording(self):
        self.check_recording_refuses_archive_change("approve")

    def test_stop_refuses_archive_change_during_recording(self):
        self.check_recording_refuses_archive_change("stop")

    def test_human_approval_binds_pending_proposal_without_advancing(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        def launch(spec):
            role = spec["role"]
            return {"window":"w", "tab":"t2" if role == "developer" else "t3", "session":"s2" if role == "developer" else "s3", "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
            self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
            self.write_json(current / ".reviewer.json", {"verdict":"CHANGES_REQUIRED", "summary":"fix", "findings":["defect"], "evidence":[], "human_reason":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 0)
        args = (root, config, authority, approval, current, history, state_path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 2)
        (current / "coordinator_summary.md").write_text("Correction proposed\n")
        proposal = current / "coordinator_proposal.md"
        proposal.symlink_to(authority)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 2)
        proposal.unlink(); proposal_text = self.write_correction_scope(args, "Fix the defect")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        identity = json.loads(out.getvalue())
        before_state, before_authority = state_path.read_bytes(), authority.read_bytes()
        before_history = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            archived_review = history / "001" / "review_report.md"
            archived_review.write_text("changed predecessor")
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 2)
            archived_review.write_bytes(before_history[archived_review])
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], "0" * 64), 2)
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, "0" * 64, identity["iteration"], identity["proposal_sha256"]), 2)
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"] + 1, identity["proposal_sha256"]), 2)
            proposal.write_text("Changed proposal\n")
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 2)
            proposal.write_text(proposal_text)
            cli = ["orchestrate.py", "approve-next", "--run-id", identity["run_id"], "--iteration", str(identity["iteration"]), "--proposal-sha256", identity["proposal_sha256"], "--scope-sha256", identity["scope_sha256"], "--confirm-correction-scope"]
            with mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", cli), mock.patch.object(ORCHESTRATOR, "deliver_iterm_trigger", side_effect=AssertionError("approval dispatched a role")):
                self.assertEqual(ORCHESTRATOR.main(), 0)
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 2)
        record = json.loads((current / "proposal_approval.json").read_text())
        self.assertEqual(record["proposal_sha256"], identity["proposal_sha256"])
        self.assertEqual((record["run_id"], record["iteration"]), (identity["run_id"], identity["iteration"]))
        self.assertEqual(state_path.read_bytes(), before_state); self.assertEqual(authority.read_bytes(), before_authority)
        self.assertEqual(before_history, {p:p.read_bytes() for p in history.rglob("*") if p.is_file()})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, lambda _: self.fail("unexpected dispatch")), 2)
            with mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", ["orchestrate.py", "proposal"]):
                self.assertEqual(ORCHESTRATOR.main(), 0)

    def prepare_approved_correction(self, approve=True, attempt_limit=2, findings=None, cli_config=False, real_instructions=False):
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(attempt_limit=attempt_limit, cli_config=cli_config, real_instructions=real_instructions)
        def launch(spec):
            role = spec["role"]
            return {"window":"w", "tab":"t2" if role == "developer" else "t3", "session":"s2" if role == "developer" else "s3", "result":"role_delivery_confirmed"}
        args = (root, config, authority, approval, current, history, state_path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
            (root / "work.txt").write_text("first attempt\n")
            self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":["work.txt"], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
            self.write_json(current / ".reviewer.json", {"verdict":"CHANGES_REQUIRED", "summary":"fix", "findings":findings if findings is not None else ["defect"], "evidence":[], "human_reason":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "reviewer"), 0)
        (current / "coordinator_summary.md").write_text("Correction proposed\n")
        self.write_correction_scope(args, "Fix the defect")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        identity = json.loads(out.getvalue())
        if approve:
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"], identity["scope_sha256"], True), 0)
        return args, identity

    def prepare_approved_next_task(self, cli_config=False):
        args, _ = self.prepare_approved_correction(cli_config=cli_config)
        root, config, authority, approval, current, history, state_path = args
        def sender(spec): return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["developer"], {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "reviewer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["reviewer"], {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":[], "human_reason":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "reviewer"), 0)
        (current / "coordinator_summary.md").write_text("Next task\n"); (current / "coordinator_proposal.md").write_text("Next task instructions\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        identity = json.loads(output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 0)
        return args, identity

    def test_correction_without_finding_mapping_cannot_be_approved(self):
        args, identity = self.prepare_approved_correction(approve=False, findings=["first defect", "second defect"])
        (args[4] / "correction_scope.json").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 2)
        self.assertFalse((args[4] / "proposal_approval.json").exists())

    def test_human_can_stop_at_summary_without_proposal(self):
        args, identity = self.prepare_approved_correction(approve=False)
        root, config, authority, approval, current, history, state_path = args
        (current / "coordinator_proposal.md").unlink()
        (current / "correction_scope.json").unlink()
        before = authority.read_bytes(), state_path.read_bytes(), {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        status = io.StringIO()
        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertIn(identity["run_id"], json.loads(status.getvalue())["stop_command"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.stop_proposal(*args, "0" * 64, identity["iteration"]), 2)
            self.assertEqual(ORCHESTRATOR.stop_proposal(*args, identity["run_id"], identity["iteration"] + 1), 2)
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", ["orchestrate.py", "stop-proposal", "--iteration", str(identity["iteration"]), "--run-id", identity["run_id"]]):
            self.assertEqual(ORCHESTRATOR.main(), 0)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes(), {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}), before)
        status = io.StringIO()
        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(status.getvalue())["state"], "HUMAN_STOPPED")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.stop_proposal(*args, identity["run_id"], identity["iteration"]), 2)
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 2)
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "coordinator", True, lambda _: self.fail("stop dispatched")), 2)
        (current / "coordinator_summary.md").write_text("late edit")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 2)

    def test_correction_cli_requires_exact_coverage_and_scope_confirmation(self):
        args, identity = self.prepare_approved_correction(approve=False, findings=["first defect", "second defect"])
        root, config, authority, approval, current, history, state_path = args
        scope_path = current / "correction_scope.json"; original = json.loads(scope_path.read_text())
        for change in ("missing", "partial", "unrelated", "absent", "criteria"):
            scope = json.loads(json.dumps(original))
            if change == "missing": scope["findings"] = []
            if change == "partial": scope["findings"] = scope["findings"][:1]
            if change == "unrelated": scope["findings"][0]["finding_sha256"] = "0" * 64
            if change == "absent": scope["findings"][0]["change"] = "not in approved instructions"
            if change == "criteria": scope["criteria_changes"] = ["remove criterion"]
            self.write_json(scope_path, scope); out = io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
            shown = json.loads(out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "deliver_iterm_trigger", side_effect=AssertionError("unexpected dispatch")):
                self.assertEqual(ORCHESTRATOR.approve_proposal(*args, shown["run_id"], shown["iteration"], shown["proposal_sha256"], shown["scope_sha256"], True), 2)
            self.assertFalse((current / "proposal_approval.json").exists())
        self.write_json(scope_path, original); out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        shown = json.loads(out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.approve_proposal(*args, shown["run_id"], shown["iteration"], shown["proposal_sha256"], shown["scope_sha256"], False), 2)
        cli = ["orchestrate.py", "approve-next", "--run-id", shown["run_id"], "--iteration", str(shown["iteration"]), "--proposal-sha256", shown["proposal_sha256"], "--scope-sha256", shown["scope_sha256"], "--confirm-correction-scope"]
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", cli): self.assertEqual(ORCHESTRATOR.main(), 0)
        self.assertTrue(json.loads((current / "proposal_approval.json").read_text())["correction_scope_confirmed"])
        before = authority.read_bytes(), state_path.read_bytes(); self.write_json(scope_path, {**original, "criteria_changes":["changed after approval"]})
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), before)

    def test_approved_correction_rolls_over_without_dispatch(self):
        args, identity = self.prepare_approved_correction()
        root, config, authority, approval, current, history, state_path = args
        old = {p:p.read_bytes() for p in (history / "001").rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "deliver_iterm_trigger", side_effect=AssertionError("rollover dispatched")):
            with mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", ["orchestrate.py", "rollover-correction"]): self.assertEqual(ORCHESTRATOR.main(), 0)
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        self.assertEqual(authority.read_text(), "task-one\n\nFix the defect\n")
        self.assertEqual((current / "authoritative_task.md").read_bytes(), authority.read_bytes())
        self.assertEqual(old, {p:p.read_bytes() for p in (history / "001").rglob("*") if p.is_file()})
        self.assertEqual((root / "work.txt").read_text(), "first attempt\n")
        state = json.loads(state_path.read_text()); self.assertEqual(state["task_id"], json.loads((history / "001" / "state.json").read_text())["task_id"]); self.assertEqual(state["attempt"], 2)
        self.assertFalse((current / ".developer.json").exists())
        sent = []
        def send(spec):
            sent.append(spec); return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, send), 0)
        self.assertEqual((sent[0]["window"], sent[0]["tab"], sent[0]["session"]), ("w", "t2", "s2"))
        context = json.loads(sent[0]["payload"].split(": ", 1)[1]); self.assertNotEqual(context["report"], str(current / ".developer.json"))
        self.write_json(Path(context["report"]), {"status":"DONE", "summary":"fixed", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "reviewer", True, send), 0)
        self.assertEqual(sent[-1]["session"], "s3")
        reviewer_context = json.loads(sent[-1]["payload"].split(": ", 1)[1])
        self.write_json(Path(reviewer_context["report"]), {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":[], "human_reason":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "reviewer"), 0)
        self.assertTrue((history / "002" / Path(context["report"]).name).is_file())
        self.assertTrue((history / "002" / Path(reviewer_context["report"]).name).is_file())

    def test_rollover_publishes_only_the_bytes_validated_for_approval(self):
        args, identity = self.prepare_approved_correction()
        root, config, authority, approval, current, history, state_path = args
        approved = (current / "coordinator_proposal.md").read_bytes()
        original = ORCHESTRATOR.verify_correction_scope
        def replace_after_validation(*params):
            original(*params)
            (current / "coordinator_proposal.md").write_bytes(b"unapproved replacement\n")
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "verify_correction_scope", side_effect=replace_after_validation):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
        self.assertEqual(authority.read_bytes(), approved)
        self.assertEqual((current / "authoritative_task.md").read_bytes(), approved)
        self.assertEqual(json.loads((current / "task_snapshot.json").read_text())["sha256"], identity["proposal_sha256"])
        self.assertEqual(json.loads(state_path.read_text())["task_snapshot_sha256"], identity["proposal_sha256"])
        self.assertEqual(json.loads((current / "approval_evidence.json").read_text())["proposal_sha256"], identity["proposal_sha256"])

    def test_both_rollovers_run_through_cli_without_delivery(self):
        first = True
        for kind in ("correction", "next-task"):
            if not first: self.tearDown(); self.setUp()
            first = False
            with self.subTest(kind=kind):
                args, identity = self.prepare_approved_correction(cli_config=True) if kind == "correction" else self.prepare_approved_next_task(cli_config=True)
                root, config, authority, approval, current, history, state_path = args
                before = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
                cmd = [sys.executable, "-B", str(ROOT / ".agent" / "orchestrate.py"), "rollover-" + kind]
                result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["dispatch"], "not attempted")
                self.assertEqual(authority.read_bytes(), (current / "authoritative_task.md").read_bytes())
                self.assertEqual(ORCHESTRATOR.digest(authority.read_bytes()), identity["proposal_sha256"])
                self.assertEqual(before, {p:p.read_bytes() for p in before})
                session = json.loads((current / "supervised_session.json").read_text()); self.assertNotIn("developer", session.get("trigger_attempts", {}))
                duplicate = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
                self.assertEqual(duplicate.returncode, 2, duplicate.stdout + duplicate.stderr)

    def test_both_rollovers_refuse_evidence_collisions_without_mutation(self):
        first = True
        for kind in ("correction", "next_task"):
            for collision in ("coordination", "marker_symlink", "next_archive", "summary_symlink", "approval_symlink"):
                if not first: self.tearDown(); self.setUp()
                first = False
                with self.subTest(kind=kind, collision=collision):
                    args, identity = self.prepare_approved_correction() if kind == "correction" else self.prepare_approved_next_task()
                    root, config, authority, approval, current, history, state_path = args; n = identity["iteration"]
                    if collision == "coordination":
                        target = history / f"{n:03d}-coordination"; target.mkdir(); (target / "keep").write_text("keep")
                    elif collision == "marker_symlink": (history / f"{n:03d}-rollover.json").symlink_to(authority)
                    elif collision == "next_archive":
                        target = history / f"{n + 1:03d}"; target.mkdir(); (target / "keep").write_text("keep")
                    else:
                        target = current / ("coordinator_summary.md" if collision == "summary_symlink" else "proposal_approval.json")
                        target.unlink(); target.symlink_to(authority)
                    session = ORCHESTRATOR.load_supervised_session(current); guard = session["completion_guard"]
                    ORCHESTRATOR.record_completion_guard(root, current, history, state_path, session, guard["project"], guard["excluded_sha256"])
                    before = ORCHESTRATOR.runtime_evidence(root, current, history, state_path, None); state_before = state_path.read_bytes(); authority_before = authority.read_bytes()
                    with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "deliver_iterm_trigger", side_effect=AssertionError("unexpected delivery")):
                        cli = ["orchestrate.py", "rollover-" + kind.replace("_", "-")]
                        with mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", cli): self.assertEqual(ORCHESTRATOR.main(), 2)
                        self.assertEqual(ORCHESTRATOR.rollover_approved(*args, kind), 2)
                    self.assertEqual(ORCHESTRATOR.runtime_evidence(root, current, history, state_path, None), before)
                    self.assertEqual((state_path.read_bytes(), authority.read_bytes()), (state_before, authority_before))

    def test_manual_rollover_readiness_refuses_failed_and_accepts_healthy_turn(self):
        for failed in (True, False):
            if not failed: self.tearDown(); self.setUp()
            with self.subTest(failed=failed):
                args, _ = self.prepare_approved_correction(cli_config=True, real_instructions=True)
                root, config, authority, approval, current, history, state_path = args
                original = ORCHESTRATOR.write_json
                def fail_after_state(path, data):
                    if path == state_path and data.get("status") == "RUNNING":
                        original(path, data); raise OSError("injected post-write failure")
                    return original(path, data)
                patcher = mock.patch.object(ORCHESTRATOR, "write_json", side_effect=fail_after_state) if failed else contextlib.nullcontext()
                with patcher, contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2 if failed else 0)
                session = json.loads((current / "supervised_session.json").read_text()); attempt = session["attempt_id"]
                instructions = (root / "assets" / "developer.md").read_text()
                self.assertIn("ready-developer --attempt-id", instructions); self.assertIn("do no work and write no report", instructions)
                before = {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()}; state_before = state_path.read_bytes()
                cli = [sys.executable, "-B", str(ROOT / ".agent" / "orchestrate.py"), "ready-developer", "--attempt-id", attempt]
                process = subprocess.run(cli, cwd=root, capture_output=True, text=True); result = process.returncode
                work = []
                if result == 0:
                    decision = json.loads(process.stdout); self.assertTrue(decision["ready"])
                    self.assertEqual(decision["report"], str(current / session["report_slots"]["developer"]))
                    self.assertEqual(state_path.read_bytes(), state_before)
                    self.assertEqual(before, {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()})
                    for name in ("approval_evidence.json", "authoritative_task.md"):
                        path = current / name; original_bytes = path.read_bytes(); path.write_bytes(b"inconsistent")
                        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.ready_developer(*args, attempt), 2)
                        self.assertFalse((current / session["report_slots"]["developer"]).exists()); path.write_bytes(original_bytes)
                    (root / "manual-result.txt").write_text("work")
                    self.write_json(Path(decision["report"]), {"status":"DONE", "summary":"manual", "files_changed":["manual-result.txt"], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
                    work.append("work")
                self.assertEqual(work, [] if failed else ["work"])
                if failed:
                    self.assertFalse((current / session["report_slots"]["developer"]).exists()); self.assertFalse((root / "manual-result.txt").exists())
                    self.assertEqual(state_path.read_bytes(), state_before); self.assertEqual(before, {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()})
                else:
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)

    def test_status_reports_retained_lock_when_state_write_is_torn(self):
        args, _ = self.prepare_approved_correction(cli_config=True); root, config, authority, approval, current, history, state_path = args
        original = ORCHESTRATOR.write_json
        def tear(path, data):
            if path == state_path and data.get("status") == "RUNNING":
                path.write_bytes(b"{torn"); raise OSError("injected torn state")
            return original(path, data)
        with mock.patch.object(ORCHESTRATOR, "write_json", side_effect=tear), contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        lock = state_path.parent / "orchestrate.lock"; self.assertTrue(lock.is_file())
        before = {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()}; state_bytes = state_path.read_bytes(); lock_bytes = lock.read_bytes(); authority_bytes = authority.read_bytes()
        result = subprocess.run([sys.executable, "-B", str(ROOT / ".agent" / "orchestrate.py"), "status"], cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        response = json.loads(result.stdout); self.assertIn("lock", response["reason"].lower()); self.assertIn("lock", response["recovery"].lower()); self.assertIn("malformed", response["reason"].lower())
        self.assertEqual((state_path.read_bytes(), lock.read_bytes(), authority.read_bytes()), (state_bytes, lock_bytes, authority_bytes))
        self.assertEqual(before, {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()})

    def test_controller_sent_rollover_waits_for_unlock_and_confirms_delivery_identity(self):
        args, _ = self.prepare_approved_correction(real_instructions=True)
        root, config, authority, approval, current, history, state_path = args
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
        session = json.loads((current / "supervised_session.json").read_text()); attempt_id = session["attempt_id"]; captured = []
        def sender(spec):
            fields = json.loads(spec["payload"].split(": ", 1)[1]); captured.append(fields)
            self.assertEqual(fields["rollover_attempt_id"], attempt_id)
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.ready_developer(*args, attempt_id, fields["delivery_id"]), 2)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{key:spec[key] for key in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 0)
        out = io.StringIO(); delivery_id = captured[0]["delivery_id"]
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.ready_developer(*args, attempt_id, delivery_id), 0)
        self.assertTrue(json.loads(out.getvalue())["ready"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.ready_developer(*args, attempt_id), 2)
            self.assertEqual(ORCHESTRATOR.ready_developer(*args, attempt_id, "wrong"), 2)
            self.assertEqual(ORCHESTRATOR.ready_developer(*args, "0" * 32, delivery_id), 2)

    def test_uncertain_rollover_delivery_cannot_authorize_work(self):
        args, _ = self.prepare_approved_correction(real_instructions=True)
        root, config, authority, approval, current, history, state_path = args
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
        attempt_id = json.loads((current / "supervised_session.json").read_text())["attempt_id"]; captured = []
        def sender(spec):
            captured.append(json.loads(spec["payload"].split(": ", 1)[1])); raise RuntimeError("uncertain fake delivery")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 2)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.ready_developer(*args, attempt_id, captured[0]["delivery_id"]), 2)
        session = json.loads((current / "supervised_session.json").read_text())
        self.assertFalse((current / session["report_slots"]["developer"]).exists())

    def test_unlocked_torn_state_retains_malformed_diagnostic(self):
        config, root, (authority, approval, current, history, state_path) = self.locations(); state_path.write_bytes(b"{torn")
        (root / ".agent" / "controller_config.json").write_bytes((root / ".runtime" / "controller.json").read_bytes())
        result = subprocess.run([sys.executable, "-B", str(ROOT / ".agent" / "orchestrate.py"), "status"], cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("malformed", json.loads(result.stdout)["reason"].lower()); self.assertFalse((state_path.parent / "orchestrate.lock").exists())

    def test_interrupted_rollovers_preserve_evidence_and_block_delivery(self):
        first = True
        for kind in ("correction", "next_task"):
            for point in ("marker_fsync", "rename", "publish", "snapshot", "baseline", "state_before_write", "state_after_write", "crash_after_write"):
                if not first: self.tearDown(); self.setUp()
                first = False
                with self.subTest(kind=kind, point=point):
                    args, identity = self.prepare_approved_correction() if kind == "correction" else self.prepare_approved_next_task()
                    root, config, authority, approval, current, history, state_path = args
                    original_history = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
                    original_current = {p.relative_to(current):p.read_bytes() for p in current.rglob("*") if p.is_file()}
                    old_authority = authority.read_bytes(); approved = (current / "coordinator_proposal.md").read_bytes()
                    original_write = ORCHESTRATOR.write_json
                    def fail_write(path, data):
                        if point == "snapshot" and path == current / "task_snapshot.json": raise OSError("injected snapshot failure")
                        if point == "baseline" and path == current / "baseline.json": raise OSError("injected baseline failure")
                        if point == "state_before_write" and path == state_path and data.get("status") == "RUNNING": raise OSError("injected state failure")
                        if point in ("state_after_write", "crash_after_write") and path == state_path and data.get("status") == "RUNNING":
                            original_write(path, data)
                            if point == "crash_after_write": raise KeyboardInterrupt()
                            raise OSError("injected post-write failure")
                        return original_write(path, data)
                    target = "fsync" if point == "marker_fsync" else "rename" if point == "rename" else "replace" if point == "publish" else None
                    patcher = mock.patch.object(ORCHESTRATOR.os, target, side_effect=OSError("injected " + point)) if target else contextlib.nullcontext()
                    with patcher, mock.patch.object(ORCHESTRATOR, "write_json", side_effect=fail_write), contextlib.redirect_stdout(io.StringIO()):
                        if point == "crash_after_write":
                            with self.assertRaises(KeyboardInterrupt): ORCHESTRATOR.rollover_approved(*args, kind)
                        else: self.assertEqual(ORCHESTRATOR.rollover_approved(*args, kind), 2)
                    self.assertTrue((state_path.parent / "orchestrate.lock").is_file())
                    self.assertEqual(original_history, {p:p.read_bytes() for p in original_history})
                    moved = history / f"{identity['iteration']:03d}-coordination"
                    preserved = moved if moved.is_dir() else current
                    self.assertEqual(original_current, {name:(preserved / name).read_bytes() for name in original_current})
                    self.assertIn(authority.read_bytes(), (old_authority, approved))
                    evidence = ORCHESTRATOR.runtime_evidence(root, current, history, state_path, None); saved_state = state_path.read_bytes(); sent = []
                    def sender(spec):
                        sent.append(spec); return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(ORCHESTRATOR.rollover_approved(*args, kind), 2)
                        self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 2)
                        with mock.patch.object(sys, "argv", ["orchestrate.py", "--resume"]), mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(ORCHESTRATOR, "run_role", side_effect=AssertionError("unexpected role")) as role_run:
                            with self.assertRaisesRegex(RuntimeError, "lock exists"): ORCHESTRATOR.main()
                            role_run.assert_not_called()
                    self.assertEqual(sent, [])
                    if point in ("state_after_write", "crash_after_write"):
                        status = io.StringIO()
                        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 2)
                        self.assertIn("lock", json.loads(status.getvalue())["reason"].lower())
                    self.assertEqual(ORCHESTRATOR.runtime_evidence(root, current, history, state_path, None), evidence)
                    self.assertEqual(state_path.read_bytes(), saved_state)

    def test_legacy_resume_refuses_recorded_proposal_stop_without_mutation(self):
        args, identity = self.prepare_approved_correction(approve=False)
        root, config, authority, approval, current, history, state_path = args
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.stop_proposal(*args, identity["run_id"], identity["iteration"]), 0)
        before = {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()}
        state_before, authority_before = state_path.read_bytes(), authority.read_bytes(); output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch.object(sys, "argv", ["orchestrate.py", "--resume"]), mock.patch.object(ORCHESTRATOR, "clean_baseline", return_value=("fake-head", {})), mock.patch.object(ORCHESTRATOR, "run_role", side_effect=ORCHESTRATOR.RoleFailure("fake role was invoked")) as run:
            self.assertEqual(ORCHESTRATOR.main(), 2)
        self.assertIn("stop", json.loads(output.getvalue())["reason"].lower()); run.assert_not_called()
        self.assertEqual((state_path.read_bytes(), authority.read_bytes()), (state_before, authority_before))
        self.assertEqual(before, {p:p.read_bytes() for base in (current, history) for p in base.rglob("*") if p.is_file()})

    def test_successive_corrections_keep_original_task_and_each_review(self):
        args, _ = self.prepare_approved_correction(attempt_limit=3)
        root, config, authority, approval, current, history, state_path = args
        def sender(spec): return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["developer"], {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "reviewer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["reviewer"], {"verdict":"CHANGES_REQUIRED", "summary":"another fix", "findings":["second defect"], "evidence":[], "human_reason":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "reviewer"), 0)
        evidence = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        (current / "coordinator_summary.md").write_text("Second correction\n"); self.write_correction_scope(args, "Fix second defect")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        identity = json.loads(out.getvalue()); scope = identity["correction_scope"]
        self.assertEqual((scope["original_iteration"], scope["predecessor_iteration"]), (1, 2))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"], identity["scope_sha256"], True), 0)
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
        self.assertIn("task-one\n", authority.read_text()); self.assertEqual(json.loads(state_path.read_text())["attempt"], 3)
        self.assertEqual(evidence, {p:p.read_bytes() for p in evidence})

    def test_correction_rollover_rejects_stale_approval_and_project_drift(self):
        args, _ = self.prepare_approved_correction(); root, _, authority, _, current, _, state_path = args
        before = authority.read_bytes(), state_path.read_bytes()
        (current / "coordinator_proposal.md").write_text("stale\n")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        (current / "coordinator_proposal.md").write_text("task-one\n\nFix the defect\n")
        (root / "unexpected").write_text("edit")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), before)

    def test_correction_rollover_partial_persistence_blocks_retry_and_dispatch(self):
        args, _ = self.prepare_approved_correction(); root, _, authority, _, current, _, state_path = args
        original = ORCHESTRATOR.write_json
        def fail(path, data):
            if path == current / "baseline.json": raise OSError("injected failure")
            return original(path, data)
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "write_json", side_effect=fail):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, lambda _: self.fail("unexpected dispatch")), 2)

    def test_two_task_budget_with_correction_and_immutable_attempts(self):
        args, identity = self.prepare_approved_correction()
        root, config, authority, approval, current, history, state_path = args
        policy = json.loads(state_path.read_text())["effective_policy"]; frozen = (current / "workflow_policy.json").read_bytes()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
        self.assertEqual(json.loads(state_path.read_text())["effective_policy"], policy); self.assertEqual((current / "workflow_policy.json").read_bytes(), frozen)
        task_one = json.loads(state_path.read_text())["task_id"]
        def sender(spec):
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        def complete_attempt(filename, content):
            out = io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 0)
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, lambda _: self.fail("duplicate dispatch")), 2)
            session = json.loads((current / "supervised_session.json").read_text()); slot = current / session["report_slots"]["developer"]
            (root / filename).write_text(content)
            self.write_json(slot, {"status":"DONE", "summary":"done", "files_changed":[filename], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
                self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "reviewer", True, sender), 0)
                session = json.loads((current / "supervised_session.json").read_text())
                self.write_json(current / session["report_slots"]["reviewer"], {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":[], "human_reason":None, "human_category":None})
                self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "reviewer"), 0)
            return slot.name
        previous_slot = complete_attempt("correction.txt", "corrected")
        preserved = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        (current / "coordinator_summary.md").write_text("Next task proposed\n")
        (current / "coordinator_proposal.md").write_text("Task two\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        proposed = json.loads(out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, proposed["run_id"], proposed["iteration"], proposed["proposal_sha256"]), 0)
        status = io.StringIO(); before_status = state_path.read_bytes()
        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        view = json.loads(status.getvalue()); self.assertEqual((view["task_number"], view["attempt"], view["task_limit"], view["attempt_limit"]), (1, 2, 2, 2)); self.assertEqual(view["review_verdict"], "APPROVED"); self.assertEqual(view["next_action"], "rollover-next-task"); self.assertEqual(state_path.read_bytes(), before_status)
        policy_path = current / "workflow_policy.json"; original_policy = policy_path.read_bytes(); policy_path.write_bytes(original_policy + b"\n")
        before_refusal = authority.read_bytes(), state_path.read_bytes(), {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_next_task(*args), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes(), {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}), before_refusal)
        policy_path.write_bytes(original_policy)
        rollover_out = io.StringIO()
        with contextlib.redirect_stdout(rollover_out):
            result = ORCHESTRATOR.rollover_next_task(*args)
            self.assertEqual(result, 0, rollover_out.getvalue())
            self.assertEqual(ORCHESTRATOR.rollover_next_task(*args), 2)
        state = json.loads(state_path.read_text()); self.assertNotEqual(state["task_id"], task_one); self.assertEqual((state["task_number"], state["attempt"]), (2, 1))
        self.assertEqual(state["effective_policy"], policy); self.assertEqual((current / "workflow_policy.json").read_bytes(), frozen)
        self.assertEqual(preserved, {p:p.read_bytes() for p in preserved})
        self.assertNotEqual(json.loads((current / "supervised_session.json").read_text())["report_slots"]["developer"], previous_slot)
        stale = current / previous_slot; stale.write_text("late report")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, lambda _: self.fail("stale report dispatched")), 2)
        stale.unlink()
        baseline = json.loads((current / "baseline.json").read_text()); self.assertIn("work.txt", baseline["manifest"]); self.assertIn("correction.txt", baseline["manifest"])
        complete_attempt("task2.txt", "second task")
        after = json.loads((history / "003" / "after_developer.json").read_text())
        self.assertEqual({key for key in after if after.get(key) != baseline["manifest"].get(key)}, {"task2.txt"})
        (current / "coordinator_summary.md").write_text("Third task proposed\n"); (current / "coordinator_proposal.md").write_text("Task three\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        third = json.loads(out.getvalue()); before = authority.read_bytes(), state_path.read_bytes()
        status = io.StringIO()
        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertNotIn("approve-next", json.loads(status.getvalue())["next_action"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.approve_proposal(*args, third["run_id"], third["iteration"], third["proposal_sha256"]), 2)
            self.assertEqual(ORCHESTRATOR.rollover_next_task(*args), 2)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, lambda _: self.fail("unexpected dispatch")), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), before)
        self.assertFalse((current / "proposal_approval.json").exists())

    def test_policy_edit_blocks_rollover_cli_without_side_effects(self):
        args, _ = self.prepare_approved_correction(); root, config, authority, approval, current, history, state_path = args
        policy_path = root / ".agent" / "workflow_policy.json"; policy_path.write_bytes(policy_path.read_bytes() + b"\n")
        before = authority.read_bytes(), state_path.read_bytes(), {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(ORCHESTRATOR, "load_config", return_value=(config, root)), mock.patch.object(sys, "argv", ["orchestrate.py", "rollover-correction"]), mock.patch.object(ORCHESTRATOR, "deliver_iterm_trigger", side_effect=AssertionError("unexpected dispatch")):
            self.assertEqual(ORCHESTRATOR.main(), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes(), {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}), before)

    def test_missing_active_policy_identity_never_rebinds(self):
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        state = json.loads(state_path.read_text()); state.pop("effective_policy"); self.write_json(state_path, state)
        before = state_path.read_bytes(), authority.read_bytes(); sent = []
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", sent.append), 2)
        self.assertEqual(sent, []); self.assertEqual((state_path.read_bytes(), authority.read_bytes()), before)
        state["effective_policy"] = {"version":2}; self.write_json(state_path, state); before = state_path.read_bytes()
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", sent.append), 2)
        self.assertIn("unsupported effective policy identity", json.loads(out.getvalue())["reason"])
        self.assertEqual(sent, []); self.assertEqual(state_path.read_bytes(), before)

    def test_legacy_resume_without_policy_identity_is_refused(self):
        config, root, (authority, approval, current, history, state_path) = self.locations()
        current.mkdir(parents=True, exist_ok=True)
        self.write_json(state_path, {"iteration":0, "active_iteration":1, "phase":"coordinator", "config_sha256":config["_sha256"]})
        before = state_path.read_bytes(), authority.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(sys, "argv", ["orchestrate.py", "--resume"]):
            self.assertEqual(ORCHESTRATOR.main(), 2)
        self.assertEqual((state_path.read_bytes(), authority.read_bytes()), before); self.assertFalse((current / "calls").exists())

    def test_fresh_project_inherits_and_binds_shared_policy(self):
        target = self.root / "fresh-project"
        init = subprocess.run([sys.executable, str(ROOT / ".agent" / "orchestrate.py"), "init", "--project-root", str(target), "--init-git"], capture_output=True, text=True)
        self.assertEqual(init.returncode, 0, init.stderr)
        policy = target / ".agent" / "workflow_policy.json"
        self.assertEqual(policy.read_bytes(), (ROOT / ".agent" / "workflow_policy.json").read_bytes())
        for name in ("coordinator", "developer", "reviewer"):
            self.assertIn("workflow_policy.json", (target / ".agent" / "roles" / (name + ".md")).read_text())
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "fixture"], cwd=target, check=True)
        script = """import importlib.util,json,pathlib
p=pathlib.Path.cwd(); s=importlib.util.spec_from_file_location('installed',p/'.agent/orchestrate.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
m.update_role_label=lambda *a, **k: {'status':'fake'}
c,r=m.load_config(p/'.agent/controller_config.json'); a,b,cur,h,st=m.locations(r,c)
specs=[]
result=m.start_supervised(r,c,a,b,cur,h,st,lambda spec: specs.append(spec) or {'window':'w','tab':'t','session':'s','elapsed_seconds':0,'result':'coordinator_delivery_confirmed'})
assert result==0
state=json.loads(st.read_text()); assert state['effective_policy']['policy_sha256']==m.digest((cur/'workflow_policy.json').read_bytes())
assert m.verify_active_policy(r,c,cur,state)['version']==1
policy=json.loads((cur/'workflow_policy.json').read_text()); assert policy['decisions']=={'CHANGES_REQUIRED':'correction','APPROVED':'next_task','completion_or_exhausted_budget':'stop','unsafe_or_ambiguous_evidence':'stop'}
guidance=m.decision_guidance(policy)
assert 'correction to the same task' in guidance and 'bounded next task' in guidance and 'Stop and send nothing' in guidance
assert 'workflow_policy.json' in pathlib.Path(specs[0]['instruction']).read_text()
assert specs[0]['policy_guidance']==guidance
m.write_json(cur/'.coordinator.json', {'status':'CONTINUE','summary':'go','next_prompt':None,'human_reason':None,'human_category':None})
assert m.supervised_accept(r,c,a,b,cur,h,st,'coordinator')==0
def launch(spec):
 specs.append(spec); return {'window':'w','tab':'t2' if spec['role']=='developer' else 't3','session':'s2' if spec['role']=='developer' else 's3','result':'role_delivery_confirmed'}
assert m.launch_staged_role(r,c,a,cur,h,st,'developer',launch)==0
m.write_json(cur/'.developer.json', {'status':'DONE','summary':'done','files_changed':[],'validation':[],'self_check':[],'known_issues':[],'commit_or_diff_reference':None,'human_category':None})
assert m.supervised_accept(r,c,a,b,cur,h,st,'developer')==0
assert m.launch_staged_role(r,c,a,cur,h,st,'reviewer',launch)==0
assert all(str(cur/'workflow_policy.json') in spec['handoff'] for spec in specs[1:])
assert all(guidance in spec['handoff'] for spec in specs[1:])
assert all('workflow_policy.json' in pathlib.Path(spec['instruction']).read_text() for spec in specs[1:])
assert 'ready-developer --attempt-id' in pathlib.Path(specs[1]['instruction']).read_text()
assert str(pathlib.Path(specs[1]['instruction'])) in m.interactive_session_command(specs[1])
"""
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=target, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_attempt_budget_blocks_additional_correction(self):
        args, _ = self.prepare_approved_correction(); _, _, authority, _, current, _, state_path = args
        deliveries = []
        def sender(spec):
            deliveries.append(spec)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "developer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["developer"], {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "reviewer", True, sender), 0)
            session = json.loads((current / "supervised_session.json").read_text())
            self.write_json(current / session["report_slots"]["reviewer"], {"verdict":"CHANGES_REQUIRED", "summary":"fix again", "findings":["defect remains"], "evidence":[], "human_reason":None, "human_category":None})
            self.assertEqual(ORCHESTRATOR.supervised_accept(*args, "reviewer"), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(*args, "coordinator", True, sender), 0)
        context = json.loads(deliveries[-1]["payload"].split(": ", 1)[1]); self.assertEqual(context["proposal_decision"], "stop"); self.assertIn("Stop and send nothing", context["policy_guidance"])
        (current / "coordinator_summary.md").write_text("More correction\n"); (current / "coordinator_proposal.md").write_text("Fix again\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.pending_proposal(*args), 0)
        identity = json.loads(out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.approve_proposal(*args, identity["run_id"], identity["iteration"], identity["proposal_sha256"]), 2)
        before = authority.read_bytes(), state_path.read_bytes(); status = io.StringIO()
        with contextlib.redirect_stdout(status):
            self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
            self.assertEqual(ORCHESTRATOR.supervised_view(*args[:2], current, args[5], state_path, "status"), 0)
        self.assertIn("limit exhausted", json.loads(status.getvalue().splitlines()[-1])["next_action"])
        self.assertNotIn("approve-next", json.loads(status.getvalue().splitlines()[-1])["next_action"]); self.assertFalse((current / "proposal_approval.json").exists())
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), before)

    def test_invalid_run_budgets_refuse_before_launch(self):
        config, root, args = self.locations(); authority, approval, current, history, state_path = args
        before = state_path.read_bytes(); launches = []
        for task_limit, attempt_limit in ((0, 1), (3, 1), (1, 0), (1, 101)):
            with self.subTest(task_limit=task_limit, attempt_limit=attempt_limit), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, launches.append, task_limit, attempt_limit), 2)
        self.assertEqual(launches, []); self.assertEqual(state_path.read_bytes(), before); self.assertFalse(current.exists())

    def test_uncertain_coordinator_delivery_blocks_rollover(self):
        args, _ = self.prepare_approved_correction(); root, _, authority, _, current, history, state_path = args
        session = json.loads((current / "supervised_session.json").read_text()); guard = session["completion_guard"]
        session.setdefault("trigger_attempts", {})["coordinator"] = {"status":"uncertain"}
        ORCHESTRATOR.record_completion_guard(root, current, history, state_path, session, guard["project"], guard["excluded_sha256"])
        before = authority.read_bytes(), state_path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.rollover_correction(*args), 2)
        self.assertEqual((authority.read_bytes(), state_path.read_bytes()), before)

    def test_developer_launch_refuses_drift_stale_and_wrong_order(self) -> None:
        for mode in ("dirty", "head", "snapshot", "stale", "protected", "wrong_role", "lock"):
            with self.subTest(mode=mode):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); launched = []
                lock = None
                if mode == "dirty": (root / "dirty").write_text("x")
                if mode == "head": subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "--allow-empty", "-qm", "other"], cwd=root, check=True)
                if mode == "snapshot": (current / "authoritative_task.md").write_text("changed")
                if mode == "stale": (current / ".developer.json").write_text("{}")
                if mode == "protected": (current / ".coordinator.json").write_text("changed")
                if mode == "lock": lock = ORCHESTRATOR.acquire_lock(state_path.parent)
                before = {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}; state_before = state_path.read_bytes(); out = io.StringIO()
                with contextlib.redirect_stdout(out): result = ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer" if mode == "wrong_role" else "developer", launched.append)
                self.assertEqual(result, 2); self.assertEqual(json.loads(out.getvalue())["outcome"], "refusal"); self.assertEqual(before, {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}); self.assertEqual(state_before, state_path.read_bytes()); self.assertEqual(launched, []); self.assertFalse(history.exists())
                if lock is not None: self.assertTrue(lock.exists()); ORCHESTRATOR.release_lock(lock)
                self.tearDown(); self.setUp()

    def test_staged_delivery_failure_never_relaunches(self) -> None:
        for mode in ("delivery", "persistence"):
            with self.subTest(mode=mode):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); calls = []; original = ORCHESTRATOR.write_json
                def launcher(spec):
                    calls.append(spec)
                    if mode == "delivery": raise RuntimeError("injected delivery failure")
                    return {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}
                def write(path, data):
                    if mode == "persistence" and path == state_path and data.get("phase") == "developer": raise OSError("injected persistence failure")
                    return original(path, data)
                output = io.StringIO()
                with mock.patch.object(ORCHESTRATOR, "write_json", side_effect=write), contextlib.redirect_stdout(output): result = ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher)
                self.assertEqual(result, 2); self.assertEqual(json.loads(output.getvalue())["delivery"], "uncertain"); self.assertEqual(len(calls), 1)
                self.assertEqual(json.loads((current / "supervised_session.json").read_text())["state"], "PREPARING_DEVELOPER_DELIVERY")
                before = (current / "supervised_session.json").read_bytes()
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 2)
                    self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
                triggers = []
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, triggers.append), 2)
                self.assertEqual(triggers, []); self.assertEqual(before, (current / "supervised_session.json").read_bytes()); self.assertEqual(len(calls), 1); self.assertFalse(history.exists())
                self.tearDown(); self.setUp()

    def test_staged_launch_preserves_replaced_lock_and_refuses_activation(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); lock = state_path.parent / "orchestrate.lock"; calls = []
        def replace_lock(spec):
            calls.append(spec); lock.rename(lock.with_name("previous-lock")); lock.write_text("new owner")
            return {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", replace_lock), 2)
        self.assertEqual(json.loads(output.getvalue())["delivery"], "uncertain"); self.assertEqual(lock.read_text(), "new owner"); self.assertEqual(json.loads(state_path.read_text())["phase"], "coordinator_initial"); self.assertEqual(json.loads((current / "supervised_session.json").read_text())["state"], "PREPARING_DEVELOPER_DELIVERY"); self.assertEqual(len(calls), 1)

    def test_reviewer_launch_and_accept_refuse_review_diff_drift(self) -> None:
        for when in ("before_launch", "before_accept", "stale_report", "developer_evidence"):
            with self.subTest(when=when):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); calls = []
                def launcher(spec): calls.append(spec); return {"window":"w", "tab":"t"+str(len(calls)+1), "session":"s"+str(len(calls)+1), "result":"role_delivery_confirmed"}
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 0)
                (root / "developer-result").write_text("expected")
                self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
                if when == "before_accept":
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launcher), 0)
                    self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":[], "human_reason":None, "human_category":None})
                if when in ("before_launch", "before_accept"): (root / "developer-result").write_text("changed")
                if when == "stale_report": (current / ".reviewer.json").write_text("stale")
                if when == "developer_evidence": (current / ".developer.json").write_text("{}")
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer") if when == "before_accept" else ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launcher)
                self.assertEqual(result, 2); self.assertEqual(json.loads(out.getvalue())["outcome"], "refusal"); self.assertFalse(history.exists()); self.assertEqual(len(calls), 2 if when == "before_accept" else 1)
                self.tearDown(); self.setUp()

    def test_blocked_developer_and_rejected_reviewer_stop_once(self) -> None:
        for stopped_role in ("developer", "reviewer"):
            with self.subTest(role=stopped_role):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); calls = []
                def launcher(spec): calls.append(spec); return {"window":"w", "tab":"t"+str(len(calls)+1), "session":"s"+str(len(calls)+1), "result":"role_delivery_confirmed"}
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 0)
                missing = io.StringIO(); before = state_path.read_bytes()
                with contextlib.redirect_stdout(missing): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 2)
                self.assertIn("expected_evidence", json.loads(missing.getvalue())); self.assertEqual(before, state_path.read_bytes())
                self.write_json(current / ".developer.json", {"status":"BLOCKED" if stopped_role == "developer" else "DONE", "summary":"blocked" if stopped_role == "developer" else "done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":"unresolved_requirement" if stopped_role == "developer" else None})
                if stopped_role == "reviewer":
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
                        self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launcher), 0)
                    self.write_json(current / ".reviewer.json", {"verdict":"HUMAN_REQUIRED", "summary":"issues", "findings":["issue"], "evidence":[], "human_reason":"human decision required", "human_category":"unresolved_requirement"})
                output = io.StringIO()
                with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, stopped_role), 2)
                self.assertEqual(json.loads(output.getvalue())["outcome"], "terminal"); saved = {p: p.read_bytes() for p in history.rglob("*") if p.is_file()}
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, stopped_role), 2)
                self.assertEqual(saved, {p: p.read_bytes() for p in history.rglob("*") if p.is_file()}); self.assertEqual(len(calls), 1 if stopped_role == "developer" else 2)
                self.tearDown(); self.setUp()

    def test_staged_active_role_invalid_and_symlink_outputs_stop_without_ingestion(self) -> None:
        for role_name in ("developer", "reviewer"):
            for variant in ("malformed", "symlink", "dangling"):
                with self.subTest(role=role_name, variant=variant):
                    config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); calls = []
                    def launcher(spec): calls.append(spec); return {"window":"w", "tab":"t"+str(len(calls)+1), "session":"s"+str(len(calls)+1), "result":"role_delivery_confirmed"}
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 0)
                    if role_name == "reviewer":
                        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
                        with contextlib.redirect_stdout(io.StringIO()):
                            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
                            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launcher), 0)
                    artifact = current / f".{role_name}.json"; outside = root.parent / (root.name + "-outside-test"); payload = b"external evidence sentinel"
                    try:
                        if variant == "malformed": artifact.write_text("{bad")
                        else:
                            if variant == "symlink": outside.write_bytes(payload)
                            artifact.symlink_to(outside)
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, role_name), 2)
                        self.assertEqual(json.loads(output.getvalue())["outcome"], "terminal"); self.assertEqual(len(calls), 1 if role_name == "developer" else 2)
                        for item in history.rglob("*"):
                            if item.is_file(): self.assertNotIn(payload, item.read_bytes())
                        if variant != "malformed": self.assertFalse((history / "001" / f".{role_name}.json").exists()); self.assertTrue(artifact.is_symlink())
                        if variant == "symlink": self.assertEqual(outside.read_bytes(), payload)
                    finally: outside.unlink(missing_ok=True)
                    self.tearDown(); self.setUp()

    def test_production_launch_uses_configured_current_and_owned_paths(self) -> None:
        self.write_config(paths={"current":"run-data/live", "history":"run-data/archive", "state":"run-data/state.json"})
        config, root, (authority, approval, current, history, state_path) = self.locations(); calls = []
        delivery = {"window":"w", "tab":"t1", "session":"s1", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda spec: calls.append(spec) or delivery), 0)
        self.assertEqual(calls[0]["current"], str(current)); self.assertEqual(calls[0]["authority"], str(authority)); self.assertEqual(calls[0]["sandbox"], "workspace-write"); self.assertEqual(calls[0]["command"], ["fake-session", "coordinator"])
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE", "summary":"go", "next_prompt":None, "human_reason":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        self.assertTrue((current / ".coordinator.json").exists()); self.assertFalse((root / ".agent/runtime/current/.coordinator.json").exists())

    def test_coordinator_report_only_allows_accept_and_protected_changes_refuse(self) -> None:
        for mode in ("report_only", "code", "ignored_code", "excluded_code", "authority", "approval", "session", "other_report", "state", "state_reformat", "history"):
            with self.subTest(mode=mode):
                config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.clean_baseline = self.old_clean
                (root / ".gitignore").write_text(".runtime/\nignored/\nsecrets/\n"); subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True)
                delivery = {"window":"w", "tab":"t1", "session":"s1", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery), 0)
                self.write_json(current / ".coordinator.json", {"status":"CONTINUE", "summary":"go", "next_prompt":None, "human_reason":None, "human_category":None})
                if mode == "code": (root / "unexpected.py").write_text("changed")
                if mode == "ignored_code": (root / "ignored").mkdir(); (root / "ignored" / "unexpected.py").write_text("changed")
                if mode == "excluded_code": (root / "secrets").mkdir(); (root / "secrets" / "unexpected.py").write_text("SECRET_SENTINEL")
                if mode == "authority": authority.write_text("changed")
                if mode == "approval": approval.write_text('{"approvals": [1]}')
                if mode == "session":
                    session = json.loads((current / "supervised_session.json").read_text()); session["extra"] = "changed"; self.write_json(current / "supervised_session.json", session)
                if mode == "other_report": (current / ".reviewer.json").write_text("{}")
                if mode == "state":
                    state = json.loads(state_path.read_text()); state["extra"] = "changed"; self.write_json(state_path, state)
                if mode == "state_reformat": state_path.write_text(json.dumps(json.loads(state_path.read_text())))
                if mode == "history": (history / "777").mkdir(parents=True); (history / "777" / "keep").write_text("keep")
                output = io.StringIO()
                with contextlib.redirect_stdout(output): result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator")
                self.assertEqual(result, 0 if mode == "report_only" else 2, output.getvalue())
                if mode == "report_only":
                    calls = []
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", lambda spec: calls.append(spec) or {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}), 0)
                    self.assertEqual(len(calls), 1); self.assertEqual(calls[0]["sandbox"], "workspace-write"); self.assertIn(str(current / ".developer.json"), calls[0]["handoff"])
                else:
                    self.assertNotEqual(json.loads(state_path.read_text()).get("phase"), "developer")
                    if mode == "excluded_code": self.assertNotIn("SECRET_SENTINEL", state_path.read_text()); self.assertNotIn("secrets/unexpected.py", state_path.read_text())
                self.tearDown(); self.setUp()

    def test_reviewer_protected_evidence_changes_prevent_completion(self) -> None:
        for mode in ("report_only", "code", "authority", "approval", "snapshot", "baseline", "developer_report", "other_report", "session", "history"):
            with self.subTest(mode=mode):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); launched = []
                def launcher(spec): launched.append(spec); return {"window":"w", "tab":"t"+str(len(launched)+1), "session":"s"+str(len(launched)+1), "result":"role_delivery_confirmed"}
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 0)
                (root / "approved.py").write_text("approved")
                self.write_json(current / ".developer.json", {"status":"DONE", "summary":"developer evidence", "files_changed":["approved.py"], "validation":["tested"], "self_check":["scope verified"], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
                    self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launcher), 0)
                self.assertEqual(launched[-1]["sandbox"], "workspace-write"); self.assertIn(str(current / ".reviewer.json"), launched[-1]["handoff"])
                startup = ORCHESTRATOR.interactive_session_command(launched[-1]); self.assertIn("-s workspace-write", startup); self.assertIn(str(root / "assets/reviewer.md"), startup); self.assertIn(str(current / ".reviewer.json"), startup); self.assertIn(str(current / "dev_report.md"), startup)
                self.assertFalse(next(item for item in config["roles"] if item["name"] == "reviewer")["write_capable"]); self.assertTrue(next(item for item in config["roles"] if item["name"] == "developer")["write_capable"])
                self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"review evidence", "findings":[], "evidence":["checked"], "human_reason":None, "human_category":None})
                if mode == "code": (root / "approved.py").write_text("unauthorized reviewer change")
                if mode == "authority": authority.write_text("tampered")
                if mode == "approval": approval.write_text('{"approvals": [1]}')
                if mode == "snapshot": (current / "authoritative_task.md").write_text("tampered")
                if mode == "baseline": (current / "baseline.json").write_text("{}")
                if mode == "developer_report": (current / "dev_report.md").write_text("tampered")
                if mode == "other_report": (current / ".coordinator.json").write_text("tampered")
                if mode == "session":
                    session = json.loads((current / "supervised_session.json").read_text()); session["extra"] = "changed"; self.write_json(current / "supervised_session.json", session)
                if mode == "history": (history / "777").mkdir(parents=True); (history / "777" / "keep").write_text("keep")
                output = io.StringIO()
                with contextlib.redirect_stdout(output): result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer")
                self.assertEqual(result, 0 if mode == "report_only" else 2, output.getvalue())
                if mode == "report_only":
                    self.assertIn("scope verified", (current / "dev_report.md").read_text()); self.assertIn("review evidence", (current / "review_report.md").read_text())
                    initial = (current / ".coordinator.json").read_bytes(); archived = {p: p.read_bytes() for p in history.rglob("*") if p.is_file()}
                    status = io.StringIO()
                    with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
                    self.assertEqual(json.loads(status.getvalue())["owned_report"], str(current / "coordinator_summary.md"))
                    (current / "coordinator_summary.md").write_text("Completed iteration 1; see authoritative_task.md, dev_report.md and review_report.md; proposed next task is non-authoritative.")
                    self.assertEqual(initial, (current / ".coordinator.json").read_bytes()); self.assertEqual(archived, {p: p.read_bytes() for p in history.rglob("*") if p.is_file()})
                    summary_status = io.StringIO()
                    with contextlib.redirect_stdout(summary_status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
                    self.assertIn("inspect coordinator summary", json.loads(summary_status.getvalue())["next_action"])
                    archived_review = history / "001" / "review_report.md"; archived_review.write_text("unauthorized history change")
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 2)
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 2)
                    self.assertEqual(len(launched), 2)
                else: self.assertFalse((history / "001").exists()); self.assertFalse((current / "review_report.md").exists())
                self.tearDown(); self.setUp()

    def test_complete_app_trigger_cycle_binds_attempts_and_preserves_archive(self) -> None:
        configuration = json.loads((self.agent / "controller.json").read_text()); configuration["task_authority"] = "tasks/tâsk $(literal).md"
        (self.root / configuration["task_authority"]).write_text("task-one\n"); self.write_json(self.agent / "controller.json", configuration)
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); launches = []; deliveries = []
        def launcher(spec): launches.append(spec); return {"window":"w", "tab":"t"+str(len(launches)+1), "session":"s"+str(len(launches)+1), "result":"role_delivery_confirmed"}
        def sender(spec):
            deliveries.append(spec); session = json.loads((current / "supervised_session.json").read_text()); role = ("developer", "reviewer", "coordinator")[len(deliveries)-1]
            attempt = session["trigger_attempts"][role]; self.assertEqual(attempt["status"], "prepared"); self.assertEqual(attempt["payload_sha256"], ORCHESTRATOR.digest(spec["payload"].encode())); self.assertNotIn("\n", spec["payload"])
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{key:spec[key] for key in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launcher), 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 0)
        self.assertEqual(json.loads(output.getvalue())["delivery"], "confirmed"); self.assertTrue(deliveries[0]["payload"].startswith("do next prompt ")); self.assertEqual(deliveries[0]["tab"], "t2")
        session_before = (current / "supervised_session.json").read_bytes(); state_before = state_path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 2)
        self.assertEqual(session_before, (current / "supervised_session.json").read_bytes()); self.assertEqual(state_before, state_path.read_bytes()); self.assertEqual(len(deliveries), 1)
        context = json.loads(deliveries[0]["payload"].split(": ", 1)[1]); self.assertEqual(context["snapshot"], str(current / "authoritative_task.md")); self.assertEqual(context["task_authority"], str(authority)); self.assertEqual(context["coordinator_report"], str(current / ".coordinator.json")); self.assertEqual(context["iteration"], 1)
        view = io.StringIO(); state_before = state_path.read_bytes(); session_before = (current / "supervised_session.json").read_bytes()
        with contextlib.redirect_stdout(view): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(view.getvalue())["trigger_status"], "awaiting_output"); self.assertEqual(json.loads(view.getvalue())["transport"], "confirmed"); self.assertEqual(json.loads(view.getvalue())["role_output"], "not_observed"); self.assertEqual(state_before, state_path.read_bytes()); self.assertEqual(session_before, (current / "supervised_session.json").read_bytes())
        (root / "marker").write_text("done")
        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":["marker"], "validation":[], "self_check":["checked"], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        observed = io.StringIO()
        with contextlib.redirect_stdout(observed): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(observed.getvalue())["transport"], "confirmed"); self.assertEqual(json.loads(observed.getvalue())["role_output"], "present_unvalidated")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launcher), 0)
            self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "reviewer", True, sender), 0)
        self.assertTrue(deliveries[1]["payload"].startswith("review latest ")); self.assertEqual(deliveries[1]["session"], "s3"); self.assertEqual(json.loads(deliveries[1]["payload"].split(": ", 1)[1])["developer_report"], str(current / "dev_report.md"))
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":["checked"], "human_reason":None, "human_category":None})
        self.label_mock.return_value = {"status":"failed", "reason":"injected"}; accepted = io.StringIO()
        with contextlib.redirect_stdout(accepted): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 0)
        self.assertEqual(json.loads(accepted.getvalue())["labels"]["reviewer"]["status"], "failed"); self.assertTrue((history / "001").is_dir())
        archive_before = {path: path.read_bytes() for path in history.rglob("*") if path.is_file()}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, sender), 0)
        self.assertTrue(deliveries[2]["payload"].startswith("coordinate latest ")); self.assertEqual(deliveries[2]["session"], "s1"); context = json.loads(deliveries[2]["payload"].split(": ", 1)[1]); self.assertEqual(context["archive"], str(history / "001")); self.assertEqual(context["report"], str(current / "coordinator_summary.md")); self.assertEqual(context["reviewer_report"], str(current / "review_report.md"))
        self.assertEqual(archive_before, {path: path.read_bytes() for path in history.rglob("*") if path.is_file()})
        attempts = json.loads((current / "supervised_session.json").read_text())["trigger_attempts"]
        self.assertEqual(set(attempts), {"developer", "reviewer", "coordinator"}); self.assertEqual(len({item["id"] for item in attempts.values()}), 3); self.assertTrue(all(item["status"] == "confirmed" for item in attempts.values()))
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, sender), 2)
        (current / "coordinator_summary.md").write_text("Completed iteration 1")
        view = io.StringIO()
        with contextlib.redirect_stdout(view): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertEqual(json.loads(view.getvalue())["trigger_status"], "output_present"); self.assertEqual(len(deliveries), 3); self.assertEqual(len(launches), 2)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, sender), 2)
        self.assertEqual(len(deliveries), 3)
        self.assertEqual(archive_before, {path: path.read_bytes() for path in history.rglob("*") if path.is_file()})

    def test_trigger_preflight_refusals_do_not_deliver_or_change_evidence(self) -> None:
        for mode in ("not_ready", "wrong_role", "existing_report", "snapshot", "authority", "baseline", "session", "run", "lock"):
            with self.subTest(mode=mode):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); calls = []
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", lambda _: {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}), 0)
                lock = None
                if mode == "existing_report": (current / ".developer.json").write_text("{}")
                if mode == "snapshot": (current / "authoritative_task.md").write_text("changed")
                if mode == "authority": authority.write_text("changed")
                if mode == "baseline": (root / "unauthorized.py").write_text("changed")
                if mode == "session":
                    session = json.loads((current / "supervised_session.json").read_text()); session["tab"]["session"] = "wrong"; self.write_json(current / "supervised_session.json", session)
                if mode == "run":
                    run_state = json.loads(state_path.read_text()); run_state["active_iteration"] = 2; self.write_json(state_path, run_state)
                if mode == "lock": lock = ORCHESTRATOR.acquire_lock(state_path.parent)
                before = {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}; state_before = state_path.read_bytes(); output = io.StringIO()
                with contextlib.redirect_stdout(output): result = ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "reviewer" if mode == "wrong_role" else "developer", mode != "not_ready", calls.append)
                self.assertEqual(result, 2); self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(calls, []); self.assertEqual(before, {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}); self.assertEqual(state_before, state_path.read_bytes()); self.assertFalse(history.exists())
                if lock: self.assertTrue(lock.exists()); ORCHESTRATOR.release_lock(lock)
                self.tearDown(); self.setUp()

    def test_trigger_delivery_and_persistence_failures_do_not_resend(self) -> None:
        for failure in ("prepare", "prepare_partial", "send", "crash", "confirm"):
            with self.subTest(failure=failure):
                config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); calls = []
                with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", lambda _: {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}), 0)
                original = ORCHESTRATOR.write_json
                def write(path, data):
                    attempt = data.get("trigger_attempts", {}).get("developer", {}) if isinstance(data, dict) else {}
                    if path == current / "supervised_session.json" and failure == "prepare_partial" and attempt.get("status") == "prepared":
                        original(path, data); raise OSError("injected partial persistence failure")
                    if path == current / "supervised_session.json" and ((failure == "prepare" and attempt.get("status") == "prepared") or (failure == "confirm" and attempt.get("status") == "confirmed")): raise OSError("injected persistence failure")
                    return original(path, data)
                def sender(spec):
                    calls.append(spec)
                    if failure == "send": raise RuntimeError("partial send")
                    if failure == "crash": raise KeyboardInterrupt()
                    return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{key:spec[key] for key in ("window", "tab", "session")}}
                output = io.StringIO()
                with mock.patch.object(ORCHESTRATOR, "write_json", side_effect=write), contextlib.redirect_stdout(output):
                    if failure == "crash":
                        with self.assertRaises(KeyboardInterrupt): ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender)
                    else: self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 2)
                self.assertEqual(len(calls), 0 if failure in ("prepare", "prepare_partial") else 1)
                if failure == "prepare_partial":
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 2)
                    self.assertEqual(calls, [])
                elif failure != "prepare":
                    session = json.loads((current / "supervised_session.json").read_text()); self.assertIn(session["trigger_attempts"]["developer"]["status"], ("prepared", "uncertain"))
                    (current / ".developer.json").write_text("{}")
                    view = io.StringIO()
                    with contextlib.redirect_stdout(view): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
                    self.assertEqual(json.loads(view.getvalue())["trigger_status"], "delivery_uncertain"); self.assertEqual(json.loads(view.getvalue())["transport"], "uncertain"); self.assertEqual(json.loads(view.getvalue())["role_output"], "present_unvalidated")
                    with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 2)
                    self.assertEqual(len(calls), 1)
                self.assertFalse(history.exists()); self.tearDown(); self.setUp()

    def test_reviewer_trigger_refuses_changed_review_identity(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); deliveries = []; launches = []
        def launch(spec): launches.append(spec); return {"window":"w", "tab":"t"+str(len(launches)+1), "session":"s"+str(len(launches)+1), "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
        (root / "post-accept-change").write_text("unexpected"); before = (current / "supervised_session.json").read_bytes(); output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "reviewer", True, deliveries.append), 2)
        self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(deliveries, []); self.assertEqual(before, (current / "supervised_session.json").read_bytes()); self.assertFalse(history.exists())

    def test_return_delivery_failure_is_uncertain_and_never_resent(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); events = []
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", lambda _: {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}), 0)
        class Session:
            session_id = "s2"
            async def async_get_variable(self, _): return "codex"
            async def async_send_text(self, text, suppress_broadcast=False):
                events.append((text, suppress_broadcast))
                if text == "\r": raise RuntimeError("return request failed")
        class Tab: tab_id = "t2"; sessions = [Session()]
        class Window: window_id = "w"; tabs = [Tab()]
        async def app(_): return types.SimpleNamespace(terminal_windows=[Window()])
        bridge = ROOT / ".agent/iterm_probe.py"
        def runner(args, **kwargs):
            fake = fake_trigger_iterm(app)
            captured = io.StringIO()
            with mock.patch.dict(sys.modules, {"iterm2":fake}), mock.patch.object(sys, "stdin", io.StringIO(kwargs["input"])), contextlib.redirect_stdout(captured):
                exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
            return subprocess.CompletedProcess(args, 0, captured.getvalue(), "")
        def sender(spec): return ORCHESTRATOR.deliver_iterm_trigger(spec, runner)
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 2)
        self.assertEqual(json.loads(output.getvalue())["delivery"], "uncertain"); self.assertEqual(len(events), 2); self.assertTrue(events[0][0].startswith("do next prompt ")); self.assertEqual(events[1], ("\r", True)); self.assertTrue(events[0][1])
        self.assertEqual(json.loads((current / "supervised_session.json").read_text())["trigger_attempts"]["developer"]["status"], "uncertain")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, sender), 2)
        self.assertEqual(len(events), 2); self.assertFalse(history.exists())

    def test_final_trigger_confirmation_failure_preserves_completed_archive(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture(); launches = []; sends = []
        def launch(spec): launches.append(spec); return {"window":"w", "tab":"t"+str(len(launches)+1), "session":"s"+str(len(launches)+1), "result":"role_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", launch), 0)
        self.write_json(current / ".developer.json", {"status":"DONE", "summary":"done", "files_changed":[], "validation":[], "self_check":[], "known_issues":[], "commit_or_diff_reference":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer"), 0)
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "reviewer", launch), 0)
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED", "summary":"ok", "findings":[], "evidence":[], "human_reason":None, "human_category":None})
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer"), 0)
        archived = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}; original = ORCHESTRATOR.write_json
        def write(path, data):
            attempt = data.get("trigger_attempts", {}).get("coordinator", {}) if isinstance(data, dict) else {}
            if path == current / "supervised_session.json" and attempt.get("status") == "confirmed": raise OSError("injected confirmation failure")
            return original(path, data)
        def send(spec): sends.append(spec); return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{key:spec[key] for key in ("window", "tab", "session")}}
        out = io.StringIO()
        with mock.patch.object(ORCHESTRATOR, "write_json", side_effect=write), contextlib.redirect_stdout(out): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, send), 2)
        self.assertEqual(json.loads(out.getvalue())["delivery"], "uncertain"); self.assertEqual(len(sends), 1)
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, send), 2)
        self.assertEqual(len(sends), 1); self.assertEqual(archived, {p:p.read_bytes() for p in history.rglob("*") if p.is_file()})

    def test_terminal_run_refuses_trigger_without_mutation(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery), 0)
        self.write_json(current / ".coordinator.json", {"status":"HUMAN_REQUIRED", "summary":"stop", "next_prompt":None, "human_reason":"stop", "human_category":"unresolved_requirement"})
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        before = state_path.read_bytes(); archived = {p:p.read_bytes() for p in history.rglob("*") if p.is_file()}; calls = []
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "coordinator", True, calls.append), 2)
        self.assertEqual(calls, []); self.assertEqual(before, state_path.read_bytes()); self.assertEqual(archived, {p:p.read_bytes() for p in history.rglob("*") if p.is_file()})

    def test_changed_coordinator_task_refuses_without_mutation(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations()
        delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE", "summary":"proposal", "next_prompt":"changed", "human_reason":None, "human_category":None})
        before = {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}; state_before = state_path.read_bytes(); authority_before = authority.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal")
        self.assertEqual(before, {p: p.read_bytes() for p in current.rglob("*") if p.is_file()})
        self.assertEqual(state_before, state_path.read_bytes()); self.assertEqual(authority_before, authority.read_bytes()); self.assertFalse(history.exists())

    def test_corrupt_state_refuses_all_coordinator_entrypoints_without_mutation(self) -> None:
        variants = (None, b"{bad", b"[]", b"{}", b'{"iteration":true}', b'{"iteration":0,"status":[]}', b'{"iteration":0,"status":null}', b'{"iteration":0,"status":"RUNNING","phase":"coordinator_initial"}')
        for data in variants:
            for command in ("start", "accept", "status", "cycle"):
                with self.subTest(data=data, command=command):
                    config, root, (authority, approval, current, history, state_path) = self.locations()
                    if data is None: state_path.unlink()
                    else: state_path.write_bytes(data)
                    history.mkdir(); (history / "existing").write_bytes(b"history")
                    launches = []; output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        if command == "start": result = ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, launches.append)
                        elif command == "accept": result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator")
                        elif command == "cycle": result = ORCHESTRATOR.supervised_cycle(root, config, authority, current, history, state_path)
                        else: result = ORCHESTRATOR.supervised_view(root, config, current, history, state_path, command)
                    self.assertEqual(result, 2); self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(state_path.read_bytes() if state_path.exists() else None, data); self.assertEqual((history / "existing").read_bytes(), b"history"); self.assertFalse(current.exists()); self.assertEqual(launches, [])
                    self.tearDown(); self.setUp()

    def test_unreadable_state_refuses_without_history_or_launch(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); before = state_path.read_bytes(); original = Path.read_text
        def unreadable(path, *args, **kwargs):
            if path == state_path: raise PermissionError("injected state read failure")
            return original(path, *args, **kwargs)
        for command in ("start", "accept", "status"):
            output = io.StringIO(); launches = []
            with mock.patch.object(Path, "read_text", unreadable), contextlib.redirect_stdout(output):
                if command == "start": result = ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, launches.append)
                elif command == "accept": result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator")
                else: result = ORCHESTRATOR.supervised_view(root, config, current, history, state_path, command)
            self.assertEqual(result, 2); self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(state_path.read_bytes(), before); self.assertFalse(current.exists()); self.assertFalse(history.exists()); self.assertEqual(launches, [])

    def test_duplicate_start_and_wrong_role_preserve_run(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); launches = []
        delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda spec: launches.append(spec) or delivery)
        before = {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}; state_before = state_path.read_bytes()
        for operation in (lambda: ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, launches.append), lambda: ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "reviewer")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(operation(), 2)
            self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(before, {p: p.read_bytes() for p in current.rglob("*") if p.is_file()}); self.assertEqual(state_before, state_path.read_bytes()); self.assertFalse(history.exists()); self.assertEqual(len(launches), 1)

    def test_terminal_persistence_collision_and_write_failure_are_disclosed(self) -> None:
        for failure in ("collision", "stop_write", "archive_write"):
            with self.subTest(failure=failure):
                config, root, (authority, approval, current, history, state_path) = self.locations(); delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
                ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
                (current / ".coordinator.json").write_text("{bad")
                if failure == "collision":
                    (history / "001").mkdir(parents=True); (history / "001" / "keep").write_bytes(b"keep")
                    state = json.loads(state_path.read_text()); ORCHESTRATOR.record_runtime_guard(current, history, state_path, state, "coordinator")
                original = ORCHESTRATOR.write_json
                def fail_stop(path, value):
                    if (failure == "stop_write" and path == current / "human_stop.json") or (failure == "archive_write" and path == history / "001" / "state.json"): raise OSError("injected failure")
                    return original(path, value)
                output = io.StringIO()
                with mock.patch.object(ORCHESTRATOR, "write_json", side_effect=fail_stop if failure != "collision" else original), contextlib.redirect_stdout(output):
                    self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
                result = json.loads(output.getvalue()); self.assertEqual(result["outcome"], "refusal"); self.assertIn("partial_effects", result); self.assertNotIn("stop_evidence", result)
                self.assertTrue((current / "supervised_session.json").exists()); self.assertEqual(json.loads(state_path.read_text())["status"], "RUNNING")
                if failure == "collision": self.assertEqual((history / "001" / "keep").read_bytes(), b"keep")
                if failure == "archive_write":
                    self.assertTrue((history / "001" / "human_stop.json").exists())
                    observed = io.StringIO()
                    with contextlib.redirect_stdout(observed): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 2)
                    self.assertEqual(json.loads(observed.getvalue())["outcome"], "refusal"); self.assertNotIn("next_action", json.loads(observed.getvalue()))
                self.tearDown(); self.setUp()

    def test_inconsistent_session_and_unreadable_output_terminalize_identified_run(self) -> None:
        for case in ("session", "unreadable", "schema"):
            with self.subTest(case=case):
                config, root, (authority, approval, current, history, state_path) = self.locations(); delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
                ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
                artifact = current / ".coordinator.json"; artifact.write_text("{}")
                if case == "session":
                    path = current / "supervised_session.json"; session = json.loads(path.read_text()); del session["launch_mode"]; self.write_json(path, session)
                    saved_state = json.loads(state_path.read_text()); ORCHESTRATOR.record_runtime_guard(current, history, state_path, saved_state, "coordinator")
                original_open = os.open
                def open_file(path, *args, **kwargs):
                    if case == "unreadable" and path == artifact: raise PermissionError("injected unreadable output")
                    return original_open(path, *args, **kwargs)
                output = io.StringIO()
                with mock.patch.object(os, "open", open_file), contextlib.redirect_stdout(output):
                    self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
                result = json.loads(output.getvalue()); self.assertEqual(result["outcome"], "terminal"); self.assertIn("stop_evidence", result); self.assertTrue((history / "001" / ".coordinator.json").exists()); self.assertFalse((current / "supervised_session.json").exists())
                self.tearDown(); self.setUp()

    def test_coordinator_output_symlinks_are_invalid_and_never_archived(self) -> None:
        for target_exists in (True, False):
            with self.subTest(target_exists=target_exists):
                config, root, (authority, approval, current, history, state_path) = self.locations()
                launches = []; delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
                self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda spec: launches.append(spec) or delivery), 0)
                target = root.parent / (root.name + "-outside.json")
                payload = b'{"status":"CONTINUE","summary":"external sentinel","next_prompt":null,"human_reason":null,"human_category":null}'
                try:
                    if target_exists: target.write_bytes(payload)
                    output_path = current / ".coordinator.json"; output_path.symlink_to(target)
                    captured = io.StringIO(); original_read = Path.read_text
                    def guard_read(path, *args, **kwargs):
                        if path == output_path or path == target: raise AssertionError("symlink target was read")
                        return original_read(path, *args, **kwargs)
                    with mock.patch.object(Path, "read_text", guard_read), contextlib.redirect_stdout(captured):
                        result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator")
                    message = json.loads(captured.getvalue())
                    self.assertEqual(result, 2); self.assertEqual(message["outcome"], "terminal"); self.assertEqual(message["category"], "failed_or_incomplete_validation")
                    self.assertIn("symbolic link", message["reason"]); self.assertIn("stop_evidence", message); self.assertNotIn("expected_evidence", message)
                    self.assertEqual([spec["role"] for spec in launches], ["coordinator"]); self.assertEqual(json.loads(state_path.read_text())["status"], "HUMAN_REQUIRED")
                    self.assertTrue(output_path.is_symlink()); self.assertFalse((history / "001" / ".coordinator.json").exists()); self.assertFalse((history / "001" / ".coordinator.json").is_symlink())
                    for archived in history.rglob("*"):
                        if archived.is_file(): self.assertNotIn(b"external sentinel", archived.read_bytes())
                    if target_exists: self.assertEqual(target.read_bytes(), payload)
                    else: self.assertFalse(target.exists())
                finally:
                    target.unlink(missing_ok=True)
                self.tearDown(); self.setUp()

    def test_later_role_symlink_evidence_is_not_read_or_archived(self) -> None:
        for role in ("developer", "reviewer"):
            for target_exists in (True, False):
                with self.subTest(role=role, target_exists=target_exists):
                    config, root, (authority, approval, current, history, state_path) = self.locations()
                    delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
                    ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
                    state = json.loads(state_path.read_text()); state["phase"] = role; state.pop("evidence_guard"); self.write_json(state_path, state)
                    session = json.loads((current / "supervised_session.json").read_text()); session["phase"] = role; session.pop("launch_mode"); self.write_json(current / "supervised_session.json", session)
                    target = root.parent / (root.name + "-role-output.json"); payload = b"external role evidence sentinel"
                    try:
                        if target_exists: target.write_bytes(payload)
                        artifact = current / f".{role}.json"; artifact.symlink_to(target)
                        result_text = io.StringIO()
                        with contextlib.redirect_stdout(result_text): result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, role)
                        result_json = json.loads(result_text.getvalue()); self.assertEqual(result, 2); self.assertEqual(result_json["outcome"], "terminal"); self.assertIn("symbolic link", result_json["reason"])
                        self.assertTrue(artifact.is_symlink()); self.assertFalse((history / "001" / f".{role}.json").is_symlink()); self.assertFalse((history / "001" / f".{role}.json").exists())
                        for item in history.rglob("*"):
                            if item.is_file(): self.assertNotIn(payload, item.read_bytes())
                        if target_exists: self.assertEqual(target.read_bytes(), payload)
                        else: self.assertFalse(target.exists())
                    finally: target.unlink(missing_ok=True)
                    self.tearDown(); self.setUp()

    def test_terminal_coordinator_stop_is_one_time_and_terminal_first(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations()
        delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
        self.write_json(current / ".coordinator.json", {"status":"HUMAN_REQUIRED","summary":"needs scope decision","next_prompt":None,"human_reason":"scope expands","human_category":"scope_expansion"})
        first = io.StringIO()
        with contextlib.redirect_stdout(first): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        terminal = json.loads(first.getvalue()); self.assertEqual(terminal["state"], "HUMAN_REQUIRED"); self.assertEqual(terminal["category"], "scope_expansion"); self.assertNotIn("Start project", first.getvalue())
        self.assertFalse((current / "supervised_session.json").exists()); self.assertFalse((current / "tabs.json").exists()); evidence, state = (current / "human_stop.json").read_bytes(), state_path.read_bytes()
        status = io.StringIO()
        with contextlib.redirect_stdout(status): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assertIn("HUMAN_REQUIRED", status.getvalue()); self.assertNotIn("Start project", status.getvalue())
        history_count = len(list(history.iterdir())); repeated = io.StringIO()
        with contextlib.redirect_stdout(repeated): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        self.assertEqual(len(list(history.iterdir())), history_count); self.assertEqual((current / "human_stop.json").read_bytes(), evidence); self.assertEqual(state_path.read_bytes(), state); self.assertIn("existing stop evidence", repeated.getvalue())

    def test_active_missing_report_is_nonmutating_then_malformed_is_visible_terminal_stop(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); delivery = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
        before_state, before_session, before_tabs = state_path.read_bytes(), (current / "supervised_session.json").read_bytes(), (current / "tabs.json").read_bytes(); output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        self.assertIn("not ready", output.getvalue()); self.assertEqual(state_path.read_bytes(), before_state); self.assertEqual((current / "supervised_session.json").read_bytes(), before_session); self.assertEqual((current / "tabs.json").read_bytes(), before_tabs); self.assertFalse(history.exists())
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"ok","next_prompt":None,"human_reason":None,"human_category":None})
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: delivery)
        (current / ".coordinator.json").write_text("{bad"); terminal = io.StringIO()
        with contextlib.redirect_stdout(terminal): self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        self.assertIn("HUMAN_REQUIRED", terminal.getvalue()); self.assertFalse((current / "supervised_session.json").exists())

    def test_staged_coordinator_start_refuses_or_stops_before_unlaunched_role(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations()
        self.write_json(state_path, {"iteration":0, "status":"READY", "phase":"developer"}); before = state_path.read_bytes(); launched = []
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, launched.append), 2)
        self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(before, state_path.read_bytes()); self.assertFalse(current.exists()); self.assertFalse(history.exists()); self.assertEqual(launched, [])
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: (_ for _ in ()).throw(RuntimeError("active-window failed"))), 2)
        self.assertEqual(json.loads(output.getvalue())["delivery"], "uncertain"); self.assertEqual(json.loads((current / "supervised_session.json").read_text())["state"], "PREPARING_DELIVERY"); self.assertFalse(history.exists()); self.assertFalse((current / "tabs.json").exists())

    def test_staged_coordinator_start_held_lock_refuses_before_mutation_and_releases(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); before = state_path.read_bytes(); lock = ORCHESTRATOR.acquire_lock(state_path.parent)
        try:
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: None), 2)
            self.assertIn("lock exists", json.loads(output.getvalue())["reason"]); self.assertTrue(lock.exists())
        finally:
            lock.unlink()
        self.assertEqual(state_path.read_bytes(), before); self.assertFalse(current.exists()); self.assertFalse(history.exists())
        observation = {"window":"w", "tab":"t", "session":"s", "elapsed_seconds":0, "result":"coordinator_delivery_confirmed"}
        self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: observation), 0)
        self.assertFalse((state_path.parent / "orchestrate.lock").exists())

    def test_replaced_lock_is_not_removed_by_original_invocation(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); lock = state_path.parent / "orchestrate.lock"
        def replaced(_):
            lock.rename(lock.with_name("old-lock")); lock.write_text("other owner")
            raise RuntimeError("delivery uncertain")
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, replaced), 2)
        self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(lock.read_text(), "other owner")

    def test_staged_coordinator_start_requires_real_clean_head_and_authority(self) -> None:
        ORCHESTRATOR.clean_baseline = self.old_clean; config, root, (authority, approval, current, history, state_path) = self.locations()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: None), 2); self.assertFalse(history.exists())
        self.tearDown(); self.setUp(); ORCHESTRATOR.clean_baseline = self.old_clean; config, root, (authority, approval, current, history, state_path) = self.locations()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True)
        (root / "dirty").write_text("x")
        self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: None), 2); self.assertFalse(history.exists())
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); authority.unlink()
        self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path, lambda _: None), 2); self.assertFalse(history.exists())

    def test_trigger_bridge_process_rejects_timeout_and_bad_confirmation(self) -> None:
        spec = {"window":"w", "tab":"t", "session":"s", "payload":"review latest context"}; requests = []
        def success(args, **kwargs):
            requests.append(json.loads(kwargs["input"])); self.assertEqual(kwargs["timeout"], 15)
            return subprocess.CompletedProcess(args, 0, json.dumps({"ok":True, "window":"w", "tab":"t", "session":"s", "result":"trigger_delivery_confirmed", "submission":"carriage_return_sent"}), "")
        self.assertEqual(ORCHESTRATOR.deliver_iterm_trigger(spec, success)["result"], "trigger_delivery_confirmed"); self.assertEqual(requests[0]["payload"], spec["payload"])
        for response in (subprocess.CompletedProcess([], 1, "", "failure"), subprocess.CompletedProcess([], 0, "bad", ""), subprocess.CompletedProcess([], 0, '{"ok":false,"reason":"gone"}', ""), subprocess.CompletedProcess([], 0, '{"ok":true,"window":"w","tab":"other","session":"s","result":"trigger_delivery_confirmed","submission":"carriage_return_sent"}', ""), subprocess.CompletedProcess([], 0, '{"ok":true,"window":"w","tab":"t","session":"s","result":"trigger_delivery_confirmed"}', "")):
            with self.subTest(response=response), self.assertRaises(RuntimeError): ORCHESTRATOR.deliver_iterm_trigger(spec, lambda *_args, response=response, **_kwargs: response)
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            ORCHESTRATOR.deliver_iterm_trigger(spec, lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("fake", 15)))

    def test_native_trigger_bridge_binds_window_tab_session_and_suppresses_broadcast(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"; original_module, original_stdin = sys.modules.get("iterm2"), sys.stdin
        for variant in ("ok", "window", "tab", "session", "shell", "unknown", "text_error", "return_error", "job_changed", "text_nonok", "return_nonok", "missing_status", "settle_error", "destination_gone"):
            with self.subTest(variant=variant):
                sent = []; created = []; events = []
                class Session:
                    session_id = "session"
                    async def async_get_variable(self, key):
                        events.append("job_check"); self.key = key
                        return "zsh" if variant == "shell" or (variant == "job_changed" and sent) else "" if variant == "unknown" else "codex"
                    async def async_send_text(self, value, suppress_broadcast=False):
                        events.append("return" if value == "\r" else "payload"); sent.append((value, suppress_broadcast))
                        if (variant == "text_error" and len(sent) == 1) or (variant == "return_error" and len(sent) == 2): raise RuntimeError("partial send")
                class Tab:
                    tab_id = "tab"
                    sessions = [] if variant == "session" else [Session()]
                class Window:
                    window_id = "window"
                    tabs = [] if variant == "tab" else [Tab()]
                    async def async_create_tab(self): created.append(True)
                app_calls = []
                async def app(_):
                    app_calls.append(True)
                    return types.SimpleNamespace(terminal_windows=[] if variant == "window" or (variant == "destination_gone" and len(app_calls) > 2) else [Window()])
                async def settle(seconds):
                    events.append(("settle", seconds))
                    if variant == "settle_error": raise RuntimeError("settle interrupted")
                def status(value):
                    if variant == "missing_status": return None
                    return 1 if (variant == "text_nonok" and value != "\r") or (variant == "return_nonok" and value == "\r") else 0
                sys.modules["iterm2"] = fake_trigger_iterm(app, status)
                payload = 'do next prompt Controller context: {"task":"/tmp/é space/task"}'
                sys.stdin = io.StringIO(json.dumps({"mode":"role_trigger", "window":"window", "tab":"tab", "session":"session", "payload":payload}, ensure_ascii=False)); out = io.StringIO()
                try:
                    with mock.patch("asyncio.sleep", settle), contextlib.redirect_stdout(out): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
                finally:
                    sys.stdin = original_stdin
                    if original_module is None: sys.modules.pop("iterm2", None)
                    else: sys.modules["iterm2"] = original_module
                result = json.loads(out.getvalue()); self.assertEqual(result["ok"], variant == "ok"); self.assertEqual(created, [])
                if variant in ("ok", "return_error", "return_nonok"): self.assertEqual(sent, [(payload, True), ("\r", True)])
                elif variant in ("text_error", "job_changed", "text_nonok", "missing_status", "settle_error", "destination_gone"): self.assertEqual(sent, [(payload, True)])
                else: self.assertEqual(sent, [])
                if variant in ("ok", "return_error"): self.assertEqual(events, ["job_check", "payload", ("settle", 1.0), "job_check", "return"])
                if variant == "text_error": self.assertEqual(events, ["job_check", "payload"])
                if variant == "job_changed": self.assertEqual(events, ["job_check", "payload", ("settle", 1.0), "job_check"])
                if variant in ("settle_error", "destination_gone"): self.assertEqual(events, ["job_check", "payload", ("settle", 1.0)])
                if variant == "ok": self.assertEqual(result["submission"], "carriage_return_sent")
                if sent:
                    self.assertEqual((result["window"], result["tab"], result["session"]), ("window", "tab", "session"))
                    self.assertEqual(len(result["sends"]), len(sent))
                    for item in result["sends"]: self.assertLessEqual(item["started_monotonic"], item["finished_monotonic"])
                if variant == "ok": self.assertEqual([x["status"] for x in result["sends"]], ["OK", "OK"])
                if variant == "ok": self.assertEqual(result["settle"]["requested_seconds"], 1.0)
                if variant in ("text_nonok", "return_nonok"): self.assertEqual(result["sends"][-1]["status"], "SESSION_NOT_FOUND")

    def test_native_label_targets_exact_destination_with_unicode(self) -> None:
        bridge = ROOT / ".agent/iterm_probe.py"
        for wrong in (None, "window", "tab", "session"):
            titles = []
            class Session: session_id = "s"
            class Tab:
                tab_id = "t"; sessions = [Session()]
                async def async_set_title(self, value): titles.append(value)
            class Window: window_id = "w"; tabs = [Tab()]
            async def app(_): return types.SimpleNamespace(terminal_windows=[Window()])
            fake = types.SimpleNamespace(async_get_app=app, run_until_complete=lambda main: __import__("asyncio").run(main(None)))
            request = {"mode":"role_label", "window":"w", "tab":"t", "session":"s", "title":"ORCHESTR8 · Déveloper · accepté"}
            if wrong: request[wrong] = "wrong"
            output = io.StringIO()
            with mock.patch.dict(sys.modules, {"iterm2":fake}), mock.patch.object(sys, "stdin", io.StringIO(json.dumps(request))), contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
            self.assertEqual(json.loads(output.getvalue())["ok"], wrong is None)
            self.assertEqual(titles, [request["title"]] if wrong is None else [])

    def test_initial_role_labels_match_human_phrases(self) -> None:
        config, root, _ = self.locations()
        expected = {"coordinator":"ORCHESTR8 · Coordinator · waiting for Start project…", "developer":"ORCHESTR8 · Developer · waiting for do next prompt", "reviewer":"ORCHESTR8 · Reviewer · waiting for review latest"}
        for name, title in expected.items(): self.assertEqual(ORCHESTRATOR.tab_spec(root, config, name, production=True)["title"], title)

    def test_bridge_dependency_preflight_uses_interpreter_and_refuses_before_writes(self) -> None:
        calls = []
        ORCHESTRATOR.bridge_environment_preflight(lambda args, **kw: calls.append((args, kw)) or subprocess.CompletedProcess(args, 0, "", ""))
        self.assertEqual(calls[0][0], [sys.executable, "-c", "import iterm2"])
        with self.assertRaisesRegex(RuntimeError, "interpreter.*virtualenv"):
            ORCHESTRATOR.bridge_environment_preflight(lambda args, **kw: subprocess.CompletedProcess(args, 1, "", "missing"))
        config, root, (authority, approval, current, history, state_path) = self.locations()
        before = state_path.read_bytes(); output = io.StringIO()
        with mock.patch.object(ORCHESTRATOR, "bridge_environment_preflight", side_effect=RuntimeError("missing interpreter dependency")), contextlib.redirect_stdout(output):
            self.assertEqual(ORCHESTRATOR.start_supervised(root, config, authority, approval, current, history, state_path), 2)
        self.assertIn("missing interpreter dependency", output.getvalue()); self.assertEqual(state_path.read_bytes(), before); self.assertFalse(current.exists()); self.assertFalse(history.exists())
        self.tearDown(); self.setUp()
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        before = {p:p.read_bytes() for p in current.rglob("*") if p.is_file()}; state_before = state_path.read_bytes(); output = io.StringIO()
        with mock.patch.object(ORCHESTRATOR, "bridge_environment_preflight", side_effect=RuntimeError("missing interpreter dependency")), contextlib.redirect_stdout(output):
            self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer"), 2)
        self.assertIn("missing interpreter dependency", output.getvalue()); self.assertEqual(before, {p:p.read_bytes() for p in current.rglob("*") if p.is_file()}); self.assertEqual(state_before, state_path.read_bytes()); self.assertFalse(history.exists())

    def test_label_failure_does_not_undo_acceptance_or_resend(self) -> None:
        self.label_mock.return_value = {"status":"failed", "reason":"injected"}
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        self.assertEqual(json.loads((current / "supervised_session.json").read_text())["state"], "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", lambda _: {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}), 0)
        sent = []; output = io.StringIO()
        def send(spec):
            sent.append(spec)
            return {"result":"trigger_delivery_confirmed", "submission":"carriage_return_sent", **{k:spec[k] for k in ("window", "tab", "session")}}
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, send), 0)
        self.assertEqual(json.loads(output.getvalue())["label"]["status"], "failed")
        self.assertEqual(json.loads((current / "supervised_session.json").read_text())["trigger_attempts"]["developer"]["status"], "confirmed")
        self.assertEqual(self.label_mock.call_args.args[2], "trigger sent · awaiting report")
        self.label_mock.reset_mock()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.label_mock.assert_not_called()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, send), 2)
        self.assertEqual(len(sent), 1)

    def test_uncertain_delivery_label_is_separate_and_never_resends(self) -> None:
        config, root, authority, approval, current, history, state_path = self.prepare_staged_fixture()
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.launch_staged_role(root, config, authority, current, history, state_path, "developer", lambda _: {"window":"w", "tab":"t2", "session":"s2", "result":"role_delivery_confirmed"}), 0)
        self.label_mock.return_value = {"status":"failed", "reason":"injected"}; calls = []; output = io.StringIO()
        def send(spec): calls.append(spec); raise RuntimeError("partial")
        with contextlib.redirect_stdout(output): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, send), 2)
        self.assertEqual(json.loads(output.getvalue())["label"]["status"], "failed"); self.assertEqual(self.label_mock.call_args.args[2], "delivery uncertain")
        self.assertEqual(json.loads((current / "supervised_session.json").read_text())["trigger_attempts"]["developer"]["status"], "uncertain")
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(ORCHESTRATOR.trigger_staged_role(root, config, authority, approval, current, history, state_path, "developer", True, send), 2)
        self.assertEqual(len(calls), 1)

    def test_native_staged_bridge_targets_recorded_window_and_quoted_command(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"; original_module, original_stdin = sys.modules.get("iterm2"), sys.stdin
        for role_name in ("developer", "reviewer"):
            for available in (True, False):
                with self.subTest(role=role_name, available=available):
                    sent, created = [], []
                    class Session:
                        session_id = "s"
                        async def async_send_text(self, value): sent.append(value)
                    class Tab:
                        tab_id = "t"; current_session = Session()
                        async def async_set_title(self, value): self.title = value
                    class Window:
                        window_id = "target"
                        async def async_create_tab(self): created.append("target"); return Tab()
                    async def app(_): return types.SimpleNamespace(terminal_windows=[Window()] if available else [])
                    sys.modules["iterm2"] = types.SimpleNamespace(async_get_app=app, run_until_complete=lambda main: __import__("asyncio").run(main(None)))
                    spec = {"window":"target", "title":"role", "cwd":"/tmp/path with spaces", "instruction":"/tmp/path with spaces/role.md", "command":["custom cmd", "literal arg"], "sandbox":"workspace-write" if role_name == "developer" else "read-only"}
                    command = ORCHESTRATOR.interactive_session_command(spec)
                    sys.stdin = io.StringIO(json.dumps({"mode":"staged_role_start", "window":"target", "title":"role", "command":command})); output = io.StringIO()
                    try:
                        with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
                    finally:
                        sys.stdin = original_stdin
                        if original_module is None: sys.modules.pop("iterm2", None)
                        else: sys.modules["iterm2"] = original_module
                    result = json.loads(output.getvalue()); self.assertEqual(result["ok"], available)
                    if available:
                        self.assertEqual(created, ["target"]); self.assertEqual(sent, [command + "\n"]); self.assertIn("'custom cmd' 'literal arg'", command); self.assertIn("'/tmp/path with spaces'", command); self.assertIn("-s " + spec["sandbox"], command); self.assertNotIn("do next prompt", command); self.assertNotIn("review latest", command)
                    else: self.assertEqual(created, []); self.assertEqual(sent, [])

    def test_native_coordinator_start_bridge_uses_one_default_tab_and_read_only_command(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"; output, original_module, original_stdin = io.StringIO(), sys.modules.get("iterm2"), sys.stdin; sent = []
        class Session:
            session_id = "session"
            async def async_send_text(self, value): sent.append(value)
        class Tab:
            tab_id = "tab"
            current_session = Session()
            async def async_set_title(self, title): self.title = title
        tab = Tab()
        class Window:
            window_id = "window"
            async def async_create_tab(self): return tab
        async def app(_): return types.SimpleNamespace(current_terminal_window=Window())
        sys.modules["iterm2"] = types.SimpleNamespace(async_get_app=app, run_until_complete=lambda main: __import__("asyncio").run(main(None))); sys.stdin = io.StringIO('{"mode":"coordinator_start","cwd":"/tmp/project","instruction":"/tmp/project/role.md","current":"/tmp/project/run/live","authority":"/tmp/project/task.md","command":["codex"]}')
        try:
            with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
        finally:
            sys.stdin = original_stdin
            if original_module is None: del sys.modules["iterm2"]
            else: sys.modules["iterm2"] = original_module
        response = json.loads(output.getvalue()); self.assertTrue(response["ok"]); self.assertEqual(tab.title, "ORCHESTR8 · Coordinator · waiting for Start project…"); self.assertEqual(len(sent), 1); self.assertIn("codex -C /tmp/project -s workspace-write", sent[0]); self.assertIn("/tmp/project/role.md", sent[0]); self.assertIn("/tmp/project/run/live/.coordinator.json", sent[0]); self.assertIn("/tmp/project/run/live/dev_report.md", sent[0]); self.assertIn("/tmp/project/run/live/review_report.md", sent[0]); self.assertIn("/tmp/project/run/live/coordinator_summary.md", sent[0]); self.assertNotIn("--skip-git-repo-check", sent[0]); self.assertTrue(sent[0].endswith("\n"))

    def test_native_coordinator_start_bridge_reports_each_native_failure(self) -> None:
        bridge = ROOT / ".agent" / "iterm_probe.py"
        def run(failure):
            output, original_module, original_stdin = io.StringIO(), sys.modules.get("iterm2"), sys.stdin
            class Session:
                session_id = "session"
                async def async_send_text(self, _):
                    if failure == "send": raise RuntimeError("send")
            class Tab:
                tab_id = "tab"
                async def async_set_title(self, _):
                    if failure == "title": raise RuntimeError("title")
                @property
                def current_session(self):
                    if failure == "session": raise RuntimeError("session")
                    return None if failure == "session_none" else Session()
            class Window:
                window_id = "window"
                async def async_create_tab(self):
                    if failure == "tab": raise RuntimeError("tab")
                    return None if failure == "tab_none" else Tab()
            class App:
                @property
                def current_terminal_window(self):
                    if failure == "window": raise RuntimeError("window")
                    return None if failure == "window_none" else Window()
            async def get_app(_):
                if failure == "app": raise RuntimeError("app")
                return None if failure == "app_none" else App()
            sys.modules["iterm2"] = types.SimpleNamespace(async_get_app=get_app, run_until_complete=lambda main: __import__("asyncio").run(main(None))); sys.stdin = io.StringIO('{"mode":"coordinator_start","cwd":"/tmp/project","instruction":"/tmp/project/role.md","current":"/tmp/project/run/live","authority":"/tmp/project/task.md","command":["codex"]}')
            try:
                with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
            finally:
                sys.stdin = original_stdin
                if original_module is None: del sys.modules["iterm2"]
                else: sys.modules["iterm2"] = original_module
            return json.loads(output.getvalue())
        for failure in ("app", "app_none", "window", "window_none", "tab", "tab_none", "title", "session", "session_none", "send"):
            with self.subTest(failure=failure):
                response = run(failure); self.assertFalse(response["ok"]); self.assertIn("Coordinator start", response["reason"]); self.assertIn("partial tabs", response["reason"])

    def test_native_coordinator_start_outer_boundary_rejects_bad_delivery(self) -> None:
        expected = {"ok":True, "window":"w", "tab":"t", "session":"s", "elapsed_seconds":0.1, "result":"coordinator_delivery_confirmed"}
        self.assertEqual(ORCHESTRATOR.launch_iterm_coordinator_start({"cwd":"/tmp/project", "instruction":"/tmp/project/role.md", "current":"/tmp/project/run/live", "authority":"/tmp/project/task.md","command":["codex"]}, lambda arguments, **kwargs: subprocess.CompletedProcess(arguments, 0, json.dumps(expected), "")), expected)
        for completed, message in ((subprocess.CompletedProcess([], 1, "", "failed"), "native Coordinator start failed"), (subprocess.CompletedProcess([], 0, "not-json", ""), "malformed diagnostics"), (subprocess.CompletedProcess([], 0, '{"ok":false,"reason":"session failed"}', ""), "session failed"), (subprocess.CompletedProcess([], 0, '{"ok":true,"window":"w","tab":"t","elapsed_seconds":0,"result":"coordinator_delivery_confirmed"}', ""), "incomplete delivery")):
            with self.subTest(message=message):
                with self.assertRaisesRegex(RuntimeError, message): ORCHESTRATOR.launch_iterm_coordinator_start({"cwd":"/tmp/project", "instruction":"/tmp/project/role.md", "current":"/tmp/project/run/live", "authority":"/tmp/project/task.md","command":["codex"]}, lambda *_args, response=completed, **_kwargs: response)

    def test_role_contracts_are_isolated_and_have_non_overlapping_outputs(self) -> None:
        instructions = {name: (ROOT / ".agent" / "roles" / f"{name}.md").read_text() for name in ("coordinator", "developer", "reviewer")}
        outputs = {name: f".{name}.json" for name in instructions}
        self.assertIn("Common task", instructions["coordinator"]); self.assertIn("Coordinator work", instructions["coordinator"])
        self.assertIn("Common task", instructions["developer"]); self.assertIn("Developer work", instructions["developer"]); self.assertIn("Reviewer handoff", instructions["developer"])
        self.assertIn("Common task", instructions["reviewer"]); self.assertIn("Reviewer handoff", instructions["reviewer"]); self.assertIn("Developer work", instructions["reviewer"])
        for name, instruction in instructions.items():
            self.assertIn(outputs[name], instruction)
            for other, output in outputs.items():
                if other != name: self.assertNotIn(output, instruction)

    def test_supervised_accept_uses_c1_baseline_and_structured_stops(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.clean_baseline = self.old_clean
        subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True)
        ORCHESTRATOR.supervised_init(root, config, current, True, lambda _: None)
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"go","next_prompt":None,"human_reason":None,"human_category":None})
        (root / "dirty").write_text("x")
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2)
        self.assertFalse(history.exists())
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.clean_baseline = self.old_clean
        subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True); subprocess.run(["git", "update-ref", "-d", "HEAD"], cwd=root, check=True)
        ORCHESTRATOR.supervised_init(root, config, current, True, lambda _: None); self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"go","next_prompt":None,"human_reason":None,"human_category":None})
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 2); self.assertFalse(history.exists())

    def test_supervised_cycle_refuses_invalid_artifact_preconditions(self) -> None:
        config, root, (authority, _, current, history, state_path) = self.locations(); ORCHESTRATOR.supervised_init(root, config, current, True, lambda _: None)
        self.write_json(session_path := current / "supervised_session.json", {"phase":"reviewer", "state":"WAITING_FOR_HUMAN", "task_snapshot_sha256":"missing"})
        self.assertEqual(ORCHESTRATOR.supervised_cycle(root, config, authority, current, history, state_path), 2)
        self.assertFalse(history.exists())

    def test_supervised_session_malformed_states_stop_for_accept_cycle_and_views(self) -> None:
        cases = (("accept", ["developer"]), ("cycle", {"phase": None}), ("status", {"phase": "unknown"}), ("preview", {"phase": ["reviewer"]}), ("resume", "{bad"))
        for command, payload in cases:
            with self.subTest(command=command):
                config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
                path = current / "supervised_session.json"
                if isinstance(payload, str): path.write_text(payload)
                else: self.write_json(path, payload)
                before, state_before = path.read_bytes(), state_path.read_bytes(); output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    if command == "accept": result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer")
                    elif command == "cycle": result = ORCHESTRATOR.supervised_cycle(root, config, authority, current, history, state_path)
                    else: result = ORCHESTRATOR.supervised_view(root, config, current, history, state_path, command)
                self.assertEqual(result, 2); self.assertEqual(json.loads(output.getvalue())["outcome"], "refusal"); self.assertEqual(path.read_bytes(), before); self.assertEqual(state_path.read_bytes(), state_before); self.assertFalse(history.exists())
                self.tearDown(); self.setUp()

    def test_supervised_phrase_contract_matches_each_displayed_phase(self) -> None:
        expected = {"coordinator_initial": "Start project: <human initial brief>", "developer": "do next prompt", "reviewer": "review latest", "coordinator_review": "coordinate latest"}
        self.assertEqual(ORCHESTRATOR.ROLE_PHRASES, expected)
        for phase, phrase in expected.items(): self.assertEqual(ORCHESTRATOR.next_action(phase).split(": ", 1)[1], phrase)


class InitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.script = ROOT / ".agent" / "orchestrate.py"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_init(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(self.script), "init", "--project-root", str(project), "--task-authority", "docs/NEXT_PROMPT.md", *args], text=True, capture_output=True)

    def test_inherited_quality_contracts_and_report_validation(self) -> None:
        project = self.root / "quality"
        result = self.run_init(project, "--init-git")
        self.assertEqual(result.returncode, 0, result.stderr)
        table = (project / "docs/controller/README.md").read_text()
        self.assertIn("future design guidance", table)
        self.assertIn("not current-behavior evidence", table)
        for number in range(1, 21):
            self.assertIn(f"| Q{number:02d} |", table)
        self.assertIn("Fresh authorized run for an approved change", table)
        for role_name, heading in (("developer", "Mandatory pre-review self-check"), ("reviewer", "Independent review checklist")):
            self.assertIn(heading, (project / f".agent/roles/{role_name}.md").read_text())
        config = json.loads((project / ".agent/controller_config.json").read_text())
        report = {"status": "DONE", "summary": "done", "files_changed": [], "validation": [], "known_issues": [], "commit_or_diff_reference": None, "human_category": None, "self_check": ["scope: passed; diff inspected"]}
        self.assertEqual(ORCHESTRATOR.validate_output(project, config, "developer", report), report)
        variants = [{k: v for k, v in report.items() if k != "self_check"}, dict(report, self_check="bad"), dict(report, self_check=[1]), dict(report, extra=True)]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ORCHESTRATOR.RoleFailure):
                ORCHESTRATOR.validate_output(project, config, "developer", variant)
        reviewer = {"verdict": "APPROVED", "summary": "ok", "findings": [], "evidence": ["checked"], "human_reason": None, "human_category": None}
        self.assertEqual(ORCHESTRATOR.validate_output(project, config, "reviewer", reviewer), reviewer)

    def test_isolated_cli_corrupt_state_refusals_are_json(self) -> None:
        project = self.root / "cli-state"; result = self.run_init(project, "--init-git"); self.assertEqual(result.returncode, 0, result.stderr)
        state = project / ".agent/runtime/state.json"; state.write_bytes(b"{bad")
        for args in (("start", "--tabs"), ("accept", "coordinator"), ("status",)):
            result = subprocess.run([sys.executable, str(self.script), *args], cwd=project, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr); self.assertEqual(json.loads(result.stdout)["outcome"], "refusal"); self.assertEqual(state.read_bytes(), b"{bad"); self.assertFalse((project / ".agent/runtime/current").exists()); self.assertFalse((project / ".agent/runtime/history").exists())

    def test_isolated_cli_launch_unknown_and_wrong_sequence_are_refusals(self) -> None:
        project = self.root / "launch-cli"; result = self.run_init(project, "--init-git"); self.assertEqual(result.returncode, 0, result.stderr)
        state = project / ".agent/runtime/state.json"; before = state.read_bytes()
        for name in ("coordinator", "unknown", "dev", "review"):
            result = subprocess.run([sys.executable, str(self.script), "launch", name], cwd=project, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr); self.assertEqual(json.loads(result.stdout)["outcome"], "refusal"); self.assertEqual(state.read_bytes(), before); self.assertFalse((project / ".agent/runtime/current").exists()); self.assertFalse((project / ".agent/runtime/history").exists())

    def test_trigger_cli_requires_ready_and_valid_phase_without_mutation(self) -> None:
        project = self.root / "trigger-cli"; result = self.run_init(project, "--init-git"); self.assertEqual(result.returncode, 0, result.stderr)
        state = project / ".agent/runtime/state.json"; before = state.read_bytes()
        for args in (("trigger", "developer"), ("trigger", "reviewer", "--ready"), ("trigger", "unknown", "--ready")):
            result = subprocess.run([sys.executable, str(self.script), *args], cwd=project, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr); self.assertEqual(json.loads(result.stdout)["outcome"], "refusal"); self.assertEqual(state.read_bytes(), before); self.assertFalse((project / ".agent/runtime/current").exists()); self.assertFalse((project / ".agent/runtime/history").exists())

    def test_new_project_requires_explicit_git_and_has_no_head(self) -> None:
        project = self.root / "new"
        refused = self.run_init(project)
        self.assertNotEqual(refused.returncode, 0); self.assertFalse(project.exists())
        result = self.run_init(project, "--init-git")
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn("create an initial Git commit/HEAD", result.stdout)
        self.assertTrue((project / ".agent/iterm_probe.py").is_file())
        self.assertIn("def trigger_staged_role", (project / ".agent/orchestrate.py").read_text()); self.assertIn("role_trigger", (project / ".agent/iterm_probe.py").read_text())
        for role_name in ("coordinator", "developer", "reviewer"): self.assertIn("Controller-sent trigger context", (project / f".agent/roles/{role_name}.md").read_text())
        inherited = json.loads((project / ".agent/controller_config.json").read_text())
        self.assertEqual([role["write_capable"] for role in inherited["roles"]], [False, True, False])
        self.assertIn("coordinator_summary.md", (project / ".agent/roles/coordinator.md").read_text()); self.assertIn("workspace-write", (project / ".agent/roles/reviewer.md").read_text())
        self.assertTrue((project / ".git").is_dir())
        self.assertNotEqual(subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, capture_output=True).returncode, 0)
        self.assertEqual(json.loads((project / ".agent/controller_config.json").read_text())["task_authority"], "docs/NEXT_PROMPT.md")
        self.assertEqual(json.loads((project / ".agent/authority_approvals.json").read_text()), {"approvals": []})
        self.assertIn("No Developer task is currently authorized.", (project / "docs/NEXT_PROMPT.md").read_text())
        self.assertTrue((project / ".agent/runtime/state.json").is_file())
        self.assertFalse((project / ".agent/runtime/current").exists()); self.assertFalse((project / ".agent/runtime/history").exists())

    def test_existing_git_project_preserves_files_and_supports_dry_run_after_baseline(self) -> None:
        project = self.root / "existing"; project.mkdir()
        (project / "AGENTS.md").write_text("keep rules\n"); (project / ".gitignore").write_text("build/\n"); (project / "product.txt").write_text("keep\n")
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        result = self.run_init(project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((project / "AGENTS.md").read_text(), "keep rules\n"); self.assertEqual((project / "product.txt").read_text(), "keep\n")
        self.assertIn("build/", (project / ".gitignore").read_text()); self.assertIn(".agent/runtime/", (project / ".gitignore").read_text())
        subprocess.run(["git", "add", "."], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "baseline"], cwd=project, check=True)
        dry_run = subprocess.run([sys.executable, str(project / ".agent/orchestrate.py"), "--dry-run"], cwd=project, text=True, capture_output=True)
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr); self.assertIn('"task_authority": "docs/NEXT_PROMPT.md"', dry_run.stdout)

    def test_refuses_conflicts_path_escapes_and_non_git_projects(self) -> None:
        project = self.root / "conflict"; project.mkdir(); (project / ".agent/runtime/history").mkdir(parents=True)
        refused = self.run_init(project, "--init-git")
        self.assertNotEqual(refused.returncode, 0); self.assertTrue((project / ".agent/runtime/history").is_dir())
        other = self.root / "other"; other.mkdir()
        escape = subprocess.run([sys.executable, str(self.script), "init", "--project-root", str(other), "--task-authority", "../escape.md", "--init-git"], text=True, capture_output=True)
        self.assertNotEqual(escape.returncode, 0); self.assertFalse((self.root / "escape.md").exists())
        invalid = subprocess.run([sys.executable, str(self.script), "init", "--project-root", str(other), "--task-authority", "docs", "--init-git"], text=True, capture_output=True)
        self.assertNotEqual(invalid.returncode, 0); self.assertFalse((other / ".git").exists())
        defaults = self.root / "defaults"
        default_init = subprocess.run([sys.executable, str(self.script), "init", "--project-root", str(defaults), "--init-git"], text=True, capture_output=True)
        self.assertEqual(default_init.returncode, 0, default_init.stderr); self.assertTrue((defaults / "docs/NEXT_PROMPT.md").is_file())
        nongit = self.root / "nongit"; nongit.mkdir(); (nongit / "file").write_text("keep")
        refused = self.run_init(nongit)
        self.assertNotEqual(refused.returncode, 0); self.assertEqual((nongit / "file").read_text(), "keep")

    def test_idempotent_refusal_has_no_role_or_execution_artifacts(self) -> None:
        project = self.root / "idempotent"; self.assertEqual(self.run_init(project, "--init-git").returncode, 0)
        again = self.run_init(project)
        self.assertNotEqual(again.returncode, 0); self.assertIn("refuses existing controller target", again.stderr)
        self.assertFalse((project / ".agent/runtime/current").exists()); self.assertFalse((project / ".agent/runtime/history").exists())
        self.assertFalse((project / ".agent/runtime/calls").exists())

    def test_symlinked_scaffold_parents_refuse_before_any_write_or_git_initialization(self) -> None:
        for parent in (".agent", "docs"):
            with self.subTest(parent=parent):
                project, external = self.root / parent.replace(".", "dot"), self.root / f"{parent.replace('.', 'dot')}-external"
                project.mkdir(); external.mkdir(); (project / ".gitignore").write_text("keep\n")
                os.symlink(external, project / parent)
                result = self.run_init(project, "--init-git")
                self.assertNotEqual(result.returncode, 0); self.assertIn("symlinked", result.stderr)
                self.assertEqual(list(external.iterdir()), [])
                self.assertFalse((project / ".git").exists()); self.assertFalse((project / ".agent/controller_config.json").exists())
                self.assertEqual((project / ".gitignore").read_text(), "keep\n")

    def test_project_root_symlink_is_resolved_once_and_scaffolds_actual_root(self) -> None:
        actual, alias = self.root / "actual", self.root / "alias"
        actual.mkdir(); os.symlink(actual, alias)
        result = self.run_init(alias, "--init-git")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((actual / ".agent/controller_config.json").is_file())
        self.assertTrue((actual / ".git").is_dir())

    def test_console_entrypoint_uses_target_cwd_for_init_defaults_and_preview(self) -> None:
        project = self.root / "console-project"
        project.mkdir()
        init = subprocess.run([sys.executable, str(ROOT / "orchestr8.py"), "init", "--init-git"], cwd=project, text=True, capture_output=True)
        self.assertEqual(init.returncode, 0, init.stderr)
        preview = subprocess.run([sys.executable, str(ROOT / "orchestr8.py"), "preview"], cwd=project, text=True, capture_output=True)
        self.assertEqual(preview.returncode, 2, preview.stderr); self.assertEqual(json.loads(preview.stdout)["outcome"], "refusal"); self.assertFalse((project / ".agent/runtime/history").exists())

    def test_tabs_cli_help_names_iterm2_and_not_terminal(self) -> None:
        result = subprocess.run([sys.executable, str(self.script), "init", "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("supervised iTerm2 role tabs", result.stdout)
        self.assertNotIn("Terminal role tabs", result.stdout)

    def test_tabs_probe_requires_tabs(self) -> None:
        result = subprocess.run([sys.executable, str(self.script), "init", "--init-git", "--tabs-probe"], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0); self.assertIn("--tabs-probe requires --tabs", result.stderr)
        layout = subprocess.run([sys.executable, str(self.script), "init", "--init-git", "--tabs-layout-probe"], text=True, capture_output=True)
        self.assertNotEqual(layout.returncode, 0); self.assertIn("--tabs-layout-probe requires --tabs", layout.stderr)
        bootstrap = subprocess.run([sys.executable, str(self.script), "init", "--init-git", "--tabs-coordinator-bootstrap-probe"], text=True, capture_output=True)
        self.assertNotEqual(bootstrap.returncode, 0); self.assertIn("--tabs-coordinator-bootstrap-probe requires --tabs", bootstrap.stderr)
        both = subprocess.run([sys.executable, str(self.script), "init", "--init-git", "--tabs", "--tabs-probe", "--tabs-layout-probe"], text=True, capture_output=True)
        self.assertNotEqual(both.returncode, 0); self.assertIn("choose only one", both.stderr)
        mixed = subprocess.run([sys.executable, str(self.script), "init", "--init-git", "--tabs", "--tabs-layout-probe", "--tabs-coordinator-bootstrap-probe"], text=True, capture_output=True)
        self.assertNotEqual(mixed.returncode, 0); self.assertIn("choose only one", mixed.stderr)


if __name__ == "__main__": unittest.main()
