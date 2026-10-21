#!/usr/bin/env python3
"""Fail-closed, project-configured Coordinator → Developer → Reviewer controller."""
from __future__ import annotations

import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".agent" / "controller_config.json"
HUMAN_STOP_CATEGORIES = ("unresolved_requirement", "material_policy_or_provider_decision", "scope_expansion", "failed_or_incomplete_validation", "unsafe_or_unexpected_diff", "remote_or_external_action", "stale_or_mismatched_task_state", "indeterminate_write_invocation")


class RoleFailure(RuntimeError):
    pass


def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def read(path: Path) -> str: return path.read_text(encoding="utf-8") if path.is_file() else "(none)"
def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def excluded(name: str) -> bool:
    path = Path(name); return "secrets" in path.parts or path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example") or path.suffix == ".key"
def project_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if root.resolve() not in path.parents and path != root.resolve(): raise RuntimeError("configured path escapes project root")
    return path


def load_config(path: Path | None = None) -> tuple[dict, Path]:
    path = path or CONFIG_PATH; raw = path.read_bytes(); config = json.loads(raw)
    required = {"task_authority", "approval_record", "paths", "roles", "role_timeout_seconds"}
    if not isinstance(config, dict) or not required <= set(config): raise RuntimeError("configuration is malformed")
    roles = config["roles"]
    # C1 intentionally supports exactly these semantic roles, with all project assets configurable.
    if not isinstance(roles, list) or [item.get("name") for item in roles] != ["coordinator", "developer", "reviewer"]: raise RuntimeError("C1 supports only coordinator, developer, reviewer role order")
    for item in roles:
        if not all(isinstance(item.get(key), str) and item[key] for key in ("name", "instruction", "schema")) or not isinstance(item.get("command"), list) or not isinstance(item.get("write_capable"), bool): raise RuntimeError("configuration role is malformed")
        if item["write_capable"] != (item["name"] == "developer"): raise RuntimeError("only Developer may be write-capable")
    if not all(isinstance(config["paths"].get(key), str) and config["paths"][key] for key in ("current", "history", "state")): raise RuntimeError("configuration paths are malformed")
    config["_sha256"] = digest(raw); return config, path.parent.parent.resolve()


def locations(root: Path, config: dict) -> tuple[Path, Path, Path, Path, Path]:
    paths = config["paths"]
    return (project_path(root, config["task_authority"]), project_path(root, config["approval_record"]), project_path(root, paths["current"]), project_path(root, paths["history"]), project_path(root, paths["state"]))
def role(config: dict, name: str) -> dict: return next(item for item in config["roles"] if item["name"] == name)
def runtime_root(current: Path, history: Path, state_path: Path) -> Path:
    return Path(os.path.commonpath([current, history, state_path])).resolve()
def manifest(root: Path, runtime: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): digest(path.read_bytes()) for path in sorted(root.rglob("*")) if path.is_file() and runtime not in path.parents and path != runtime and "__pycache__" not in path.parts and not excluded(str(path.relative_to(root)))}
def sanitize_manifest(path: Path) -> None:
    if not path.is_file(): return
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict): raise RuntimeError(f"malformed manifest: {path}")
    clean = {key: value for key, value in data.items() if not excluded(key)}
    if clean != data: write_json(path, clean)
def sanitize_existing(current: Path, history: Path) -> None:
    for path in [current / "baseline.json", current / "after_developer.json", *history.glob("*/baseline.json"), *history.glob("*/after_developer.json")]: sanitize_manifest(path)


def schema_type(value: object, declared: object) -> bool:
    types = declared if isinstance(declared, list) else [declared]
    return any((kind == "null" and value is None) or (kind == "string" and isinstance(value, str)) or (kind == "array" and isinstance(value, list)) or (kind == "object" and isinstance(value, dict)) or (kind == "boolean" and isinstance(value, bool)) for kind in types)
