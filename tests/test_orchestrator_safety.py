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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("orchestrator", ROOT / ".agent" / "orchestrate.py")
assert SPEC and SPEC.loader
ORCHESTRATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORCHESTRATOR)


class OrchestratorSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve(); self.agent = self.root / ".runtime"
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
            "base={'human_category':None}; p={'coordinator':dict(base,status='CONTINUE',summary='go',next_prompt=None,human_reason=None),'developer':dict(base,status='DONE',summary='done',files_changed=[],validation=[],known_issues=[],commit_or_diff_reference=None),'reviewer':dict(base,verdict='APPROVED',summary='ok',findings=[],evidence=[],human_reason=None)}\n"
            "if mode==role+'-extra': p[role]['unexpected']='nope'\n"
            "out.write_text(json.dumps(p[role]))\n"
        )
        self.write_config(); ORCHESTRATOR.CONFIG_PATH = self.agent / "controller.json"; ORCHESTRATOR.clean_baseline = lambda root, history: ("test-head", {})

    def tearDown(self) -> None:
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

    def state(self) -> dict:
        return json.loads(self.locations()[2][4].read_text())

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
        self.write_json(state_path, {"iteration": 0, "active_iteration": 1, "phase": "developer", "config_sha256": config["_sha256"], "task_snapshot_sha256": meta["sha256"]})
        self.run_controller("--resume"); self.assert_stop("indeterminate_write_invocation"); self.assertFalse((current / "calls").exists())

    def test_developer_and_reviewer_resume_paths(self) -> None:
        config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        self.write_json(current / ".developer.json", {"status":"DONE","summary":"done","files_changed":[],"validation":[],"known_issues":[],"commit_or_diff_reference":None,"human_category":None})
        self.write_json(state_path, {"iteration":0,"active_iteration":1,"phase":"developer","config_sha256":config["_sha256"],"task_snapshot_sha256":meta["sha256"]})
        self.run_controller("--resume"); self.assertEqual(self.state()["status"], "READY")
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        self.write_json(current / ".reviewer.json", {"verdict":"APPROVED","summary":"ok","findings":[],"evidence":[],"human_reason":None,"human_category":None})
        self.write_json(state_path, {"iteration":0,"active_iteration":1,"phase":"reviewer","config_sha256":config["_sha256"],"task_snapshot_sha256":meta["sha256"]})
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
        self.write_json(state_path, {"iteration":0,"active_iteration":1,"phase":"coordinator","config_sha256":config["_sha256"]})
        self.run_controller("--resume"); self.assert_stop("failed_or_incomplete_validation")
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
        meta = ORCHESTRATOR.snapshot_authority(root, authority, approval, current, config, {})
        self.write_json(state_path, {"iteration":0,"active_iteration":1,"phase":"reviewer","config_sha256":config["_sha256"],"task_snapshot_sha256":meta["sha256"]})
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
        self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"go","next_prompt":None,"human_reason":None,"human_category":None})
        ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator")
        session = json.loads((current / "supervised_session.json").read_text()); self.assertEqual(session["phase"], "developer")
        self.write_json(current / ".developer.json", {"status":"DONE","summary":"done","files_changed":[],"validation":[],"known_issues":[],"commit_or_diff_reference":None,"human_category":None})
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
        def run(fake_iterm, request='{ "title": "ORCHESTR8 · Host probe" }'):
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
        output = io.StringIO(); builtins.__import__ = missing_iterm2; sys.stdin = io.StringIO('{"title":"ORCHESTR8 · Host probe"}')
        try:
            with contextlib.redirect_stdout(output): exec(compile(bridge.read_text(), str(bridge), "exec"), {"__name__":"__main__"})
        finally:
            builtins.__import__ = original_import; sys.stdin = original_stdin
        self.assertIn("module unavailable", json.loads(output.getvalue())["reason"])

    def test_role_contracts_are_isolated_and_have_non_overlapping_outputs(self) -> None:
        instructions = {name: (ROOT / ".agent" / "roles" / f"{name}.md").read_text() for name in ("coordinator", "developer", "reviewer")}
        outputs = {name: f".agent/runtime/current/.{name}.json" for name in instructions}
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
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0)
        self.assert_stop("failed_or_incomplete_validation")
        self.tearDown(); self.setUp(); config, root, (authority, approval, current, history, state_path) = self.locations(); ORCHESTRATOR.clean_baseline = self.old_clean
        subprocess.run(["git", "init", "-q"], cwd=root, check=True); subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "base"], cwd=root, check=True); subprocess.run(["git", "update-ref", "-d", "HEAD"], cwd=root, check=True)
        ORCHESTRATOR.supervised_init(root, config, current, True, lambda _: None); self.write_json(current / ".coordinator.json", {"status":"CONTINUE","summary":"go","next_prompt":None,"human_reason":None,"human_category":None})
        self.assertEqual(ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "coordinator"), 0); self.assert_stop("failed_or_incomplete_validation")

    def test_supervised_cycle_refuses_invalid_artifact_preconditions(self) -> None:
        config, root, (authority, _, current, history, state_path) = self.locations(); ORCHESTRATOR.supervised_init(root, config, current, True, lambda _: None)
        self.write_json(session_path := current / "supervised_session.json", {"phase":"reviewer", "state":"WAITING_FOR_HUMAN", "task_snapshot_sha256":"missing"})
        self.assertEqual(ORCHESTRATOR.supervised_cycle(root, config, authority, current, history, state_path), 0)
        self.assert_stop("stale_or_mismatched_task_state")

    def test_supervised_session_malformed_states_stop_for_accept_cycle_and_views(self) -> None:
        cases = (("accept", ["developer"]), ("cycle", {"phase": None}), ("status", {"phase": "unknown"}), ("preview", {"phase": ["reviewer"]}), ("resume", "{bad"))
        for command, payload in cases:
            with self.subTest(command=command):
                config, root, (authority, approval, current, history, state_path) = self.locations(); current.mkdir(parents=True)
                if isinstance(payload, str): (current / "supervised_session.json").write_text(payload)
                else: self.write_json(current / "supervised_session.json", payload)
                if command == "accept": result = ORCHESTRATOR.supervised_accept(root, config, authority, approval, current, history, state_path, "developer")
                elif command == "cycle": result = ORCHESTRATOR.supervised_cycle(root, config, authority, current, history, state_path)
                else: result = ORCHESTRATOR.supervised_view(root, config, current, history, state_path, command)
                self.assertEqual(result, 0); self.assert_stop("stale_or_mismatched_task_state")
                archived = history / "001" / "supervised_session.json"; self.assertTrue(archived.is_file()); self.assertFalse((current / "calls").exists())
                self.tearDown(); self.setUp()
        config, root, (_, _, current, history, state_path) = self.locations()
        self.assertEqual(ORCHESTRATOR.supervised_view(root, config, current, history, state_path, "status"), 0)
        self.assert_stop("stale_or_mismatched_task_state")

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

    def test_new_project_requires_explicit_git_and_has_no_head(self) -> None:
        project = self.root / "new"
        refused = self.run_init(project)
        self.assertNotEqual(refused.returncode, 0); self.assertFalse(project.exists())
        result = self.run_init(project, "--init-git")
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn("create an initial Git commit/HEAD", result.stdout)
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
        self.assertEqual(preview.returncode, 0, preview.stderr); self.assertTrue((project / ".agent/runtime/history/001/human_stop.json").is_file())

    def test_tabs_cli_help_names_iterm2_and_not_terminal(self) -> None:
        result = subprocess.run([sys.executable, str(self.script), "init", "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("supervised iTerm2 role tabs", result.stdout)
        self.assertNotIn("Terminal role tabs", result.stdout)

    def test_tabs_probe_requires_tabs(self) -> None:
        result = subprocess.run([sys.executable, str(self.script), "init", "--init-git", "--tabs-probe"], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0); self.assertIn("--tabs-probe requires --tabs", result.stderr)


if __name__ == "__main__": unittest.main()
