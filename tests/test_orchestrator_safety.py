from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
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
            roles.append({"name": name, "instruction": f"assets/{name}.md", "command": [sys.executable, str(self.fake)], "schema": f"contracts/{name}.json", "write_capable": writable})
        self.write_json(self.agent / "controller.json", {"task_authority": "tasks/authority.md", "approval_record": "approvals.json", "paths": paths, "role_timeout_seconds": timeout, "roles": roles})
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
        missing = subprocess.run([sys.executable, str(self.script), "init", "--project-root", str(other), "--init-git"], text=True, capture_output=True)
        self.assertNotEqual(missing.returncode, 0); self.assertIn("--task-authority", missing.stderr)
        invalid = subprocess.run([sys.executable, str(self.script), "init", "--project-root", str(other), "--task-authority", "docs", "--init-git"], text=True, capture_output=True)
        self.assertNotEqual(invalid.returncode, 0); self.assertFalse((other / ".git").exists())
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


if __name__ == "__main__": unittest.main()