def validate_output(root: Path, config: dict, name: str, value: object) -> dict:
    try: schema = json.loads(project_path(root, role(config, name)["schema"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise RoleFailure(f"unreadable {name} output schema") from error
    if not isinstance(value, dict) or not isinstance(schema, dict): raise RoleFailure(f"malformed {name} output contract")
    properties, required = schema.get("properties"), schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list) or any(key not in value for key in required): raise RoleFailure(f"malformed {name} output contract")
    if schema.get("additionalProperties") is False and set(value) - set(properties): raise RoleFailure(f"malformed {name} output contract")
    for key, definition in properties.items():
        if key not in value or not isinstance(definition, dict): continue
        item = value[key]
        if "type" in definition and not schema_type(item, definition["type"]): raise RoleFailure(f"malformed {name} output contract")
        if "enum" in definition and item not in definition["enum"]: raise RoleFailure(f"malformed {name} output contract")
        if definition.get("type") == "array" and isinstance(item, list):
            items = definition.get("items", {})
            if isinstance(items, dict) and "type" in items and any(not schema_type(entry, items["type"]) for entry in item): raise RoleFailure(f"malformed {name} output contract")
    return value


def run_role(root: Path, current: Path, config: dict, name: str, prompt: str) -> dict:
    spec = role(config, name); output = current / f".{name}.json"; output.unlink(missing_ok=True)
    cmd = spec["command"] + ["-C", str(root), "--skip-git-repo-check", "-s", "workspace-write" if spec.get("write_capable") else "read-only", "--output-schema", str(project_path(root, spec["schema"])), "-o", str(output), prompt]
    try: result = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=config["role_timeout_seconds"])
    except subprocess.TimeoutExpired as error: raise RoleFailure(f"{name} timed out after {config['role_timeout_seconds']} seconds") from error
    if result.returncode: raise RoleFailure(f"{name} exited {result.returncode}: {result.stderr[-500:]}")
    if not output.is_file(): raise RoleFailure(f"{name} completed without output")
    try: return validate_output(root, config, name, json.loads(output.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error: raise RoleFailure(f"malformed {name} JSON output") from error


def acquire_lock(agent: Path) -> Path:
    lock = agent / "orchestrate.lock"
    try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error: raise RuntimeError(f"controller lock exists: {lock}; remove only after verifying it is stale") from error
    os.write(fd, str(os.getpid()).encode()); os.close(fd); return lock
def archive(current: Path, history: Path, iteration: int, state: dict) -> None:
    target = history / f"{iteration:03d}"
    if target.exists() and any(target.iterdir()): raise RuntimeError(f"iteration {iteration} is already archived; refusing to overwrite history")
    target.mkdir(parents=True, exist_ok=True)
    for name in ("authoritative_task.md", "task_snapshot.json", "approval_evidence.json", "dev_report.md", "review_report.md", "baseline.json", "after_developer.json", "human_stop.json"):
        if (current / name).is_file(): shutil.copy2(current / name, target / name)
    write_json(target / "state.json", state)
def finish(current: Path, history: Path, state_path: Path, iteration: int, state: dict, status: str, reason: str | None = None) -> int:
    state.update(iteration=iteration, status=status, stopped_reason=reason); state.pop("phase", None); state.pop("active_iteration", None); archive(current, history, iteration, state); write_json(state_path, state); return 0
def human_stop(current: Path, history: Path, state_path: Path, iteration: int, state: dict, category: str, reason: str) -> int:
    if category not in HUMAN_STOP_CATEGORIES: raise RuntimeError(f"unknown human-stop category: {category}")
    write_json(current / "human_stop.json", {"category": category, "reason": reason, "state": "HUMAN_REQUIRED", "phase": state.get("phase"), "task_snapshot_sha256": state.get("task_snapshot_sha256")})
    return finish(current, history, state_path, iteration, state, "HUMAN_REQUIRED", f"{category}: {reason}")


def approval_entries(record: Path) -> list[dict]:
    if not record.is_file(): raise RuntimeError("configured approval record is missing")
    try: data = json.loads(record.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error: raise RuntimeError("configured approval record is malformed") from error
    entries = data.get("approvals") if isinstance(data, dict) else None
    if not isinstance(entries, list): raise RuntimeError("configured approval record lacks approvals")
    if not all(isinstance(item, dict) for item in entries): raise RuntimeError("configured approval record is malformed")
    return entries
def approval(root: Path, record: Path, old_hash: str, new_hash: str, current: Path) -> None:
    entries = approval_entries(record)
    matched = next((item for item in entries if isinstance(item, dict) and item.get("prior_authority_sha256") == old_hash and item.get("new_authority_sha256") == new_hash and isinstance(item.get("approved_at"), str) and item["approved_at"]), None)
    if matched is None: raise RuntimeError("authority change lacks matching explicit approval")
    write_json(current / "approval_evidence.json", {"record": str(record.relative_to(root)), "approval": matched})


def snapshot_authority(root: Path, authority: Path, approval_record: Path, current: Path, config: dict, state: dict) -> dict:
    if not authority.is_file(): raise RuntimeError("configured durable task authority is missing")
    data = authority.read_bytes(); new_hash = digest(data); old_hash = state.get("last_authority_sha256")
    if old_hash and old_hash != new_hash: approval(root, approval_record, old_hash, new_hash, current)
    meta = {"source": str(authority.relative_to(root)), "sha256": new_hash, "bytes": len(data), "config_sha256": config["_sha256"]}
    (current / "authoritative_task.md").write_bytes(data); write_json(current / "task_snapshot.json", meta); return meta
def validate_snapshot(root: Path, authority: Path, current: Path, config: dict, state: dict) -> str:
    task, meta = current / "authoritative_task.md", current / "task_snapshot.json"
    if not task.is_file() or not meta.is_file(): raise RuntimeError("missing task snapshot")
    data = task.read_bytes(); expected = {"source": str(authority.relative_to(root)), "sha256": digest(data), "bytes": len(data), "config_sha256": config["_sha256"]}
    if json.loads(meta.read_text()) != expected or state.get("task_snapshot_sha256") != expected["sha256"] or authority.read_bytes() != data: raise RuntimeError("stale or mismatched task snapshot")
    return data.decode("utf-8")
def clean_baseline(root: Path, runtime: Path) -> tuple[str, dict[str, str]]:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True)
    if status.returncode: raise RuntimeError("developer dispatch requires a clean Git baseline")
    runtime_name = str(runtime.relative_to(root))
    changes = [line for line in status.stdout.splitlines() if not (len(line) >= 4 and (line[3:] == runtime_name or line[3:].startswith(runtime_name + "/")))]
    if changes: raise RuntimeError("developer dispatch requires a clean Git baseline")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True)
    if head.returncode: raise RuntimeError("developer dispatch requires a Git HEAD")
    return head.stdout.strip(), manifest(root, runtime)
def report(title: str, value: dict) -> str: return f"# {title}\n\n```json\n{json.dumps(value, indent=2, sort_keys=True)}\n```\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--multi-cycle", action="store_true"); parser.add_argument("--max-iterations", type=int); parser.add_argument("--resume", action="store_true"); parser.add_argument("--dry-run", action="store_true"); args = parser.parse_args()
    if args.max_iterations is not None and not args.multi_cycle: parser.error("--max-iterations requires --multi-cycle")
    config, root = load_config(); authority, approval_record, current, history, state_path = locations(root, config); approval_entries(approval_record); state = json.loads(state_path.read_text())
    if state.get("config_sha256") not in (None, config["_sha256"]): raise RuntimeError("saved state belongs to a different controller configuration")
    maximum = args.max_iterations if args.multi_cycle and args.max_iterations is not None else (state.get("max_iterations", 1) if args.multi_cycle else 1)
    if args.dry_run: print(json.dumps({"root": str(root), "task_authority": str(authority.relative_to(root)), "roles": [item["name"] for item in config["roles"]], "max_iterations": maximum}, indent=2)); return 0
    if state.get("phase") and not args.resume: raise RuntimeError("use --resume for the saved active phase")
    lock = acquire_lock(state_path.parent)
    try:
        resumed = state.get("phase") if args.resume else None; completed = 0; runtime = runtime_root(current, history, state_path)
        while completed < maximum:
            if not state.get("phase"):
                iteration = state.get("iteration", 0) + 1; legacy = current / "next_prompt.md"
                if legacy.is_file() and legacy.read_bytes() != authority.read_bytes():
                    state.update(active_iteration=iteration, phase="coordinator", config_sha256=config["_sha256"]); return human_stop(current, history, state_path, iteration, state, "stale_or_mismatched_task_state", "existing current task differs from durable authority")
                try: head, base = clean_baseline(root, runtime)
                except RuntimeError as error:
                    state.update(active_iteration=iteration, phase="coordinator", config_sha256=config["_sha256"])
                    return human_stop(current, history, state_path, iteration, state, "unsafe_or_unexpected_diff", str(error))
                sanitize_existing(current, history)
                current.mkdir(parents=True, exist_ok=True)
                state.update(active_iteration=iteration, phase="coordinator", status="RUNNING", config_sha256=config["_sha256"])
                for name in (".coordinator.json", ".developer.json", ".reviewer.json", "authoritative_task.md", "task_snapshot.json", "approval_evidence.json", "dev_report.md", "review_report.md", "baseline.json", "after_developer.json", "human_stop.json"): (current / name).unlink(missing_ok=True)
                state["baseline"] = {"head": head, "manifest": base}; write_json(state_path, state)
            iteration, phase = state["active_iteration"], state["phase"]
            try:
                if phase == "coordinator":
                    output = current / ".coordinator.json"; prompt = read(project_path(root, role(config, "coordinator")["instruction"])) + "\nOwner input:\n" + read(current / "human_input.md")
                    if output.is_file():
                        try: result = validate_output(root, config, "coordinator", json.loads(output.read_text()))
                        except json.JSONDecodeError as error: raise RoleFailure("malformed saved coordinator checkpoint") from error
                    else: result = run_role(root, current, config, "coordinator", prompt)
                    if result["status"] != "CONTINUE": return human_stop(current, history, state_path, iteration, state, result["human_category"] or "unresolved_requirement", result.get("human_reason") or result["summary"])
                    if result["next_prompt"] not in (None, "") and result["next_prompt"] != authority.read_text(): return human_stop(current, history, state_path, iteration, state, "unresolved_requirement", "coordinator proposal is non-authoritative")
                    meta = snapshot_authority(root, authority, approval_record, current, config, state); state.update(phase="developer", task_snapshot_sha256=meta["sha256"]); write_json(current / "baseline.json", state.pop("baseline")); write_json(state_path, state)
                elif phase == "developer":
                    task = validate_snapshot(root, authority, current, config, state); output = current / ".developer.json"
                    if output.is_file():
                        try: result = validate_output(root, config, "developer", json.loads(output.read_text()))
                        except json.JSONDecodeError as error: raise RoleFailure("malformed saved Developer checkpoint") from error
                    elif resumed == "developer": return human_stop(current, history, state_path, iteration, state, "indeterminate_write_invocation", "Developer checkpoint is absent; refusing duplicate invocation")
                    else: result = run_role(root, current, config, "developer", read(project_path(root, role(config, "developer")["instruction"])) + "\nImmutable task snapshot:\n" + task)
                    (current / "dev_report.md").write_text(report("Developer report", result)); write_json(current / "after_developer.json", manifest(root, runtime))
                    if result["status"] != "DONE": return human_stop(current, history, state_path, iteration, state, result["human_category"] or "failed_or_incomplete_validation", result["summary"])
                    state["phase"] = "reviewer"; write_json(state_path, state)
                elif phase == "reviewer":
                    task = validate_snapshot(root, authority, current, config, state); output = current / ".reviewer.json"; prompt = read(project_path(root, role(config, "reviewer")["instruction"])) + "\nImmutable task snapshot:\n" + task + "\nDeveloper report:\n" + read(current / "dev_report.md")
                    if output.is_file():
                        try: result = validate_output(root, config, "reviewer", json.loads(output.read_text()))
                        except json.JSONDecodeError as error: raise RoleFailure("malformed saved reviewer checkpoint") from error
                    else: result = run_role(root, current, config, "reviewer", prompt)
                    (current / "review_report.md").write_text(report("Reviewer report", result))
                    if result["verdict"] != "APPROVED": return human_stop(current, history, state_path, iteration, state, result["human_category"] or "failed_or_incomplete_validation", result.get("human_reason") or result["summary"])
                    state["last_authority_sha256"] = state["task_snapshot_sha256"]; finish(current, history, state_path, iteration, state, "READY"); completed += 1
                    if not args.multi_cycle: return 0
                else: return human_stop(current, history, state_path, iteration, state, "stale_or_mismatched_task_state", "unknown saved phase")
            except RoleFailure as error:
                category = "indeterminate_write_invocation" if phase == "developer" else "failed_or_incomplete_validation"
                return human_stop(current, history, state_path, iteration, state, category, str(error))
            except (RuntimeError, json.JSONDecodeError) as error:
                category = "unsafe_or_unexpected_diff" if "baseline" in str(error) or "Git" in str(error) else "stale_or_mismatched_task_state"
                return human_stop(current, history, state_path, iteration, state, category, str(error))
        return 0
    finally: lock.unlink(missing_ok=True)


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (RuntimeError, OSError, json.JSONDecodeError) as error: print(f"orchestration stopped: {error}", file=sys.stderr); raise SystemExit(2)
