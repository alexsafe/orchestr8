#!/usr/bin/env python3
"""Fail-closed, project-configured Coordinator → Developer → Reviewer controller."""
from __future__ import annotations

import argparse, hashlib, json, os, re, shlex, shutil, stat, subprocess, sys, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".agent" / "controller_config.json"
INIT_ASSETS = (
    ".agent/orchestrate.py", ".agent/iterm_probe.py", ".agent/workflow_policy.json", ".agent/roles/coordinator.md", ".agent/roles/developer.md",
    ".agent/roles/reviewer.md", ".agent/schemas/coordinator.json", ".agent/schemas/developer.json",
    ".agent/schemas/reviewer.json", "docs/controller/README.md", "docs/controller/SUBMISSION_SMOKE.md",
)
INIT_CONFIG = {
    "tab_host": "iterm2",
    "approval_record": ".agent/authority_approvals.json",
    "paths": {"current": ".agent/runtime/current", "history": ".agent/runtime/history", "state": ".agent/runtime/state.json"},
    "role_timeout_seconds": 900,
    "roles": [
        {"name": "coordinator", "instruction": ".agent/roles/coordinator.md", "command": ["codex", "exec"], "session_command": ["codex"], "schema": ".agent/schemas/coordinator.json", "write_capable": False},
        {"name": "developer", "instruction": ".agent/roles/developer.md", "command": ["codex", "exec"], "session_command": ["codex"], "schema": ".agent/schemas/developer.json", "write_capable": True},
        {"name": "reviewer", "instruction": ".agent/roles/reviewer.md", "command": ["codex", "exec"], "session_command": ["codex"], "schema": ".agent/schemas/reviewer.json", "write_capable": False},
    ],
}
NEUTRAL_AUTHORITY = "# Current Task Authority\n\nNo Developer task is currently authorized.\n\nBefore running a write-capable cycle, replace this document through the project's explicit approval process with one bounded task, acceptance criteria, validation commands, and stop conditions.\n"
RUNTIME_IGNORES = (".agent/runtime/", ".agent/orchestrate.lock")
HUMAN_STOP_CATEGORIES = ("unresolved_requirement", "material_policy_or_provider_decision", "scope_expansion", "failed_or_incomplete_validation", "unsafe_or_unexpected_diff", "remote_or_external_action", "stale_or_mismatched_task_state", "indeterminate_write_invocation")
ROLE_ALIASES = {"coordinator": "coordinator", "coord": "coordinator", "developer": "developer", "dev": "developer", "reviewer": "reviewer", "review": "reviewer"}
ROLE_ORDER = ("coordinator", "developer", "reviewer")
ROLE_PHRASES = {"coordinator_initial": "Start project: <human initial brief>", "developer": "do next prompt", "reviewer": "review latest", "coordinator_review": "coordinate latest"}
INITIAL_LABELS = {"coordinator":"waiting for Start project…", "developer":"waiting for do next prompt", "reviewer":"waiting for review latest"}
SUPERVISED_PHASES = frozenset(ROLE_PHRASES)


class RoleFailure(RuntimeError):
    pass


def parse_roles(value: str) -> list[str]:
    names = [ROLE_ALIASES.get(item.strip().lower()) for item in value.split(",")]
    if len(names) != 3 or any(name is None for name in names) or len(set(names)) != 3 or names != list(ROLE_ORDER):
        raise RuntimeError("--roles must be coordinator,developer,reviewer in that order (aliases: coord,dev,review)")
    return names


def tab_spec(root: Path, config: dict, name: str, production: bool = False) -> dict:
    spec = role(config, name); instruction = str(project_path(root, spec["instruction"])); sandbox = "workspace-write" if production or spec["write_capable"] else "read-only"
    command = spec.get("session_command")
    if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
        raise RuntimeError(f"{name} lacks a configured interactive session command")
    guidance = decision_guidance(json.loads(read_regular_evidence(root / ".agent" / "workflow_policy.json")))
    return {"host": config["tab_host"], "role": name, "title": f"ORCHESTR8 · {name.title()} · {INITIAL_LABELS[name]}", "cwd": str(root), "instruction": instruction, "command": command, "sandbox": sandbox, "policy_guidance":guidance, "bootstrap": f"Read {instruction}; policy decisions: {guidance}; wait for the documented human phrase; use {sandbox}."}


def applescript_text(value: str) -> str:
    """Return a Unicode-safe AppleScript text expression without JSON escapes."""
    parts: list[str] = []; literal: list[str] = []
    def flush() -> None:
        if literal:
            parts.append('"' + "".join(literal) + '"'); literal.clear()
    for char in value:
        if char == '"': literal.append('\\"')
        elif char == "\\": literal.append("\\\\")
        elif ord(char) < 32 or ord(char) == 127:
            flush(); parts.append(f"character id {ord(char)}")
        else: literal.append(char)
    flush()
    return '""' if not parts else parts[0] if len(parts) == 1 else "(" + " & ".join(parts) + ")"


def interactive_session_command(spec: dict) -> str:
    if spec.get("probe"):
        return f"cd {shlex.quote(spec['cwd'])}; printf '\\033]0;%s\\007' {shlex.quote(spec['title'])}; printf 'ORCHESTR8 Host probe\\n'; date; printf 'cwd: '; pwd; printf 'shell: %s\\n' \"${{SHELL:-unknown}}\"; \"${{SHELL:-/bin/zsh}}\" --version 2>/dev/null | head -1; printf 'PATH: %s\\n' \"$PATH\"; if command -v codex; then codex --version; printf 'codex --version status: %s\\n' \"$?\"; else printf 'codex: not found\\n'; fi; printf 'No role or workflow was started.\\n'; exec \"${{SHELL:-/bin/zsh}}\" -l"
    launch = f"{shlex.join(spec['command'])} -C {shlex.quote(spec['cwd'])} -s {shlex.quote(spec['sandbox'])} \"$(cat {shlex.quote(spec['instruction'])})\""
    if spec.get("handoff"): launch += shlex.quote("\n" + spec["handoff"])
    return f"cd {shlex.quote(spec['cwd'])}; printf '\\033]0;%s\\007' {shlex.quote(spec['title'])}; {launch}; launch_status=$?; printf '\\nORCHESTR8 role session exited (status %s); inspection shell remains open.\\n' \"$launch_status\" >&2; exec \"${{SHELL:-/bin/zsh}}\" -l"


def iterm_tab_applescript(spec: dict) -> str:
    command = interactive_session_command(spec)
    return "\n".join((
        'tell application "iTerm2"',
        "  if (count of windows) is 0 then error \"iTerm2 has no control window\"",
        "  set targetWindow to front window",
        "  tell targetWindow",
        "    set readinessStartedAt to current date",
        "    set tabCountBefore to count of tabs",
        f"    create tab with default profile command {applescript_text(command)}",
        "    set readinessAttempts to 0",
        "    repeat 10 times",
        "      set readinessAttempts to readinessAttempts + 1",
        "      if (count of tabs) is (tabCountBefore + 1) then exit repeat",
        "      delay 0.1",
        "    end repeat",
        "    set tabCountAfter to count of tabs",
        "    set readinessElapsedSeconds to ((current date) - readinessStartedAt)",
        "    if tabCountAfter is not (tabCountBefore + 1) then error \"iTerm2 tab readiness failed pre_count=\" & tabCountBefore & \" final_count=\" & tabCountAfter & \" attempts=\" & readinessAttempts & \" elapsed_seconds=\" & readinessElapsedSeconds & \" reason=unexpected_count; no supervised state, close partial probe tabs, use a fresh target\"",
        "  end tell",
        "  return \"pre_count=\" & tabCountBefore & \" final_count=\" & tabCountAfter & \" attempts=\" & readinessAttempts & \" elapsed_seconds=\" & readinessElapsedSeconds & \" reason=confirmed\"",
        "end tell",
    ))


def launch_iterm_tab(spec: dict, osascript_runner=subprocess.run, platform: str | None = None) -> None:
    if spec.get("host") != "iterm2": raise RuntimeError("unsupported automatic tab host; configure tab_host as iterm2")
    if (sys.platform if platform is None else platform) != "darwin": raise RuntimeError("--tabs requires iTerm2 on macOS")
    script = iterm_tab_applescript(spec)
    result = osascript_runner(["osascript", "-e", script], text=True, capture_output=True)
    if result.returncode: raise RuntimeError("iTerm2 tab launch failed before supervised state creation; install/open iTerm2 and rerun from an iTerm2 control tab: " + result.stderr.strip())
    return result.stdout.strip()


def launch_iterm_probe(spec: dict, runner=subprocess.run) -> dict:
    request = {"title": spec["title"], "mode": "default_profile_tab_only"}
    result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True)
    if result.returncode: raise RuntimeError("native iTerm2 probe failed before supervised state; create an isolated .venv and authorize iTerm2 Python API: " + result.stderr.strip())
    try: response = json.loads(result.stdout)
    except json.JSONDecodeError as error: raise RuntimeError("native iTerm2 probe returned malformed diagnostics") from error
    if not isinstance(response, dict) or response.get("ok") is not True: raise RuntimeError(str(response.get("reason", "native iTerm2 probe failed; close partial tab and use a fresh target")))
    return response


def launch_iterm_layout_probe(spec: dict, runner=subprocess.run) -> dict:
    request = {"mode": "layout_default_profile_tabs", "titles": ["ORCHESTR8 · Coordinator", "ORCHESTR8 · Developer", "ORCHESTR8 · Reviewer"]}
    result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True)
    if result.returncode: raise RuntimeError("native iTerm2 layout probe failed before supervised state; create an isolated .venv and authorize iTerm2 Python API: " + result.stderr.strip())
    try: response = json.loads(result.stdout)
    except json.JSONDecodeError as error: raise RuntimeError("native iTerm2 layout probe returned malformed diagnostics") from error
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(str(response.get("reason", "native iTerm2 layout probe failed; close partial tabs and use a fresh target")) if isinstance(response, dict) else "native iTerm2 layout probe returned invalid diagnostics")
    tabs = response.get("tabs")
    if not isinstance(response.get("window"), str) or not response["window"] or not isinstance(tabs, list) or len(tabs) != 3 or len(set(tabs)) != 3 or not all(isinstance(tab, str) and tab for tab in tabs) or not isinstance(response.get("elapsed_seconds"), (int, float)) or response.get("result") != "confirmed":
        raise RuntimeError("native iTerm2 layout probe returned incomplete confirmation; close partial tabs and use a fresh target")
    return response


def launch_iterm_coordinator_bootstrap_probe(spec: dict, runner=subprocess.run) -> dict:
    request = {"mode": "coordinator_bootstrap", "cwd": spec["cwd"]}
    result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True)
    if result.returncode: raise RuntimeError("native Coordinator bootstrap probe failed before supervised state; create an isolated .venv and authorize iTerm2 Python API: " + result.stderr.strip())
    try: response = json.loads(result.stdout)
    except json.JSONDecodeError as error: raise RuntimeError("native Coordinator bootstrap probe returned malformed diagnostics") from error
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(str(response.get("reason", "native Coordinator bootstrap probe failed; close partial tabs and use a fresh target")) if isinstance(response, dict) else "native Coordinator bootstrap probe returned invalid diagnostics")
    identifiers = ("window", "tab", "session")
    if not all(isinstance(response.get(key), str) and response[key] for key in identifiers) or not isinstance(response.get("elapsed_seconds"), (int, float)) or response.get("result") != "unverified_bootstrap_delivered":
        raise RuntimeError("native Coordinator bootstrap probe returned incomplete delivery diagnostics; close partial tabs and use a fresh target")
    return response


def launch_iterm_coordinator_start(spec: dict, runner=subprocess.run) -> dict:
    request = {"mode": "coordinator_start", "cwd": spec["cwd"], "instruction": spec["instruction"], "current": spec["current"], "authority": spec["authority"], "command":spec["command"], "policy_guidance":spec.get("policy_guidance", "")}
    result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True)
    if result.returncode: raise RuntimeError("native Coordinator start failed before supervised state; create an isolated .venv and authorize iTerm2 Python API: " + result.stderr.strip())
    try: response = json.loads(result.stdout)
    except json.JSONDecodeError as error: raise RuntimeError("native Coordinator start returned malformed diagnostics") from error
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(str(response.get("reason", "native Coordinator start failed; close partial tabs and use a fresh target")) if isinstance(response, dict) else "native Coordinator start returned invalid diagnostics")
    identifiers = ("window", "tab", "session")
    if not all(isinstance(response.get(key), str) and response[key] for key in identifiers) or not isinstance(response.get("elapsed_seconds"), (int, float)) or response.get("result") != "coordinator_delivery_confirmed":
        raise RuntimeError("native Coordinator start returned incomplete delivery diagnostics; close partial tabs and use a fresh target")
    return response



def launch_iterm_staged_role(spec: dict, runner=subprocess.run) -> dict:
    request = {"mode":"staged_role_start", "window":spec["window"], "title":spec["title"], "command":interactive_session_command(spec)}
    result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True)
    if result.returncode: raise RuntimeError("native role delivery failed: " + result.stderr.strip())
    try: response = json.loads(result.stdout)
    except json.JSONDecodeError as error: raise RuntimeError("malformed native role delivery response") from error
    if not isinstance(response, dict) or response.get("ok") is not True: raise RuntimeError(str(response.get("reason", "native role delivery failed")) if isinstance(response, dict) else "invalid native role delivery response")
    if response.get("window") != spec["window"] or response.get("result") != "role_delivery_confirmed" or not all(isinstance(response.get(key), str) and response[key] for key in ("window", "tab", "session")): raise RuntimeError("native role delivery confirmation is incomplete")
    return response



def bridge_environment_preflight(runner=subprocess.run) -> None:
    try:
        result = runner([sys.executable, "-c", "import iterm2"], capture_output=True, text=True, timeout=10)
        if result.returncode: raise RuntimeError(result.stderr.strip() or "import iterm2 failed")
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
        raise RuntimeError(f"iTerm bridge dependency unavailable for interpreter {sys.executable}: {error}; use the configured Orchestr8 virtualenv interpreter with iTerm dependencies installed") from error


def update_role_label(destination: dict, role_name: str, description: str, runner=subprocess.run) -> dict:
    title = f"ORCHESTR8 · {role_name.title()} · {description}"
    try:
        request = {"mode":"role_label", "title":title, **{k:destination[k] for k in ("window", "tab", "session")}}
        result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True, timeout=10)
        if result.returncode: raise RuntimeError("label bridge failed: " + result.stderr.strip())
        response = json.loads(result.stdout)
        if not isinstance(response, dict) or response.get("ok") is not True: raise RuntimeError(str(response.get("reason", "label update failed")) if isinstance(response, dict) else "invalid label response")
        if any(response.get(k) != request[k] for k in ("window", "tab", "session", "title")): raise RuntimeError("label confirmation does not match destination")
        return {"status":"updated", "title":title}
    except Exception as error:
        return {"status":"failed", "reason":str(error), "title":title}


def deliver_iterm_trigger(spec: dict, runner=subprocess.run) -> dict:
    request = {"mode":"role_trigger", **{key:spec[key] for key in ("window", "tab", "session", "payload")}}
    try: result = runner([sys.executable, str(ROOT / ".agent" / "iterm_probe.py")], input=json.dumps(request), text=True, capture_output=True, timeout=15)
    except subprocess.TimeoutExpired as error: raise RuntimeError("native trigger timed out") from error
    if result.returncode: raise RuntimeError("native trigger bridge failed: " + result.stderr.strip())
    try: response = json.loads(result.stdout)
    except json.JSONDecodeError as error: raise RuntimeError("native trigger returned malformed diagnostics") from error
    if not isinstance(response, dict) or response.get("ok") is not True: raise RuntimeError(str(response.get("reason", "native trigger failed")) if isinstance(response, dict) else "invalid native trigger response")
    if response.get("result") != "trigger_delivery_confirmed" or response.get("submission") != "carriage_return_sent" or any(response.get(key) != spec[key] for key in ("window", "tab", "session")): raise RuntimeError("native trigger confirmation does not match destination")
    return response


def session_path(current: Path) -> Path: return current / "supervised_session.json"
def tab_state(current: Path) -> Path: return current / "tabs.json"
def load_supervised_session(current: Path) -> dict:
    path = session_path(current)
    if not path.is_file(): raise RuntimeError("supervised session is missing")
    try: session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error: raise RuntimeError("supervised session is malformed") from error
    phase = session.get("phase") if isinstance(session, dict) else None
    if not isinstance(session, dict) or not isinstance(phase, str) or phase not in SUPERVISED_PHASES:
        raise RuntimeError("supervised session has an invalid phase")
    return session
def displayed_role(phase: str) -> str:
    if phase not in SUPERVISED_PHASES: raise RuntimeError("supervised session has an invalid phase")
    return "coordinator" if phase.startswith("coordinator") else phase
def next_action(phase: str) -> str: return f"{displayed_role(phase)}: {ROLE_PHRASES[phase]}"
def print_session(root: Path, config: dict, current: Path, phase: str, title: str) -> None:
    print(json.dumps({"outcome": "success", "title": title, "roles": list(ROLE_ORDER), "phase": phase, "next_action": next_action(phase), "task_authority": config["task_authority"], "current": str(current.relative_to(root)), "tab_labels": [tab_spec(root, config, name)["title"] for name in ROLE_ORDER]}, indent=2))


def supervised_init(root: Path, config: dict, current: Path, tabs: bool, launcher=launch_iterm_tab, tabs_probe: bool = False, tabs_layout_probe: bool = False, tabs_coordinator_bootstrap_probe: bool = False) -> None:
    if not tabs: return
    if not tabs_probe and not tabs_layout_probe and not tabs_coordinator_bootstrap_probe and launcher is launch_iterm_tab:
        raise RuntimeError("full --tabs launch is unavailable pending an approved native iTerm2 design; use a documented --tabs probe or recover with a fresh target")
    if tabs_probe:
        spec = {"host":"iterm2", "probe":True, "role":"host_probe", "title":"ORCHESTR8 · Host probe", "cwd":str(root), "instruction":"", "command":[], "sandbox":"read-only", "bootstrap":"host probe"}
        probe_launcher = launch_iterm_probe if launcher is launch_iterm_tab else launcher
        try: observation = probe_launcher(spec)
        except Exception as error: raise RuntimeError("host probe stopped safely before workflow state creation: " + str(error)) from error
        print(json.dumps({"title":"host probe", "host":"iterm2", "roles_started":0, "supervised_state_created":False, "readiness":observation or "fake launcher confirmed", "result":"one probe tab requested; inspect its bounded diagnostics"}))
        return
    if tabs_layout_probe:
        spec = {"host":"iterm2", "layout_probe":True, "role":"layout_probe", "titles":["ORCHESTR8 · Coordinator", "ORCHESTR8 · Developer", "ORCHESTR8 · Reviewer"], "cwd":str(root), "instruction":"", "command":[], "sandbox":"read-only"}
        layout_launcher = launch_iterm_layout_probe if launcher is launch_iterm_tab else launcher
        try: observation = layout_launcher(spec)
        except Exception as error: raise RuntimeError("layout probe stopped safely before workflow state creation: " + str(error)) from error
        if not isinstance(observation, dict): observation = {"window":"fake-window", "tabs":["fake-1", "fake-2", "fake-3"], "elapsed_seconds":0, "result":"confirmed"}
        print(json.dumps({"title":"layout probe", "host":"iterm2", "roles_started":0, "supervised_state_created":False, "window":observation["window"], "tabs":observation["tabs"], "elapsed_seconds":observation["elapsed_seconds"], "result":observation["result"]}))
        return
    if tabs_coordinator_bootstrap_probe:
        spec = {"host":"iterm2", "coordinator_bootstrap_probe":True, "role":"coordinator_bootstrap_probe", "title":"ORCHESTR8 · Coordinator · bootstrap probe", "cwd":str(root), "instruction":"", "command":[], "sandbox":"read-only"}
        bootstrap_launcher = launch_iterm_coordinator_bootstrap_probe if launcher is launch_iterm_tab else launcher
        try: observation = bootstrap_launcher(spec)
        except Exception as error: raise RuntimeError("Coordinator bootstrap probe stopped safely before workflow state creation: " + str(error)) from error
        if not isinstance(observation, dict): observation = {"window":"fake-window", "tab":"fake-tab", "session":"fake-session", "elapsed_seconds":0, "result":"unverified_bootstrap_delivered"}
        print(json.dumps({"title":"Coordinator bootstrap probe", "host":"iterm2", "roles_started":0, "supervised_state_created":False, "window":observation["window"], "tab":observation["tab"], "session":observation["session"], "elapsed_seconds":observation["elapsed_seconds"], "result":observation["result"], "human_action":"visually confirm Codex remains interactive; bootstrap delivery is unverified"}))
        return
    specs = [tab_spec(root, config, name) for name in ROLE_ORDER]
    try:
        for spec in specs: launcher(spec)
    except Exception as error:
        stop = {"state": "HUMAN_REQUIRED", "category": "failed_or_incomplete_validation", "reason": str(error), "phase": "tab_launch"}
        raise RuntimeError("tab launch stopped safely before workflow state creation: " + json.dumps(stop, sort_keys=True)) from error
    current.mkdir(parents=True, exist_ok=True)
    write_json(tab_state(current), {"roles": specs, "state": "waiting_for_human", "non_authoritative": True})
    write_json(session_path(current), {"phase": "coordinator_initial", "state": "WAITING_FOR_HUMAN"})


def refusal(reason: str, category: str = "failed_or_incomplete_validation", recovery: str = "preserve evidence and resolve the issue before a fresh authorized run", **details: object) -> int:
    print(json.dumps({"outcome":"refusal", "state":"HUMAN_REQUIRED", "category":category, "reason":reason, "recovery":recovery, **details}))
    return 2


def load_saved_state(state_path: Path, config: dict) -> dict:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("saved controller state is missing, unreadable or malformed") from error
    if not isinstance(state, dict): raise RuntimeError("saved controller state is not an object")
    iteration = state.get("iteration")
    if type(iteration) is not int or iteration < 0: raise RuntimeError("saved controller state has invalid iteration")
    if "active_iteration" in state and (type(state["active_iteration"]) is not int or state["active_iteration"] <= iteration): raise RuntimeError("saved controller state has invalid active iteration")
    for key in ("status", "phase", "config_sha256", "task_snapshot_sha256", "last_authority_sha256"):
        if key in state and not isinstance(state[key], str): raise RuntimeError(f"saved controller state has invalid {key}")
    if "max_iterations" in state and (type(state["max_iterations"]) is not int or state["max_iterations"] < 1): raise RuntimeError("saved controller state has invalid max_iterations")
    if state.get("status") not in ("READY", "RUNNING", "PREPARING", "HUMAN_REQUIRED"): raise RuntimeError("saved controller state has invalid status")
    if state.get("status") in ("RUNNING", "PREPARING") and (type(state.get("active_iteration")) is not int or not isinstance(state.get("phase"), str)): raise RuntimeError("saved active state lacks trustworthy run identity")
    if state.get("status") == "HUMAN_REQUIRED" and (state.get("phase") is not None or state.get("active_iteration") is not None): raise RuntimeError("terminal state contains active run metadata")
    if state.get("phase") not in (None, "coordinator", "coordinator_initial", "developer", "reviewer", "coordinator_review"): raise RuntimeError("saved controller state has invalid phase")
    if state.get("phase") == "coordinator_initial":
        snapshot = state.get("task_snapshot_sha256")
        if state.get("active_iteration") != iteration + 1 or state.get("config_sha256") != config["_sha256"] or not isinstance(snapshot, str) or len(snapshot) != 64 or any(char not in "0123456789abcdef" for char in snapshot):
            raise RuntimeError("saved Coordinator state lacks trustworthy run identity")
    if state.get("config_sha256") not in (None, config["_sha256"]): raise RuntimeError("saved state belongs to a different controller configuration")
    return state


def start_supervised(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, launcher=launch_iterm_coordinator_start, task_limit: int = 1, attempt_limit: int = 1) -> int:
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error), recovery="wait for the lock owner; remove a lock only after verifying it is stale")
    try:
        return _start_supervised_locked(root, config, authority, approval_record, current, history, state_path, launcher, task_limit, attempt_limit)
    finally:
        release_lock(lock)


def _start_supervised_locked(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, launcher=launch_iterm_coordinator_start, task_limit: int = 1, attempt_limit: int = 1) -> int:
    try: state = load_saved_state(state_path, config)
    except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
    iteration = state["iteration"] + 1
    try:
        if type(task_limit) is not int or task_limit not in (1, 2) or type(attempt_limit) is not int or not 1 <= attempt_limit <= 100: raise RuntimeError("task limit must be 1 or 2 and attempt limit must be 1 to 100")
        if state.get("phase") or state.get("status") not in ("READY", None) or state.get("active_iteration") is not None: raise RuntimeError("start refuses an active or stale supervised session")
        if current.exists() and any(current.iterdir()): raise RuntimeError("start refuses stale supervised runtime artifacts")
        head, base = clean_baseline(root, runtime_root(current, history, state_path))
        excluded_fingerprint = excluded_project_fingerprint(root, runtime_root(current, history, state_path))
        if not authority.is_file(): raise RuntimeError("configured durable task authority is missing")
        data = read_regular_evidence(authority); approval_entries(approval_record); approval_bytes = read_regular_evidence(approval_record); old_hash = state.get("last_authority_sha256")
        if old_hash and old_hash != digest(data):
            entries = approval_entries(approval_record)
            if not any(item.get("prior_authority_sha256") == old_hash and item.get("new_authority_sha256") == digest(data) and isinstance(item.get("approved_at"), str) and item["approved_at"] for item in entries): raise RuntimeError("authority change lacks matching explicit approval")
        if (history / f"{iteration:03d}").exists(): raise RuntimeError("next iteration already exists in history")
        policy_identity, policy_bytes = effective_policy(root, config)
        spec = tab_spec(root, config, "coordinator", production=True)
        spec.update(coordinator_start=True, current=str(current), authority=str(authority))
        if launcher is launch_iterm_coordinator_start: bridge_environment_preflight()
    except (KeyError, RuntimeError, OSError, UnicodeError, json.JSONDecodeError) as error:
        return refusal(str(error))
    try:
        current.mkdir(parents=True, exist_ok=True)
        state.update(active_iteration=iteration, phase="coordinator_initial", status="PREPARING", config_sha256=config["_sha256"], protected_authority_sha256=digest(data), protected_approval_sha256=digest(approval_bytes), protected_excluded_sha256=excluded_fingerprint, baseline={"head":head, "manifest":base}, task_limit=task_limit, attempt_limit=attempt_limit, task_number=1, attempt=1, task_id=uuid.uuid4().hex)
        state["effective_policy"] = policy_identity
        (current / "workflow_policy.json").write_bytes(policy_bytes); write_json(current / "effective_policy.json", policy_identity)
        meta = snapshot_authority(root, authority, approval_record, current, config, state)
        state["task_snapshot_sha256"] = meta["sha256"]; write_json(current / "baseline.json", state.pop("baseline"))
        session = {"phase":"coordinator_initial", "state":"PREPARING_DELIVERY", "task_snapshot_sha256":meta["sha256"], "launch_mode":"coordinator_only"}
        write_json(session_path(current), session); write_json(state_path, state)
        verify_active_policy(root, config, current, state)
        observation = launcher(spec)
        if not isinstance(observation, dict) or not all(isinstance(observation.get(k), str) and observation[k] for k in ("window", "tab", "session")) or not isinstance(observation.get("elapsed_seconds"), (int, float)) or observation.get("result") != "coordinator_delivery_confirmed": raise RuntimeError("native Coordinator start returned incomplete delivery confirmation")
        session.update(state="WAITING_FOR_HUMAN", tab={key:observation[key] for key in ("window", "tab", "session")}, elapsed_seconds=observation["elapsed_seconds"])
        write_json(tab_state(current), {"roles":[{"role":"coordinator", "title":spec["title"], "host":"iterm2", "window":observation["window"], "tab":observation["tab"], "session":observation["session"]}], "state":"waiting_for_human", "non_authoritative":True})
        state.update(status="RUNNING", coordinator_tab=session["tab"]); write_json(session_path(current), session); record_runtime_guard(current, history, state_path, state, "coordinator")
        print(json.dumps({"outcome":"success", "title":"started Coordinator", "phase":"coordinator_initial", "roles_started":["coordinator"], "supervised_state_created":True, "task_snapshot_sha256":meta["sha256"], "window":observation["window"], "tab":observation["tab"], "session":observation["session"], "result":"wait for human Start project: <human initial brief>", "next_action":"confirm the tab and send Start project: <human initial brief>"}))
        return 0
    except (KeyError, RuntimeError, OSError, UnicodeError, json.JSONDecodeError) as error:
        return refusal("Coordinator preparation or delivery incomplete: " + str(error), recovery="preserve preparation evidence; inspect any partial tab and delivery, resolve prior process and lock ownership, then use a fresh authorized run", delivery="uncertain", partial_effects="preparation or physical tab effects may already exist")





def runtime_evidence(root: Path, current: Path, history: Path, state_path: Path, allowed_role: str | None, exclude_session: bool = False) -> dict:
    runtime = runtime_root(current, history, state_path)
    allowed = current / "coordinator_summary.md" if allowed_role == "coordinator_summary" else current / f".{allowed_role}.json" if allowed_role else None
    if allowed_role in ("developer", "reviewer"):
        try:
            session = json.loads(read_regular_evidence(session_path(current)))
            filename = session.get("report_slots", {}).get(allowed_role)
            if filename and re.fullmatch(r"\.(developer|reviewer)-[0-9a-f]{32}\.json", filename): allowed = current / filename
        except (OSError, ValueError, TypeError, AttributeError): pass
    evidence = {}
    def onerror(error: OSError) -> None: raise error
    for directory, dirs, files in os.walk(runtime, followlinks=False, onerror=onerror):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            if path == state_path or path == allowed or (allowed_role == "coordinator_summary" and path in (current / "coordinator_proposal.md", current / "correction_scope.json")) or path == state_path.parent / "orchestrate.lock" or (exclude_session and path == session_path(current)): continue
            relative = str(path.relative_to(runtime)); info = path.lstat()
            if stat.S_ISLNK(info.st_mode): evidence[relative] = {"symlink":os.readlink(path)}
            elif stat.S_ISREG(info.st_mode): evidence[relative] = {"sha256":digest(read_regular_evidence(path))}
            elif stat.S_ISDIR(info.st_mode): evidence[relative] = {"directory":True}
            else: raise RuntimeError("unsupported runtime evidence type: " + relative)
    return evidence


def record_runtime_guard(current: Path, history: Path, state_path: Path, state: dict, allowed_role: str | None) -> None:
    projection = {key:value for key,value in state.items() if key != "evidence_guard"}
    state["evidence_guard"] = {"state":projection, "allowed_role":allowed_role, "files":runtime_evidence(state_path.parent, current, history, state_path, allowed_role)}
    write_json(state_path, state)


def verify_runtime_guard(current: Path, history: Path, state_path: Path, state: dict) -> None:
    if read_regular_evidence(state_path) != (json.dumps(state, indent=2, sort_keys=True) + "\n").encode("utf-8"): raise RuntimeError("protected controller state bytes changed")
    guard = state.get("evidence_guard")
    if not isinstance(guard, dict) or guard.get("state") != {key:value for key,value in state.items() if key != "evidence_guard"}: raise RuntimeError("protected controller state changed")
    allowed = guard.get("allowed_role")
    if allowed not in (None, "coordinator", "developer", "reviewer"): raise RuntimeError("invalid protected evidence guard")
    if guard.get("files") != runtime_evidence(state_path.parent, current, history, state_path, allowed): raise RuntimeError("protected runtime evidence changed")


def read_regular_evidence(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise RuntimeError("evidence is not a regular file")
        return stream.read()


def effective_policy(root: Path, config: dict) -> tuple[dict, bytes]:
    raw = read_regular_evidence(root / ".agent" / "workflow_policy.json")
    policy = json.loads(raw)
    if not isinstance(policy, dict) or type(policy.get("version")) is not int or policy["version"] != 1: raise RuntimeError("unsupported workflow policy version")
    decisions = policy.get("decisions")
    if decisions != {"CHANGES_REQUIRED":"correction", "APPROVED":"next_task", "completion_or_exhausted_budget":"stop", "unsafe_or_ambiguous_evidence":"stop"}: raise RuntimeError("unsupported workflow policy decisions")
    if set(policy) != {"version", "decisions"}: raise RuntimeError("unsupported workflow policy fields")
    roles = {name:digest(read_regular_evidence(project_path(root, role(config, name)["instruction"]))) for name in ROLE_ORDER}
    return {"version":1, "policy_sha256":digest(raw), "role_sha256":roles}, raw


def verify_active_policy(root: Path, config: dict, current: Path, state: dict) -> dict:
    expected = state.get("effective_policy")
    if not isinstance(expected, dict): raise RuntimeError("active run lacks supported effective policy identity; preserve evidence and start a fresh authorized run")
    if type(expected.get("version")) is not int or expected["version"] != 1: raise RuntimeError("active run has unsupported effective policy identity")
    actual, raw = effective_policy(root, config)
    if actual != expected or read_regular_evidence(current / "workflow_policy.json") != raw or json.loads(read_regular_evidence(current / "effective_policy.json")) != expected: raise RuntimeError("active workflow policy or role guidance changed")
    return json.loads(raw)


def decision_guidance(policy: dict) -> str:
    labels = {"CHANGES_REQUIRED":"Actionable CHANGES_REQUIRED with attempts remaining", "APPROVED":"APPROVED with work and task budget remaining", "completion_or_exhausted_budget":"Completion, human stop, or exhausted applicable budget", "unsafe_or_ambiguous_evidence":"Unsafe, missing, or ambiguous evidence"}
    actions = {"correction":"Coordinator may propose a correction to the same task tied to findings; ask for human approval only when eligible.", "next_task":"Coordinator may propose a bounded next task; ask for human approval only when eligible.", "stop":"Stop and send nothing; do not request approval for a proposal."}
    return "\n".join(labels[key] + ": " + actions[value] for key, value in policy["decisions"].items())


def proposal_decision(policy: dict, state: dict, session: dict) -> tuple[str, str]:
    task_limit, attempt_limit, task_number, attempt = (state.get(k) for k in ("task_limit", "attempt_limit", "task_number", "attempt"))
    if any(type(v) is not int for v in (task_limit, attempt_limit, task_number, attempt)) or not 1 <= task_number <= task_limit <= 2 or not 1 <= attempt <= attempt_limit <= 100 or not isinstance(state.get("task_id"), str) or not state["task_id"]: return "stop", "run lacks valid authorized task and attempt budgets"
    decision = policy["decisions"].get(session.get("review_verdict"), "stop")
    if decision == "correction" and attempt >= attempt_limit: return "stop", "authorized attempt limit exhausted"
    if decision == "next_task" and task_number >= task_limit: return "stop", "authorized task limit exhausted"
    if decision not in ("correction", "next_task"): return "stop", "review verdict does not permit a proposal"
    return decision, "eligible"


def review_escalation(result: dict) -> tuple[str, str] | None:
    category, reason = result.get("human_category"), result.get("human_reason")
    if result.get("verdict") != "HUMAN_REQUIRED" and category is None and reason is None: return None
    return category or "unresolved_requirement", reason.strip() if isinstance(reason, str) and reason.strip() else result["summary"]




def record_completion_guard(root: Path, current: Path, history: Path, state_path: Path, session: dict, reviewed_project: dict, reviewed_excluded: str, expected_files: dict | None = None, expected_state_sha256: str | None = None) -> None:
    if excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != reviewed_excluded: raise RuntimeError("excluded project evidence changed during completion")
    project = project_review_identity(root, runtime_root(current, history, state_path))
    if project != reviewed_project: raise RuntimeError("project changed during completion")
    files = runtime_evidence(root, current, history, state_path, "coordinator_summary", exclude_session=True)
    if expected_files is not None and files != expected_files: raise RuntimeError("protected completion evidence changed during Coordinator delivery")
    state_sha256 = digest(read_regular_evidence(state_path))
    if expected_state_sha256 is not None and state_sha256 != expected_state_sha256: raise RuntimeError("controller state changed during Coordinator delivery")
    session["completion_guard"] = {"session":{key:value for key,value in session.items() if key != "completion_guard"}, "state_sha256":state_sha256, "files":files, "project":project, "excluded_sha256":reviewed_excluded}
    write_json(session_path(current), session)


def verify_completion_guard(root: Path, current: Path, history: Path, state_path: Path, session: dict) -> None:
    guard = session.get("completion_guard")
    if not isinstance(guard, dict) or guard.get("session") != {key:value for key,value in session.items() if key != "completion_guard"} or guard.get("state_sha256") != digest(read_regular_evidence(state_path)) or guard.get("files") != runtime_evidence(root, current, history, state_path, "coordinator_summary", exclude_session=True) or guard.get("project") != project_review_identity(root, runtime_root(current, history, state_path)) or guard.get("excluded_sha256") != excluded_project_fingerprint(root, runtime_root(current, history, state_path)):
        raise RuntimeError("completed iteration evidence or project changed")


def verify_protected_authorities(authority: Path, approval_record: Path, state: dict) -> None:
    if digest(read_regular_evidence(authority)) != state.get("protected_authority_sha256") or digest(read_regular_evidence(approval_record)) != state.get("protected_approval_sha256"):
        raise RuntimeError("task authority or approval evidence changed")


def completed_identity(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path) -> tuple[dict, dict]:
    state = load_saved_state(state_path, config); session = load_supervised_session(current)
    if state.get("status") != "READY" or session.get("launch_mode") != "coordinator_only" or session.get("phase") != "coordinator_review" or session.get("state") != "COMPLETED_COORDINATOR_REVIEW": raise RuntimeError("no completed attempt awaiting Coordinator proposal")
    verify_active_policy(root, config, current, state)
    verify_completion_guard(root, current, history, state_path, session)
    attempts = session.get("trigger_attempts", {})
    if not isinstance(attempts, dict): raise RuntimeError("invalid Coordinator delivery evidence")
    delivery = attempts.get("coordinator")
    if delivery is not None and (not isinstance(delivery, dict) or delivery.get("status") != "confirmed"): raise RuntimeError("Coordinator delivery is uncertain")
    verify_protected_authorities(authority, approval_record, state)
    validate_snapshot(root, authority, current, config, state)
    iteration = state["iteration"]; archived = history / f"{iteration:03d}"
    archived_state = read_regular_evidence(archived / "state.json")
    if json.loads(archived_state) != state: raise RuntimeError("completed attempt archive is inconsistent")
    review = read_regular_evidence(archived / "review_report.md")
    run_id = digest(json.dumps({"config_sha256":config["_sha256"], "iteration":iteration, "archived_state_sha256":digest(archived_state), "review_sha256":digest(review), "tabs_sha256":digest(read_regular_evidence(tab_state(current)))}, sort_keys=True).encode())
    return {"run_id":run_id, "iteration":iteration, "review_sha256":digest(review), "snapshot_sha256":state["task_snapshot_sha256"]}, session


def validate_archived_review(root: Path, config: dict, history: Path, iteration: int, session: dict) -> None:
    archived = history / f"{iteration:03d}"
    review_name = session.get("report_slots", {}).get("reviewer", ".reviewer.json")
    if not isinstance(review_name, str) or not re.fullmatch(r"\.reviewer(?:-[0-9a-f]{32})?\.json", review_name): raise RuntimeError("invalid archived Reviewer identity")
    review = validate_output(root, config, "reviewer", json.loads(read_regular_evidence(archived / review_name)))
    if review.get("verdict") != session.get("review_verdict") or review_escalation(review) is not None: raise RuntimeError("archived Reviewer evidence requires human direction")
    if read_regular_evidence(archived / "review_report.md") != report("Reviewer report", review).encode("utf-8"): raise RuntimeError("archived Reviewer report does not match its structured evidence")


def proposal_identity(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, *, include_bytes: bool = False) -> tuple[dict, dict] | tuple[dict, dict, bytes]:
    base, session = completed_identity(root, config, authority, approval_record, current, history, state_path)
    if os.path.lexists(current / "proposal_stop.json"): raise RuntimeError("human stopped this proposal decision")
    validate_archived_review(root, config, history, base["iteration"], session)
    summary = read_regular_evidence(current / "coordinator_summary.md")
    proposal = read_regular_evidence(current / "coordinator_proposal.md")
    if not summary.strip() or not proposal.strip(): raise RuntimeError("Coordinator summary or proposal is empty")
    proposal_text = proposal.decode("utf-8")
    identity = {**base, "proposal_sha256":digest(proposal), "proposal":proposal_text, "summary_sha256":digest(summary)}
    scope = current / "correction_scope.json"
    if session.get("review_verdict") == "CHANGES_REQUIRED" and os.path.lexists(scope):
        raw = read_regular_evidence(scope); identity.update(scope_sha256=digest(raw), correction_scope=json.loads(raw))
    return (identity, session, proposal) if include_bytes else (identity, session)


def verify_correction_scope(current: Path, history: Path, state: dict, identity: dict) -> None:
    scope = identity.get("correction_scope")
    if not isinstance(scope, dict): raise RuntimeError("correction requires a finding mapping")
    iteration, attempt = state["iteration"], state.get("attempt")
    if type(attempt) is not int or attempt < 1: raise RuntimeError("invalid correction attempt identity")
    origin = iteration - attempt + 1
    origin_dir = history / f"{origin:03d}"; origin_state = json.loads(read_regular_evidence(origin_dir / "state.json")); original = read_regular_evidence(origin_dir / "authoritative_task.md")
    if origin_state.get("task_id") != state.get("task_id") or origin_state.get("task_snapshot_sha256") != digest(original): raise RuntimeError("original task identity is inconsistent")
    if original.decode("utf-8") not in identity["proposal"]: raise RuntimeError("correction must retain the complete original task and criteria")
    expected = {"task_id":state["task_id"], "original_snapshot_sha256":digest(original), "original_iteration":origin, "predecessor_iteration":iteration, "review_sha256":identity["review_sha256"]}
    if set(scope) != set(expected) | {"criteria_changes", "findings"} or any(scope.get(k) != v for k,v in expected.items()) or scope.get("criteria_changes") != []: raise RuntimeError("correction task, predecessor or criteria identity is inconsistent")
    archived = history / f"{iteration:03d}"; old_session = json.loads(read_regular_evidence(archived / "supervised_session.json"))
    review_name = old_session.get("report_slots", {}).get("reviewer", ".reviewer.json")
    if not isinstance(review_name, str) or not re.fullmatch(r"\.reviewer(?:-[0-9a-f]{32})?\.json", review_name): raise RuntimeError("invalid archived Reviewer identity")
    review = json.loads(read_regular_evidence(archived / review_name)); findings = review.get("findings")
    if not isinstance(findings, list): raise RuntimeError("archived findings are invalid")
    required = {i:digest(item.encode("utf-8")) for i,item in enumerate(findings) if isinstance(item, str) and item.strip()}
    mapping = scope.get("findings")
    if not required or not isinstance(mapping, list) or len(mapping) != len(required): raise RuntimeError("correction must map every actionable finding")
    seen = set()
    for entry in mapping:
        if not isinstance(entry, dict) or set(entry) != {"finding_index", "finding_sha256", "change"}: raise RuntimeError("invalid finding mapping")
        index, change = entry["finding_index"], entry["change"]
        if type(index) is not int or index not in required or index in seen or entry["finding_sha256"] != required[index] or not isinstance(change, str) or not change.strip() or change not in identity["proposal"]: raise RuntimeError("finding mapping is missing, unrelated or absent from instructions")
        seen.add(index)


def stop_proposal(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, run_id: str, iteration: int) -> int:
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error))
    try:
        try:
            identity, session = completed_identity(root, config, authority, approval_record, current, history, state_path)
            if (run_id, iteration) != (identity["run_id"], identity["iteration"]): raise RuntimeError("stop identity is stale")
            target = current / "proposal_stop.json"
            if os.path.lexists(target): raise RuntimeError("human stop already recorded")
            if os.path.lexists(current / "proposal_approval.json"): raise RuntimeError("proposal was already approved")
            record = proposal_stop_record(current, identity)
            data = json.dumps(record, sort_keys=True).encode("utf-8")
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            guard = session["completion_guard"]
            expected_files = {**guard["files"], str(target.relative_to(runtime_root(current, history, state_path))):{"sha256":digest(data)}}
            record_completion_guard(root, current, history, state_path, session, guard["project"], guard["excluded_sha256"], expected_files=expected_files, expected_state_sha256=guard["state_sha256"])
            print(json.dumps({"outcome":"success", "state":"HUMAN_STOPPED", **identity})); return 0
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal(str(error), "stale_or_mismatched_task_state", recovery="preserve evidence and inspect any partial stop")
    finally: release_lock(lock)


def proposal_stop_record(current: Path, identity: dict) -> dict:
    summary = read_regular_evidence(current / "coordinator_summary.md")
    if not summary.strip(): raise RuntimeError("Coordinator summary is empty")
    def optional_hash(name: str) -> str | None:
        path = current / name
        return digest(read_regular_evidence(path)) if os.path.lexists(path) else None
    return {**identity, "kind":"human_proposal_stop", "version":1, "summary_sha256":digest(summary), "proposal_sha256":optional_hash("coordinator_proposal.md"), "scope_sha256":optional_hash("correction_scope.json")}


def pending_proposal(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path) -> int:
    try:
        identity, session = proposal_identity(root, config, authority, approval_record, current, history, state_path)
        state = load_saved_state(state_path, config); decision, reason = proposal_decision(verify_active_policy(root, config, current, state), state, session)
        print(json.dumps({"outcome":"success", **identity, "decision":decision, "reason":reason, "approval_recorded":os.path.lexists(current / "proposal_approval.json")})); return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
        return refusal(str(error), "stale_or_mismatched_task_state")


def proposal_approval_record(identity: dict) -> dict:
    record = {key:value for key,value in identity.items() if key != "proposal"}
    record.update(kind="human_control_terminal_approval", version=1)
    if "scope_sha256" in identity: record["correction_scope_confirmed"] = True
    return record


def approve_proposal(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, run_id: str, iteration: int, proposal_sha256: str, scope_sha256: str | None = None, confirm_correction_scope: bool = False) -> int:
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error))
    try:
        try:
            identity, session = proposal_identity(root, config, authority, approval_record, current, history, state_path)
            if (run_id, iteration, proposal_sha256) != (identity["run_id"], identity["iteration"], identity["proposal_sha256"]): raise RuntimeError("proposal, run or attempt identity is stale")
            state = load_saved_state(state_path, config); decision, reason = proposal_decision(verify_active_policy(root, config, current, state), state, session)
            if decision == "stop": raise RuntimeError(reason)
            if decision == "correction":
                verify_correction_scope(current, history, state, identity)
                if not confirm_correction_scope or scope_sha256 != identity.get("scope_sha256"): raise RuntimeError("explicit correction scope confirmation and exact scope hash are required")
            target = current / "proposal_approval.json"
            if os.path.lexists(target): raise RuntimeError("proposal approval already exists")
            record = proposal_approval_record(identity)
            data = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
            # Exclusive creation preserves prior or partially written evidence.
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            old_guard = session["completion_guard"]
            expected_files = {**old_guard["files"], str(target.relative_to(runtime_root(current, history, state_path))):{"sha256":digest(data)}}
            record_completion_guard(root, current, history, state_path, session, old_guard["project"], old_guard["excluded_sha256"], expected_files=expected_files, expected_state_sha256=old_guard["state_sha256"])
            print(json.dumps({"outcome":"success", "approval":str(target), **record, "next_action":"approval recorded; no authority publication or dispatch"})); return 0
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal(str(error), "stale_or_mismatched_task_state", recovery="preserve evidence; inspect any partial approval before proceeding")
    finally: release_lock(lock)


def rollover_correction(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path) -> int:
    return rollover_approved(root, config, authority, approval_record, current, history, state_path, "correction")


def rollover_next_task(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path) -> int:
    return rollover_approved(root, config, authority, approval_record, current, history, state_path, "next_task")


def rollover_approved(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, kind: str) -> int:
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error))
    preserve_lock = False
    try:
        try:
            identity, session, proposal = proposal_identity(root, config, authority, approval_record, current, history, state_path, include_bytes=True)
            record = json.loads(read_regular_evidence(current / "proposal_approval.json"))
            expected = proposal_approval_record(identity)
            if record != expected: raise RuntimeError("recorded approval does not match the proposal and predecessor")
            state = load_saved_state(state_path, config)
            policy = verify_active_policy(root, config, current, state)
            decision, reason = proposal_decision(policy, state, session)
            if decision != kind: raise RuntimeError(reason if decision == "stop" else "rollover kind does not match review decision")
            if decision == "correction": verify_correction_scope(current, history, state, identity)
            task_number, attempt = state["task_number"], state["attempt"]
            roles = json.loads(read_regular_evidence(tab_state(current)))["roles"]
            if [item.get("role") for item in roles] != list(ROLE_ORDER) or any(not all(isinstance(item.get(k), str) and item[k] for k in ("window", "tab", "session")) or item["window"] != roles[0]["window"] for item in roles): raise RuntimeError("recorded tabs are inconsistent")
            reviewed = json.loads(read_regular_evidence(current / "review_identity.json"))
            if reviewed.get("project") != session["completion_guard"]["project"] or reviewed.get("excluded_sha256") != session["completion_guard"]["excluded_sha256"]: raise RuntimeError("reviewed project identity is inconsistent")
            target = history / (f"{identity['iteration']:03d}-coordination")
            marker = history / (f"{identity['iteration']:03d}-rollover.json")
            if os.path.lexists(target) or os.path.lexists(marker) or os.path.lexists(history / f"{identity['iteration'] + 1:03d}"): raise RuntimeError("rollover history already exists")
            authority_mode = stat.S_IMODE(authority.stat().st_mode)
            tab_bytes = read_regular_evidence(tab_state(current)); coordinator = read_regular_evidence(current / ".coordinator.json")
            policy_bytes = read_regular_evidence(current / "workflow_policy.json"); effective_bytes = read_regular_evidence(current / "effective_policy.json")
            if digest(coordinator) != session.get("accepted_coordinator_sha256"): raise RuntimeError("Coordinator evidence changed")
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal(str(error), "stale_or_mismatched_task_state")
        try:
            # Once persistence begins, an exception or interruption leaves the
            # existing lock as a recovery barrier, even if the final write landed.
            preserve_lock = True
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(expected, stream, sort_keys=True); stream.flush(); os.fsync(stream.fileno())
            os.rename(current, target); current.mkdir()
            (current / "workflow_policy.json").write_bytes(policy_bytes); (current / "effective_policy.json").write_bytes(effective_bytes)
            temp = authority.parent / (".orchestr8-publish-" + uuid.uuid4().hex)
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), authority_mode); stream.write(proposal); stream.flush(); os.fsync(stream.fileno())
            os.replace(temp, authority)
            project = project_review_identity(root, runtime_root(current, history, state_path))
            prior = reviewed["project"]; authority_name = str(authority.relative_to(root))
            if project["head"] != prior["head"] or {k:v for k,v in project["manifest"].items() if k != authority_name} != {k:v for k,v in prior["manifest"].items() if k != authority_name} or excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != reviewed["excluded_sha256"]: raise RuntimeError("project changed during publication")
            (current / "authoritative_task.md").write_bytes(proposal)
            write_json(current / "task_snapshot.json", {"source":authority_name, "sha256":digest(proposal), "bytes":len(proposal), "config_sha256":config["_sha256"]})
            write_json(current / "approval_evidence.json", record)
            (current / "tabs.json").write_bytes(tab_bytes); (current / ".coordinator.json").write_bytes(coordinator)
            write_json(current / "baseline.json", {"head":project["head"], "manifest":project["manifest"]})
            attempt_id = uuid.uuid4().hex
            next_session = {"launch_mode":"coordinator_only", "phase":"developer", "state":"WAITING_FOR_HUMAN", "tab":session["tab"], "task_snapshot_sha256":digest(proposal), "baseline_sha256":digest(read_regular_evidence(current / "baseline.json")), "accepted_coordinator_sha256":digest(coordinator), "rollover_project":project, "report_slots":{role:"." + role + "-" + attempt_id + ".json" for role in ("developer", "reviewer")}, "attempt_id":attempt_id}
            state.update(status="RUNNING", phase="developer", active_iteration=identity["iteration"] + 1, task_id=state["task_id"] if kind == "correction" else uuid.uuid4().hex, task_number=task_number if kind == "correction" else task_number + 1, attempt=attempt + 1 if kind == "correction" else 1, task_snapshot_sha256=digest(proposal), protected_authority_sha256=digest(proposal))
            write_json(session_path(current), next_session); record_runtime_guard(current, history, state_path, state, "developer")
            print(json.dumps({"outcome":"success", "task_id":state["task_id"], "attempt":state["attempt"], "attempt_id":attempt_id, "next_action":"trigger developer --ready", "dispatch":"not attempted"})); preserve_lock = False; return 0
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal("rollover persistence incomplete: " + str(error), recovery="preserve the lock and all evidence; inspect partial publication before recovery")
    finally:
        if preserve_lock: LOCK_IDENTITIES.pop(lock, None)
        else: release_lock(lock)



def excluded_project_fingerprint(root: Path, runtime: Path) -> str:
    # Preserve secret exclusion in persisted manifests: record only one aggregate digest.
    entries = []
    for path in sorted(root.rglob("*")):
        if path == runtime or runtime in path.parents or "__pycache__" in path.parts: continue
        relative = str(path.relative_to(root))
        if not excluded(relative): continue
        info = path.lstat()
        if stat.S_ISREG(info.st_mode): value = digest(read_regular_evidence(path))
        elif stat.S_ISLNK(info.st_mode): value = "symlink:" + os.readlink(path)
        elif stat.S_ISDIR(info.st_mode): value = "directory"
        else: raise RuntimeError("unsupported excluded project evidence type")
        entries.append((relative, value))
    return digest(json.dumps(entries, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


def project_review_identity(root: Path, runtime: Path) -> dict:
    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env={**os.environ, "GIT_OPTIONAL_LOCKS":"0"})
        if result.returncode: raise RuntimeError("unable to establish Git review identity")
        return result.stdout
    return {"head":git("rev-parse", "HEAD").strip(), "status":git("status", "--porcelain"), "diff_sha256":digest(git("diff", "--binary", "HEAD").encode()), "manifest":manifest(root, runtime)}


def launch_staged_role(root: Path, config: dict, authority: Path, current: Path, history: Path, state_path: Path, name: str, launcher=launch_iterm_staged_role) -> int:
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error))
    try:
        try:
            if name not in ("developer", "reviewer"): raise RuntimeError("only developer or reviewer can be launched")
            state = load_saved_state(state_path, config); session = load_supervised_session(current)
            verify_active_policy(root, config, current, state)
            if os.path.lexists(current / "proposal_stop.json"): raise RuntimeError("human stopped this proposal decision")
            if state.get("status") != "RUNNING" or session.get("launch_mode") != "coordinator_only" or state.get("active_iteration") != state["iteration"] + 1: raise RuntimeError("no eligible active staged run")
            expected_state = "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING" if name == "developer" else "DEVELOPER_ACCEPTED_STAGED_LAUNCH_PENDING"
            expected_phase = "coordinator_initial" if name == "developer" else "developer"
            if session.get("state") != expected_state or session.get("phase") != expected_phase or state.get("phase") != expected_phase: raise RuntimeError("role launch is not eligible in current state")
            verify_protected_authorities(authority, project_path(root, config["approval_record"]), state)
            validate_snapshot(root, authority, current, config, state)
            verify_runtime_guard(current, history, state_path, state)
            if (current / f".{name}.json").exists() or (current / f".{name}.json").is_symlink(): raise RuntimeError("stale role output exists before launch")
            tabs = json.loads(tab_state(current).read_text(encoding="utf-8")); roles = tabs.get("roles") if isinstance(tabs, dict) else None
            expected_roles = ["coordinator"] if name == "developer" else ["coordinator", "developer"]
            if not isinstance(roles, list) or not all(isinstance(item, dict) for item in roles) or [item.get("role") for item in roles] != expected_roles: raise RuntimeError("role tab evidence is inconsistent or already exists")
            window = roles[0].get("window")
            if not isinstance(window, str) or not window or not isinstance(session.get("tab"), dict) or session["tab"].get("window") != window or any(item.get("window") != window or not all(isinstance(item.get(key), str) and item[key] for key in ("tab", "session")) for item in roles): raise RuntimeError("Coordinator window identity is inconsistent")
            baseline_bytes = (current / "baseline.json").read_bytes(); baseline = json.loads(baseline_bytes)
            if not isinstance(baseline, dict) or not isinstance(baseline.get("head"), str) or not isinstance(baseline.get("manifest"), dict) or digest(baseline_bytes) != session.get("baseline_sha256"): raise RuntimeError("baseline evidence is malformed or changed")
            if name == "developer":
                artifact = current / ".coordinator.json"
                if artifact.is_symlink() or not artifact.is_file() or digest(read_regular_evidence(artifact)) != session.get("accepted_coordinator_sha256"): raise RuntimeError("accepted Coordinator evidence changed")
                head, base = clean_baseline(root, runtime_root(current, history, state_path))
                if {"head":head, "manifest":base} != baseline or excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != state.get("protected_excluded_sha256"): raise RuntimeError("clean baseline differs from the recorded baseline")
            else:
                if any((current / item).is_symlink() for item in (".developer.json", "dev_report.md", "review_identity.json", "baseline.json")): raise RuntimeError("Developer evidence is a symbolic link")
                record = json.loads((current / "review_identity.json").read_text(encoding="utf-8"))
                if not isinstance(record, dict): raise RuntimeError("review identity is malformed")
                if record.get("baseline_sha256") != digest(baseline_bytes) or record.get("report_sha256") != digest((current / "dev_report.md").read_bytes()) or record.get("artifact_sha256") != digest(read_regular_evidence(current / ".developer.json")) or record.get("project") != project_review_identity(root, runtime_root(current, history, state_path)) or record.get("excluded_sha256") != excluded_project_fingerprint(root, runtime_root(current, history, state_path)): raise RuntimeError("accepted Developer evidence or review diff changed")
            spec = tab_spec(root, config, name, production=True); spec["window"] = window
            spec["handoff"] = f"Configured task snapshot: {current / 'authoritative_task.md'}; read the effective workflow policy: {current / 'workflow_policy.json'}; policy decisions: {decision_guidance(verify_active_policy(root, config, current, state))}; current directory: {current}; your owned report: {current / ('.' + name + '.json')}; Developer report: {current / 'dev_report.md'}; Reviewer report: {current / 'review_report.md'}."
            if launcher is launch_iterm_staged_role: bridge_environment_preflight()
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal(str(error), "stale_or_mismatched_task_state")
        try:
            session["state"] = "PREPARING_" + name.upper() + "_DELIVERY"; write_json(session_path(current), session)
            observation = launcher(spec)
            if not lock_owned(lock): raise RuntimeError("controller lock ownership changed during delivery")
            if not isinstance(observation, dict) or observation.get("window") != window or observation.get("result") != "role_delivery_confirmed" or not all(isinstance(observation.get(key), str) and observation[key] for key in ("window", "tab", "session")) or any(observation.get("tab") == item["tab"] or observation.get("session") == item["session"] for item in roles): raise RuntimeError("role delivery confirmation is incomplete or duplicates an existing tab")
            roles.append({"role":name, "title":spec["title"], "host":"iterm2", **{key:observation[key] for key in ("window", "tab", "session")}}); write_json(tab_state(current), tabs)
            state["phase"] = name; write_json(state_path, state)
            session.update(phase=name, state="WAITING_FOR_HUMAN"); write_json(session_path(current), session)
            record_runtime_guard(current, history, state_path, state, name)
            print(json.dumps({"outcome":"success", "phase":name, "configured_roles":list(ROLE_ORDER), "roles_started":[item["role"] for item in roles], "next_action":next_action(name), "window":window, "tab":observation["tab"], "session":observation["session"]}))
            return 0
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal("role preparation or delivery incomplete: " + str(error), recovery="preserve evidence, inspect any partial tab and use a fresh authorized run", delivery="uncertain", partial_effects="preparation or physical tab effects may already exist")
    finally: release_lock(lock)



def ready_developer(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, attempt_id: str, delivery_id: str | None = None) -> int:
    lock = state_path.parent / "orchestrate.lock"
    try:
        if os.path.lexists(lock): raise RuntimeError("controller lock exists; wait for the control command to finish or inspect recovery evidence")
        state = load_saved_state(state_path, config); session = load_supervised_session(current)
        if session.get("launch_mode") != "coordinator_only" or not session.get("rollover_project") or state.get("status") != "RUNNING" or state.get("phase") != "developer" or session.get("phase") != "developer" or session.get("state") != "WAITING_FOR_HUMAN" or state.get("active_iteration") != state["iteration"] + 1: raise RuntimeError("no eligible rollover Developer attempt")
        if not isinstance(attempt_id, str) or not re.fullmatch(r"[0-9a-f]{32}", attempt_id) or session.get("attempt_id") != attempt_id: raise RuntimeError("rollover attempt identity is stale")
        if os.path.lexists(current / "proposal_stop.json"): raise RuntimeError("human stopped this proposal decision")
        verify_active_policy(root, config, current, state); verify_runtime_guard(current, history, state_path, state)
        if state["evidence_guard"].get("allowed_role") != "developer": raise RuntimeError("runtime guard does not bind Developer")
        verify_protected_authorities(authority, approval_record, state); validate_snapshot(root, authority, current, config, state)
        if session.get("task_snapshot_sha256") != state["task_snapshot_sha256"]: raise RuntimeError("session snapshot changed")
        approval = json.loads(read_regular_evidence(current / "approval_evidence.json"))
        if not isinstance(approval, dict) or approval.get("proposal_sha256") != state["task_snapshot_sha256"] or approval.get("kind") != "human_control_terminal_approval": raise RuntimeError("rollover approval evidence is inconsistent")
        baseline = read_regular_evidence(current / "baseline.json")
        if digest(baseline) != session.get("baseline_sha256") or session["rollover_project"] != project_review_identity(root, runtime_root(current, history, state_path)) or excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != state.get("protected_excluded_sha256"): raise RuntimeError("Developer carried-forward baseline changed")
        if digest(read_regular_evidence(current / ".coordinator.json")) != session.get("accepted_coordinator_sha256"): raise RuntimeError("Coordinator evidence changed")
        tabs = json.loads(read_regular_evidence(tab_state(current))); roles = tabs.get("roles") if isinstance(tabs, dict) else None
        if not isinstance(roles, list) or not all(isinstance(item, dict) for item in roles) or [item.get("role") for item in roles] != list(ROLE_ORDER) or any(not all(isinstance(item.get(k), str) and item[k] for k in ("window", "tab", "session")) or item["window"] != roles[0]["window"] for item in roles) or any(roles[0].get(k) != session.get("tab", {}).get(k) for k in ("window", "tab", "session")): raise RuntimeError("recorded role destinations are inconsistent")
        output_name = session.get("report_slots", {}).get("developer")
        if output_name != ".developer-" + attempt_id + ".json" or os.path.lexists(current / output_name): raise RuntimeError("Developer report slot is stale or occupied")
        attempts = session.get("trigger_attempts", {})
        if not isinstance(attempts, dict): raise RuntimeError("trigger evidence is invalid")
        delivery = attempts.get("developer")
        if delivery is None:
            if delivery_id is not None: raise RuntimeError("delivery identity has no recorded trigger")
        elif not isinstance(delivery, dict) or delivery.get("status") != "confirmed" or not delivery_id or delivery.get("id") != delivery_id or delivery.get("iteration") != state["active_iteration"] or delivery.get("config_sha256") != state["config_sha256"] or delivery.get("snapshot_sha256") != state["task_snapshot_sha256"] or delivery.get("destination") != {key:roles[1][key] for key in ("window", "tab", "session")}: raise RuntimeError("delivery is uncertain, stale, or does not match the recorded Developer trigger")
        if os.path.lexists(lock) or load_saved_state(state_path, config) != state or load_supervised_session(current) != session: raise RuntimeError("controller state or lock changed during readiness check")
        print(json.dumps({"outcome":"success", "ready":True, "attempt_id":attempt_id, "delivery_id":delivery_id, "snapshot_sha256":state["task_snapshot_sha256"], "report":str(current / output_name)})); return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
        return refusal(str(error), "stale_or_mismatched_task_state", recovery="do not begin work or write a report; inspect the lock, attempt and preserved evidence")


def trigger_staged_role(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, name: str, ready: bool, sender=deliver_iterm_trigger) -> int:
    if not ready: return refusal("human readiness confirmation --ready is required", recovery="inspect the intended Codex input prompt before confirming readiness")
    if name not in ROLE_ORDER: return refusal("trigger requires coordinator, developer, or reviewer")
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error))
    try:
        try:
            state = load_saved_state(state_path, config); session = load_supervised_session(current)
            verify_active_policy(root, config, current, state)
            if os.path.lexists(current / "proposal_stop.json"): raise RuntimeError("human stopped this proposal decision")
            if session.get("launch_mode") != "coordinator_only": raise RuntimeError("not an eligible staged run")
            final = name == "coordinator"
            if final:
                if state.get("status") != "READY" or session.get("phase") != "coordinator_review" or session.get("state") != "COMPLETED_COORDINATOR_REVIEW": raise RuntimeError("Coordinator trigger requires a completed iteration")
                verify_completion_guard(root, current, history, state_path, session)
                iteration = state["iteration"]; archived = history / f"{iteration:03d}"
                if json.loads(read_regular_evidence(archived / "state.json")) != state or not (archived / "review_report.md").is_file(): raise RuntimeError("completed archive is inconsistent")
            else:
                if state.get("status") != "RUNNING" or state.get("phase") != name or session.get("phase") != name or session.get("state") != "WAITING_FOR_HUMAN" or state.get("active_iteration") != state["iteration"] + 1: raise RuntimeError("role trigger is not eligible or delivery is uncertain")
                verify_runtime_guard(current, history, state_path, state)
                if state["evidence_guard"].get("allowed_role") != name: raise RuntimeError("runtime guard does not bind the active role")
                iteration = state["active_iteration"]
            verify_protected_authorities(authority, approval_record, state)
            validate_snapshot(root, authority, current, config, state)
            attempts = session.get("trigger_attempts", {})
            if not isinstance(attempts, dict): raise RuntimeError("trigger attempt metadata is invalid")
            if name in attempts: raise RuntimeError("a trigger was already attempted; inspect delivery and do not resend")
            output = current / ("coordinator_summary.md" if final else session.get("report_slots", {}).get(name, f".{name}.json"))
            if os.path.lexists(output): raise RuntimeError("role output already exists; refusing a duplicate trigger")
            tabs = json.loads(read_regular_evidence(tab_state(current))); roles = tabs.get("roles") if isinstance(tabs, dict) else None
            expected = list(ROLE_ORDER) if final or name == "reviewer" or session.get("rollover_project") else ["coordinator", "developer"]
            if not isinstance(roles, list) or not all(isinstance(item, dict) for item in roles) or [item.get("role") for item in roles] != expected: raise RuntimeError("recorded role tabs are inconsistent")
            dest = next(item for item in roles if item["role"] == name)
            if not all(isinstance(dest.get(key), str) and dest[key] for key in ("window", "tab", "session")) or not isinstance(session.get("tab"), dict) or any(roles[0].get(key) != session["tab"].get(key) for key in ("window", "tab", "session")) or any(item.get("window") != roles[0]["window"] for item in roles): raise RuntimeError("recorded destination is inconsistent")
            baseline = read_regular_evidence(current / "baseline.json")
            if digest(baseline) != session.get("baseline_sha256"): raise RuntimeError("baseline evidence changed")
            if name == "developer":
                if digest(read_regular_evidence(current / ".coordinator.json")) != session.get("accepted_coordinator_sha256"): raise RuntimeError("accepted Coordinator evidence changed")
                if session.get("rollover_project"):
                    if session["rollover_project"] != project_review_identity(root, runtime_root(current, history, state_path)): raise RuntimeError("Developer carried-forward baseline changed")
                else:
                    head, base = clean_baseline(root, runtime_root(current, history, state_path))
                    if {"head":head, "manifest":base} != json.loads(baseline): raise RuntimeError("Developer baseline changed")
                if excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != state.get("protected_excluded_sha256"): raise RuntimeError("Developer baseline changed")
            elif name == "reviewer":
                identity = json.loads(read_regular_evidence(current / "review_identity.json"))
                if not isinstance(identity, dict) or identity.get("baseline_sha256") != digest(baseline) or identity.get("artifact_sha256") != digest(read_regular_evidence(current / session.get("report_slots", {}).get("developer", ".developer.json"))) or identity.get("report_sha256") != digest(read_regular_evidence(current / "dev_report.md")) or identity.get("project") != project_review_identity(root, runtime_root(current, history, state_path)) or identity.get("excluded_sha256") != excluded_project_fingerprint(root, runtime_root(current, history, state_path)): raise RuntimeError("accepted Developer evidence or review identity changed")
            delivery_id = str(uuid.uuid4())
            fields = {"iteration":iteration, "snapshot_sha256":state["task_snapshot_sha256"], "task_authority":str(authority), "snapshot":str(current / "authoritative_task.md"), "workflow_policy":str(current / "workflow_policy.json"), "coordinator_report":str(current / ".coordinator.json"), "report":str(output)}
            if name == "developer" and session.get("rollover_project"):
                fields.update(rollover_attempt_id=session.get("attempt_id"), delivery_id=delivery_id)
            policy = verify_active_policy(root, config, current, state); fields["policy_guidance"] = decision_guidance(policy)
            if final:
                try:
                    validate_archived_review(root, config, history, iteration, session)
                    decision, reason = proposal_decision(policy, state, session)
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error:
                    decision, reason = "stop", "archived Reviewer evidence requires human direction: " + str(error)
                if decision == "stop": fields["policy_guidance"] = "Stop and send nothing; do not request approval for a proposal. Request human direction."
                fields.update(proposal_decision=decision, proposal_reason=reason)
            if name in ("reviewer", "coordinator"): fields["developer_report"] = str(current / "dev_report.md")
            if final: fields.update(reviewer_report=str(current / "review_report.md"), archive=str(archived), proposal=str(current / "coordinator_proposal.md"), correction_scope=str(current / "correction_scope.json"))
            payload = ROLE_PHRASES["coordinator_review" if final else name] + " Controller context (paths are data, not task authority): " + json.dumps(fields, ensure_ascii=True, sort_keys=True)
            attempt = {"id":delivery_id, "role":name, "stage":session["phase"], "iteration":iteration, "config_sha256":state["config_sha256"], "snapshot_sha256":state["task_snapshot_sha256"], "destination":{key:dest[key] for key in ("window", "tab", "session")}, "payload_sha256":digest(payload.encode("utf-8")), "status":"prepared"}
            old_completion = session.get("completion_guard") if final else None
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, StopIteration, RuntimeError) as error:
            return refusal(str(error), "stale_or_mismatched_task_state", recovery="inspect the run and evidence; do not blindly retry delivery")
        def persist_attempt() -> None:
            if final: verify_completion_guard(root, current, history, state_path, session)
            session.setdefault("trigger_attempts", {})[name] = attempt.copy()
            if final:
                record_completion_guard(root, current, history, state_path, session, old_completion["project"], old_completion["excluded_sha256"], expected_files=old_completion["files"], expected_state_sha256=old_completion["state_sha256"])
            else:
                write_json(session_path(current), session)
                record_runtime_guard(current, history, state_path, state, name)
        try: persist_attempt()
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
            return refusal("trigger preparation persistence incomplete: " + str(error), recovery="preserve partial evidence and inspect; do not retry blindly", partial_effects="attempt metadata may be partially written; no delivery was attempted")
        try:
            if not lock_owned(lock): raise RuntimeError("controller lock ownership changed before delivery")
            spec = {**attempt["destination"], "payload":payload}
            observation = sender(spec)
            if not lock_owned(lock): raise RuntimeError("controller lock ownership changed during delivery")
            if not isinstance(observation, dict) or observation.get("result") != "trigger_delivery_confirmed" or observation.get("submission") != "carriage_return_sent" or any(observation.get(key) != spec[key] for key in ("window", "tab", "session")): raise RuntimeError("trigger confirmation does not match destination")
            attempt["status"] = "confirmed"; persist_attempt()
        except Exception as error:
            attempt["status"] = "uncertain"
            if lock_owned(lock):
                try: persist_attempt()
                except (OSError, ValueError, TypeError, KeyError, RuntimeError): pass
            label = update_role_label(dest, name, "delivery uncertain") if lock_owned(lock) else {"status":"skipped", "reason":"controller lock ownership changed"}
            return refusal("trigger delivery or confirmation is uncertain: " + str(error), recovery="inspect the recorded tab and attempt evidence; do not resend or repeat the phrase blindly", delivery="uncertain", label=label)
        label = update_role_label(dest, name, "trigger sent · awaiting summary" if final else "trigger sent · awaiting report")
        print(json.dumps({"outcome":"success", "role":name, "iteration":iteration, "attempt_id":attempt["id"], "delivery":"confirmed", "submission":"carriage_return_sent", "role_output":"not_checked", "label":label, "next_action":"wait for the role's final summary" if final else "wait for the role report, then accept " + name}))
        return 0
    finally: release_lock(lock)


def supervised_stop(current: Path, history: Path, state_path: Path, state: dict, session: dict | None, category: str, reason: str) -> int:
    iteration = state.get("active_iteration", state.get("iteration", 0) + 1)
    phase = displayed_role(session["phase"]) if session is not None else "coordinator"
    state.update(active_iteration=iteration, phase=phase, config_sha256=state.get("config_sha256"))
    return human_stop(current, history, state_path, iteration, state, category, reason)


def terminal_stop_result(current: Path, state: dict) -> dict:
    evidence = current / "human_stop.json"
    try: stop = json.loads(evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError): raise RuntimeError("terminal controller stop evidence is missing or unreadable")
    if not isinstance(stop, dict) or stop.get("state") != "HUMAN_REQUIRED" or not isinstance(stop.get("category"), str) or not isinstance(stop.get("reason"), str): raise RuntimeError("terminal controller stop evidence is invalid")
    return {"outcome":"terminal", "state":"HUMAN_REQUIRED", "category":stop.get("category"), "reason":stop.get("reason"), "stop_evidence":str(evidence), "recovery":"inspect the existing stop evidence and recover with a fresh authorized start; do not accept a role from this terminal state"}


def terminal_accept_stop(current: Path, history: Path, state_path: Path, state: dict, session: dict | None, category: str, reason: str) -> int:
    iteration = state.get("active_iteration")
    if type(iteration) is not int or iteration <= state.get("iteration", -1):
        return refusal("cannot identify active run for terminalization", "stale_or_mismatched_task_state")
    if (history / f"{iteration:03d}").exists() or (current / "human_stop.json").exists():
        return refusal("terminal persistence conflict; existing evidence preserved", recovery="preserve existing evidence and resolve the conflict before a fresh authorized run", partial_effects="no terminal persistence attempted")
    try:
        supervised_stop(current, history, state_path, state, session, category, reason)
    except (OSError, RuntimeError, ValueError) as error:
        return refusal("terminal persistence incomplete: " + str(error), recovery="preserve all current and history evidence and resolve persistence before a fresh authorized run", partial_effects="stop evidence, archive or state may have been partially written")
    print(json.dumps(terminal_stop_result(current, state)))
    return 2


def terminal_start_stop(current: Path, history: Path, state_path: Path, iteration: int, state: dict, category: str, reason: str) -> int:
    human_stop(current, history, state_path, iteration, state, category, reason)
    print(json.dumps(terminal_stop_result(current, state)))
    return 2


def not_ready_result(current: Path, name: str) -> dict:
    return {"outcome":"refusal", "state":"HUMAN_REQUIRED", "category":"failed_or_incomplete_validation", "reason":f"{name} output is not ready", "expected_evidence":str(current / f".{name}.json"), "recovery":f"wait for the active {name} role to write its final structured artifact, then rerun accept {name}; no controller state was changed"}


def supervised_accept(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, name: str) -> int:
    try: lock = acquire_lock(state_path.parent)
    except (OSError, RuntimeError) as error: return refusal(str(error), recovery="wait for the lock owner; remove a lock only after verifying it is stale")
    try: return _supervised_accept_locked(root, config, authority, approval_record, current, history, state_path, name)
    finally: release_lock(lock)


def _supervised_accept_locked(root: Path, config: dict, authority: Path, approval_record: Path, current: Path, history: Path, state_path: Path, name: str) -> int:
    try: state = load_saved_state(state_path, config)
    except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
    if state.get("status") == "HUMAN_REQUIRED":
        try: result = terminal_stop_result(current, state)
        except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
        print(json.dumps(result))
        return 2
    if (current / "human_stop.json").exists() or (current / "human_stop.json").is_symlink():
        return refusal("existing stop evidence conflicts with nonterminal state", "stale_or_mismatched_task_state")
    if state.get("status") == "RUNNING" and "evidence_guard" in state:
        try:
            verify_runtime_guard(current, history, state_path, state)
            verify_protected_authorities(authority, approval_record, state)
        except (OSError, ValueError, TypeError, RuntimeError) as error: return refusal(str(error), "unsafe_or_unexpected_diff")
    try: session = load_supervised_session(current)
    except RuntimeError as error:
        if state.get("phase") == "coordinator_initial" and state.get("status") == "RUNNING" and type(state.get("active_iteration")) is int:
            return terminal_accept_stop(current, history, state_path, state, None, "stale_or_mismatched_task_state", str(error))
        return refusal(str(error), "stale_or_mismatched_task_state")
    try: verify_active_policy(root, config, current, state)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
    if os.path.lexists(current / "proposal_stop.json"): return refusal("human stopped this proposal decision")
    phase = session["phase"]
    if session.get("launch_mode") == "coordinator_only" and str(session.get("state", "")).startswith("PREPARING_"):
        return refusal("role delivery is uncertain; preserve preparation evidence and inspect the tab before a fresh authorized run")
    if session.get("launch_mode") == "coordinator_only" and state.get("status") == "RUNNING" and state.get("phase") != phase:
        return refusal("staged session and saved state differ; preserve evidence for recovery", "stale_or_mismatched_task_state")
    if session.get("launch_mode") == "coordinator_only" and phase == "coordinator_review":
        return refusal("iteration is complete; Coordinator summary cannot start a new run")
    if session.get("launch_mode") == "coordinator_only" and ((phase == "coordinator_initial" and name == "coordinator") or (phase == "reviewer" and name == "reviewer")):
        try:
            if phase == "coordinator_initial":
                baseline = json.loads(read_regular_evidence(current / "baseline.json"))
                head, base = clean_baseline(root, runtime_root(current, history, state_path))
                if {"head":head, "manifest":base} != baseline or excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != state.get("protected_excluded_sha256"): raise RuntimeError("Coordinator changed the project baseline")
            else:
                identity = json.loads(read_regular_evidence(current / "review_identity.json"))
                if not isinstance(identity, dict) or identity.get("project") != project_review_identity(root, runtime_root(current, history, state_path)) or identity.get("excluded_sha256") != excluded_project_fingerprint(root, runtime_root(current, history, state_path)): raise RuntimeError("Reviewer changed the frozen project identity")
        except (OSError, UnicodeError, ValueError, TypeError, RuntimeError) as error: return refusal(str(error), "unsafe_or_unexpected_diff")
    if state.get("phase") == "coordinator_initial":
        if state.get("status") != "RUNNING" or state.get("phase") != "coordinator_initial" or type(state.get("active_iteration")) is not int:
            return refusal("Coordinator run identity is not trustworthy or delivery is incomplete", "stale_or_mismatched_task_state")
        try:
            if session.get("launch_mode") != "coordinator_only" or phase != "coordinator_initial" or session.get("state") not in ("WAITING_FOR_HUMAN", "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING") or session.get("task_snapshot_sha256") != state.get("task_snapshot_sha256"):
                raise RuntimeError("Coordinator session and saved state are inconsistent")
            validate_snapshot(root, authority, current, config, state)
            tabs = json.loads(tab_state(current).read_text(encoding="utf-8"))
            identifiers = session.get("tab")
            if not isinstance(identifiers, dict) or not all(isinstance(identifiers.get(k), str) and identifiers[k] for k in ("window", "tab", "session")) or not isinstance(tabs, dict) or not isinstance(tabs.get("roles"), list) or len(tabs["roles"]) != 1 or not isinstance(tabs["roles"][0], dict) or any(tabs["roles"][0].get(k) != identifiers[k] for k in ("window", "tab", "session")):
                raise RuntimeError("Coordinator tab evidence is inconsistent")
        except (OSError, UnicodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
            return terminal_accept_stop(current, history, state_path, state, session, "stale_or_mismatched_task_state", str(error))
    if session.get("launch_mode") == "coordinator_only" and phase in ("developer", "reviewer"):
        if phase == "developer" and session.get("state") == "DEVELOPER_ACCEPTED_STAGED_LAUNCH_PENDING": return refusal("Developer evidence already accepted; launch reviewer")
        if state.get("status") != "RUNNING" or state.get("phase") != phase or session.get("state") != "WAITING_FOR_HUMAN":
            return refusal("role is not active or delivery is uncertain", "stale_or_mismatched_task_state")
        try:
            validate_snapshot(root, authority, current, config, state)
            tabs = json.loads(tab_state(current).read_text(encoding="utf-8")); roles = tabs["roles"]
            expected_roles = list(ROLE_ORDER) if session.get("rollover_project") else list(ROLE_ORDER[:(2 if phase == "developer" else 3)])
            if not isinstance(roles, list) or [entry["role"] for entry in roles] != expected_roles or any(not all(isinstance(entry.get(key), str) and entry[key] for key in ("window", "tab", "session")) for entry in roles) or any(entry["window"] != roles[0]["window"] for entry in roles): raise RuntimeError("role tab evidence is inconsistent")
        except (OSError, UnicodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
            return terminal_accept_stop(current, history, state_path, state, session, "stale_or_mismatched_task_state", str(error))
    if displayed_role(phase) != name:
        return refusal("role is not the permitted supervised handoff", "stale_or_mismatched_task_state", recovery=f"accept {displayed_role(phase)} when its evidence is ready")
    if session.get("launch_mode") == "coordinator_only":
        try:
            verify_runtime_guard(current, history, state_path, state)
            if name == "coordinator":
                baseline = json.loads(read_regular_evidence(current / "baseline.json"))
                head, base = clean_baseline(root, runtime_root(current, history, state_path))
                if {"head":head, "manifest":base} != baseline or excluded_project_fingerprint(root, runtime_root(current, history, state_path)) != state.get("protected_excluded_sha256"): raise RuntimeError("Coordinator changed the project baseline")
        except (OSError, UnicodeError, ValueError, TypeError, RuntimeError) as error:
            return refusal(str(error), "unsafe_or_unexpected_diff")
    output = current / session.get("report_slots", {}).get(name, f".{name}.json")
    try: output_stat = output.lstat()
    except FileNotFoundError:
        print(json.dumps(not_ready_result(current, name)))
        return 2
    except OSError as error:
        return terminal_accept_stop(current, history, state_path, state, session, "failed_or_incomplete_validation", "cannot inspect role output: " + str(error))
    if stat.S_ISLNK(output_stat.st_mode):
        return terminal_accept_stop(current, history, state_path, state, session, "failed_or_incomplete_validation", f"{name.title()} output is a symbolic link; expected regular evidence")
    try:
        if not output.is_file(): raise RuntimeError("structured role report is unreadable or not a regular file")
        output_bytes = read_regular_evidence(output)
        payload = json.loads(output_bytes)
        result = validate_output(root, config, name, payload)
        if name == "coordinator":
            if result["status"] == "HUMAN_REQUIRED":
                category = result.get("human_category") or "unresolved_requirement"; reason = result.get("human_reason") or result["summary"]
                return terminal_accept_stop(current, history, state_path, state, session, category, reason)
            if result.get("next_prompt") not in (None, "", authority.read_text(encoding="utf-8")):
                print(json.dumps({"outcome":"refusal", "state":"HUMAN_REQUIRED", "category":"unresolved_requirement", "reason":"Coordinator proposed a changed task", "recovery":"preserve the proposal and authorize a fresh run for any changed task"}))
                return 2
            if result["status"] != "CONTINUE":
                return terminal_accept_stop(current, history, state_path, state, session, "failed_or_incomplete_validation", "coordinator output requires human approval or stop")
            if session.get("launch_mode") == "coordinator_only":
                validate_snapshot(root, authority, current, config, state)
                if session.get("state") == "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING" and session.get("accepted_coordinator_sha256") != digest(output_bytes):
                    return refusal("accepted Coordinator evidence changed", "stale_or_mismatched_task_state")
                if session.get("state") != "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING":
                    session["state"] = "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING"
                    session["accepted_coordinator_sha256"] = digest(output_bytes)
                    session["baseline_sha256"] = digest(read_regular_evidence(current / "baseline.json"))
                    try:
                        write_json(session_path(current), session)
                        record_runtime_guard(current, history, state_path, state, None)
                    except OSError as error: return refusal("Coordinator acceptance persistence incomplete: " + str(error), partial_effects="session evidence may be partially written")
                label = update_role_label(identifiers, "coordinator", "accepted · waiting for Developer")
                print(json.dumps({"outcome":"success", "title":"accepted coordinator", "phase":"coordinator_initial", "result":"Coordinator accepted; no additional role was launched", "roles_started":["coordinator"], "next_action":"launch developer", "label":label}))
                return 0
            head, base = clean_baseline(root, runtime_root(current, history, state_path))
            iteration = state.get("iteration", 0) + 1; state.update(active_iteration=iteration, phase="developer", status="RUNNING", config_sha256=config["_sha256"], baseline={"head": head, "manifest": base})
            meta = snapshot_authority(root, authority, approval_record, current, config, state)
            state.update(task_snapshot_sha256=meta["sha256"]); write_json(current / "baseline.json", state.pop("baseline")); session.update(phase="developer", task_snapshot_sha256=meta["sha256"]); write_json(state_path, state)
        elif name == "developer":
            validate_snapshot(root, authority, current, config, state)
            if result["status"] != "DONE":
                return terminal_accept_stop(current, history, state_path, state, session, result.get("human_category") or "failed_or_incomplete_validation", result["summary"])
            if session.get("launch_mode") == "coordinator_only":
                try:
                    if any((current / name).exists() or (current / name).is_symlink() for name in ("dev_report.md", "after_developer.json", "review_identity.json")): raise RuntimeError("Developer acceptance evidence already exists")
                    baseline_bytes = read_regular_evidence(current / "baseline.json"); baseline = json.loads(baseline_bytes)
                    if digest(baseline_bytes) != session.get("baseline_sha256"): raise RuntimeError("baseline evidence changed")
                    project = project_review_identity(root, runtime_root(current, history, state_path))
                    if project["head"] != baseline["head"]: raise RuntimeError("Git HEAD changed during Developer work")
                    (current / "dev_report.md").write_text(report("Developer report", result), encoding="utf-8")
                    write_json(current / "after_developer.json", project["manifest"])
                    write_json(current / "review_identity.json", {"baseline_sha256":digest(baseline_bytes), "artifact_sha256":digest(output_bytes), "report_sha256":digest((current / "dev_report.md").read_bytes()), "excluded_sha256":excluded_project_fingerprint(root, runtime_root(current, history, state_path)), "project":project})
                    if session.get("rollover_project"):
                        session.update(phase="reviewer", state="WAITING_FOR_HUMAN"); state["phase"] = "reviewer"
                        write_json(session_path(current), session); record_runtime_guard(current, history, state_path, state, "reviewer")
                    else:
                        session["state"] = "DEVELOPER_ACCEPTED_STAGED_LAUNCH_PENDING"; write_json(session_path(current), session); record_runtime_guard(current, history, state_path, state, None)
                except (OSError, ValueError, KeyError, RuntimeError) as error: return refusal("Developer acceptance incomplete: " + str(error), partial_effects="report or review identity may be partially written")
                labels = {"developer":update_role_label(next(entry for entry in roles if entry["role"] == "developer"), "developer", "accepted · waiting for Reviewer"), "coordinator":update_role_label(next(entry for entry in roles if entry["role"] == "coordinator"), "coordinator", "accepted · waiting for Reviewer")}
                print(json.dumps({"outcome":"success", "phase":session["phase"], "roles_started":[item["role"] for item in roles], "next_action":"trigger reviewer --ready" if session.get("rollover_project") else "launch reviewer", "labels":labels})); return 0
            (current / "dev_report.md").write_text(report("Developer report", result), encoding="utf-8"); write_json(current / "after_developer.json", manifest(root, runtime_root(current, history, state_path))); state["phase"] = "reviewer"; session["phase"] = "reviewer"; write_json(state_path, state)
        else:
            validate_snapshot(root, authority, current, config, state)
            escalation = review_escalation(result)
            if escalation is not None:
                return terminal_accept_stop(current, history, state_path, state, session, *escalation)
            policy = verify_active_policy(root, config, current, state) if session.get("launch_mode") == "coordinator_only" else None
            decision = policy["decisions"].get(result["verdict"], "stop") if policy else None
            actionable_changes = (decision == "correction" and any(isinstance(item, str) and item.strip() for item in result["findings"]))
            if (decision != "next_task" if policy else result["verdict"] != "APPROVED") and not actionable_changes:
                return terminal_accept_stop(current, history, state_path, state, session, result.get("human_category") or "failed_or_incomplete_validation", result.get("human_reason") or result["summary"])
            if session.get("launch_mode") == "coordinator_only":
                try:
                    if any((current / name).is_symlink() for name in (".developer.json", "dev_report.md", "review_identity.json", "baseline.json")): raise RuntimeError("review evidence is a symbolic link")
                    if (current / "review_report.md").exists() or (current / "review_report.md").is_symlink(): raise RuntimeError("Reviewer report evidence already exists")
                    identity = json.loads((current / "review_identity.json").read_text(encoding="utf-8")); baseline_bytes = (current / "baseline.json").read_bytes()
                    if not isinstance(identity, dict): raise RuntimeError("review identity is malformed")
                    if identity.get("baseline_sha256") != digest(baseline_bytes) or identity.get("report_sha256") != digest((current / "dev_report.md").read_bytes()) or identity.get("artifact_sha256") != digest(read_regular_evidence(current / session.get("report_slots", {}).get("developer", ".developer.json"))) or identity.get("project") != project_review_identity(root, runtime_root(current, history, state_path)) or identity.get("excluded_sha256") != excluded_project_fingerprint(root, runtime_root(current, history, state_path)): raise RuntimeError("reviewed project or Developer evidence changed")
                    (current / "review_report.md").write_text(report("Reviewer report", result), encoding="utf-8")
                    session.update(phase="coordinator_review", state="COMPLETED_COORDINATOR_REVIEW", review_verdict=result["verdict"]); write_json(session_path(current), session)
                    state["last_authority_sha256"] = state["task_snapshot_sha256"]
                    finish(current, history, state_path, state["active_iteration"], state, "READY")
                    record_completion_guard(root, current, history, state_path, session, identity["project"], identity["excluded_sha256"])
                except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal("completion persistence or review verification incomplete: " + str(error), partial_effects="review or archive evidence may be partially written")
                labels = {"reviewer":update_role_label(next(entry for entry in roles if entry["role"] == "reviewer"), "reviewer", "accepted · waiting for Coordinator"), "coordinator":update_role_label(next(entry for entry in roles if entry["role"] == "coordinator"), "coordinator", "waiting for coordinate latest")}
                print(json.dumps({"outcome":"success", "phase":"coordinator_review", "review_verdict":result["verdict"], "roles_started":list(ROLE_ORDER), "next_action":"coordinator: coordinate latest", "history":str(history / f"{state['iteration']:03d}"), "labels":labels})); return 0
            (current / "review_report.md").write_text(report("Reviewer report", result), encoding="utf-8"); session["phase"] = "coordinator_review"; session["task_snapshot_sha256"] = state["task_snapshot_sha256"]; write_json(session_path(current), session)
            state["last_authority_sha256"] = state["task_snapshot_sha256"]; finish(current, history, state_path, state["active_iteration"], state, "READY")
            print_session(root, config, current, session["phase"], f"accepted {name}"); return 0
    except (OSError, UnicodeError, RuntimeError, RoleFailure, json.JSONDecodeError) as error:
        category = "indeterminate_write_invocation" if name == "developer" else "failed_or_incomplete_validation"
        return terminal_accept_stop(current, history, state_path, state, session, category, str(error))
    write_json(session_path(current), session); print_session(root, config, current, session["phase"], f"accepted {name}"); return 0


def supervised_cycle(root: Path, config: dict, authority: Path, current: Path, history: Path, state_path: Path) -> int:
    try: state = load_saved_state(state_path, config)
    except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
    if state.get("status") == "HUMAN_REQUIRED":
        try: result = terminal_stop_result(current, state)
        except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
        print(json.dumps(result))
        return 0
    if (current / "human_stop.json").exists() or (current / "human_stop.json").is_symlink():
        return refusal("existing stop evidence conflicts with nonterminal state", "stale_or_mismatched_task_state")
    try:
        session = load_supervised_session(current)
        phase = session["phase"]
        verify_active_policy(root, config, current, state)
        if session.get("launch_mode") == "coordinator_only" or state.get("phase") == "coordinator_initial": return supervised_view(root, config, current, history, state_path, "cycle")
        if not authority.is_file(): raise RuntimeError("configured durable task authority is missing")
        if phase in ("developer", "reviewer", "coordinator_review"): validate_snapshot(root, authority, current, config, state if phase != "coordinator_review" else {"task_snapshot_sha256": session.get("task_snapshot_sha256")})
        if phase == "reviewer" and not (current / "dev_report.md").is_file(): raise RuntimeError("Developer evidence is missing")
        if phase == "coordinator_review" and not (current / "review_report.md").is_file(): raise RuntimeError("Reviewer evidence is missing")
        print_session(root, config, current, phase, "cycle"); return 0
    except (KeyError, RuntimeError, OSError, UnicodeError, json.JSONDecodeError) as error:
        return refusal(str(error), "stale_or_mismatched_task_state")



def trigger_view(session: dict, role_name: str, output: Path) -> tuple[str, str]:
    attempts = session.get("trigger_attempts", {})
    if not isinstance(attempts, dict): raise RuntimeError("invalid trigger attempt metadata")
    attempt = attempts.get(role_name)
    if attempt is not None and (not isinstance(attempt, dict) or attempt.get("status") not in ("prepared", "confirmed", "uncertain")): raise RuntimeError("invalid trigger attempt metadata")
    if attempt is not None and attempt["status"] in ("prepared", "uncertain"):
        return ("delivery_uncertain", "inspect the recorded attempt, tab and any output; do not resend or repeat the phrase blindly")
    if os.path.lexists(output):
        return ("output_present", "inspect coordinator summary; no new cycle is authorized" if role_name == "coordinator" else "accept " + role_name)
    if attempt is None: return ("awaiting_trigger", "trigger " + role_name + " --ready after checking the tab; manual phrase remains supported")
    return ("awaiting_output", "wait for the role's final summary" if role_name == "coordinator" else "wait for the role report, then accept " + role_name)


def supervised_view(root: Path, config: dict, current: Path, history: Path, state_path: Path, title: str) -> int:
    try: state = load_saved_state(state_path, config)
    except RuntimeError as error:
        if os.path.lexists(state_path.parent / "orchestrate.lock"):
            return refusal("controller lock exists and saved state cannot be verified: " + str(error), "stale_or_mismatched_task_state", recovery="preserve the lock and evidence; inspect the lock owner and torn state before any recovery")
        return refusal(str(error), "stale_or_mismatched_task_state")
    if state.get("status") == "HUMAN_REQUIRED":
        try: result = terminal_stop_result(current, state)
        except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
        print(json.dumps(result))
        return 0
    if os.path.lexists(state_path.parent / "orchestrate.lock"):
        return refusal("controller lock exists; workflow activity or recovery may be incomplete", recovery="inspect the lock owner and preserved evidence before removing a verified stale lock")
    if (current / "human_stop.json").exists() or (current / "human_stop.json").is_symlink():
        return refusal("existing stop evidence conflicts with nonterminal state", "stale_or_mismatched_task_state")
    if state.get("status") == "HUMAN_REQUIRED":
        try: result = terminal_stop_result(current, state)
        except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
        print(json.dumps(result))
        return 0
    try: session = load_supervised_session(current)
    except RuntimeError as error:
        return refusal(str(error), "stale_or_mismatched_task_state")
    try: verify_active_policy(root, config, current, state)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
    if os.path.lexists(current / "proposal_stop.json"):
        try:
            identity, _ = completed_identity(root, config, project_path(root, config["task_authority"]), project_path(root, config["approval_record"]), current, history, state_path)
            record = json.loads(read_regular_evidence(current / "proposal_stop.json"))
            if record != proposal_stop_record(current, identity): raise RuntimeError("human stop evidence is inconsistent")
            print(json.dumps({"outcome":"success", "state":"HUMAN_STOPPED", **identity, "task_id":state.get("task_id"), "task_number":state.get("task_number"), "task_limit":state.get("task_limit"), "attempt":state.get("attempt"), "attempt_limit":state.get("attempt_limit"), "next_action":"human stopped; no further dispatch"})); return 0
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
    if session.get("launch_mode") == "coordinator_only" and state.get("status") == "RUNNING":
        try: verify_runtime_guard(current, history, state_path, state)
        except (OSError, ValueError, TypeError, RuntimeError) as error: return refusal("runtime evidence or trigger persistence is incomplete: " + str(error), recovery="inspect evidence and the tab; do not resend blindly")
    if session.get("launch_mode") == "coordinator_only" and session.get("phase") in ("developer", "reviewer", "coordinator_review"):
        phase = session["phase"]; stage = session.get("state")
        if phase == "coordinator_review" and stage == "COMPLETED_COORDINATOR_REVIEW" and state.get("status") == "READY": action = "coordinator: coordinate latest"
        elif state.get("status") == "RUNNING" and state.get("phase") == phase and stage == "WAITING_FOR_HUMAN": action = next_action(phase)
        elif state.get("status") == "RUNNING" and state.get("phase") == "developer" and stage == "DEVELOPER_ACCEPTED_STAGED_LAUNCH_PENDING": action = "launch reviewer"
        else: return refusal("role delivery or completion is uncertain; inspect evidence", "stale_or_mismatched_task_state")
        try:
            tabs = json.loads(tab_state(current).read_text(encoding="utf-8")); roles = tabs["roles"]
            expected = ["coordinator", "developer"] if phase == "developer" and not session.get("rollover_project") else ["coordinator", "developer", "reviewer"]
            if not isinstance(roles, list) or [item["role"] for item in roles] != expected or any(not all(isinstance(item.get(key), str) and item[key] for key in ("window", "tab", "session")) for item in roles) or any(item["window"] != roles[0]["window"] for item in roles): raise RuntimeError("role tab evidence is inconsistent")
            validate_snapshot(root, project_path(root, config["task_authority"]), current, config, state)
            if phase == "coordinator_review":
                archived = history / f"{state['iteration']:03d}"
                if json.loads((archived / "state.json").read_text(encoding="utf-8")) != state or not (archived / "review_report.md").is_file(): raise RuntimeError("completed iteration archive is inconsistent")
                verify_completion_guard(root, current, history, state_path, session)
                summary = current / "coordinator_summary.md"
                try: summary.lstat()
                except FileNotFoundError: pass
                else:
                    read_regular_evidence(summary)
                    action = "inspect coordinator summary; no new cycle is authorized"
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
        owned = current / ("coordinator_summary.md" if phase == "coordinator_review" else session.get("report_slots", {}).get(phase, f".{phase}.json"))
        trigger_status = None
        if stage in ("WAITING_FOR_HUMAN", "COMPLETED_COORDINATOR_REVIEW"):
            try: trigger_status, action = trigger_view(session, "coordinator" if phase == "coordinator_review" else phase, owned)
            except RuntimeError as error: return refusal(str(error), "stale_or_mismatched_task_state")
        attempt = session.get("trigger_attempts", {}).get("coordinator" if phase == "coordinator_review" else phase) if isinstance(session.get("trigger_attempts", {}), dict) else None
        transport = "not_attempted" if attempt is None else "confirmed" if attempt.get("status") == "confirmed" else "uncertain"
        pending = "none"
        if phase == "coordinator_review" and os.path.lexists(current / "coordinator_proposal.md") and os.path.lexists(current / "coordinator_summary.md"):
            try:
                proposal, _ = proposal_identity(root, config, project_path(root, config["task_authority"]), project_path(root, config["approval_record"]), current, history, state_path)
                decision, reason = proposal_decision(verify_active_policy(root, config, current, state), state, session)
                pending = "ineligible" if decision == "stop" else "awaiting_approval"
                action = reason + "; request human direction" if decision == "stop" else f"proposal; after review: approve-next --run-id {proposal['run_id']} --iteration {proposal['iteration']} --proposal-sha256 {proposal['proposal_sha256']}"
                if decision == "correction":
                    if "scope_sha256" not in proposal: pending = "missing_correction_scope"; action = "provide correction_scope.json and inspect proposal"
                    else:
                        verify_correction_scope(current, history, state, proposal)
                        action += f" --scope-sha256 {proposal['scope_sha256']} --confirm-correction-scope"
                if decision != "stop" and os.path.lexists(current / "proposal_approval.json"):
                    recorded = json.loads(read_regular_evidence(current / "proposal_approval.json")); wanted = proposal_approval_record(proposal)
                    if recorded != wanted: pending = "stale_approval"; action = "inspect stale approval; preserve evidence"
                    else:
                        pending = "approved"
                        action = "rollover-correction" if decision == "correction" else "rollover-next-task"
            except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError): pending = "invalid"; action = "inspect proposal evidence"
        stop_command = None
        if phase == "coordinator_review" and os.path.lexists(current / "coordinator_summary.md") and not os.path.lexists(current / "proposal_approval.json"):
            try:
                stop_identity, _ = completed_identity(root, config, project_path(root, config["task_authority"]), project_path(root, config["approval_record"]), current, history, state_path)
                stop_command = f"stop-proposal --run-id {stop_identity['run_id']} --iteration {stop_identity['iteration']}"
            except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError): pass
        print(json.dumps({"outcome":"success", "title":title, "phase":phase, "state":stage, "trigger_status":trigger_status, "transport":transport, "role_output":"present_unvalidated" if os.path.lexists(owned) else "not_observed", "output_present":os.path.lexists(owned), "configured_roles":list(ROLE_ORDER), "roles_started":expected, "next_action":action, "stop_command":stop_command, "task_id":state.get("task_id"), "task_number":state.get("task_number"), "task_limit":state.get("task_limit"), "attempt":state.get("attempt"), "attempt_limit":state.get("attempt_limit"), "review_verdict":session.get("review_verdict"), "pending_proposal":pending, "task_snapshot":str(current / "authoritative_task.md"), "owned_report":str(owned), "developer_report":str(current / "dev_report.md"), "reviewer_report":str(current / "review_report.md")})); return 0
    if session.get("launch_mode") == "coordinator_only" or state.get("phase") == "coordinator_initial":
        if session.get("launch_mode") != "coordinator_only" or state.get("status") != "RUNNING" or state.get("phase") != "coordinator_initial" or session.get("phase") != "coordinator_initial" or session.get("state") not in ("WAITING_FOR_HUMAN", "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING") or session.get("task_snapshot_sha256") != state.get("task_snapshot_sha256"):
            return refusal("Coordinator session is inconsistent or delivery remains uncertain", "stale_or_mismatched_task_state")
        try:
            validate_snapshot(root, project_path(root, config["task_authority"]), current, config, state)
            tabs = json.loads(tab_state(current).read_text(encoding="utf-8")); identifiers = session.get("tab")
            if not isinstance(identifiers, dict) or not all(isinstance(identifiers.get(k), str) and identifiers[k] for k in ("window", "tab", "session")) or not isinstance(tabs, dict) or not isinstance(tabs.get("roles"), list) or len(tabs["roles"]) != 1 or not isinstance(tabs["roles"][0], dict) or any(tabs["roles"][0].get(k) != identifiers[k] for k in ("window", "tab", "session")):
                raise RuntimeError("Coordinator tab evidence is inconsistent")
        except (OSError, UnicodeError, RuntimeError, ValueError, TypeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
        action = "launch developer" if session["state"] == "COORDINATOR_ACCEPTED_STAGED_LAUNCH_PENDING" else next_action("coordinator_initial")
        print(json.dumps({"outcome":"success", "title":title, "phase":"coordinator_initial", "state":session["state"], "configured_roles":list(ROLE_ORDER), "roles_started":["coordinator"], "next_action":action, "task_id":state.get("task_id"), "task_number":state.get("task_number"), "task_limit":state.get("task_limit"), "attempt":state.get("attempt"), "attempt_limit":state.get("attempt_limit"), "task_snapshot":str(current / "authoritative_task.md"), "owned_report":str(current / ".coordinator.json")}))
        return 0
    print_session(root, config, current, session["phase"], title); return 0


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


def init_authority_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or candidate == Path(".") or ".." in candidate.parts:
        raise RuntimeError("--task-authority must be a non-empty project-relative file path")
    path = root / candidate
    if path == root or path.suffix == "":
        raise RuntimeError("--task-authority must name a file")
    return path


def is_git_repository(root: Path) -> bool:
    result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, text=True, capture_output=True)
    return result.returncode == 0 and result.stdout.strip() == "true"


def path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def preflight_init_destinations(root: Path, destinations: list[Path]) -> None:
    for destination in destinations:
        try: relative = destination.relative_to(root)
        except ValueError as error: raise RuntimeError("initialization destination escapes project root") from error
        current = root
        for component in relative.parts:
            current /= component
            if current.is_symlink():
                raise RuntimeError("initialization refuses symlinked destination component: " + str(current.relative_to(root)))


def init_project(project_root: str, authority_value: str, init_git: bool, tabs: bool = False, launcher=launch_iterm_tab, tabs_probe: bool = False, tabs_layout_probe: bool = False, tabs_coordinator_bootstrap_probe: bool = False) -> int:
    root = Path(project_root).expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise RuntimeError("--project-root must be a directory")
    authority = init_authority_path(root, authority_value)
    targets = [root / ".agent/controller_config.json", root / ".agent/authority_approvals.json", root / ".agent/runtime", authority]
    targets.extend(root / item for item in INIT_ASSETS)
    destinations = [*targets, root / ".gitignore", root / ".git"]
    preflight_init_destinations(root, destinations)
    conflicts = [path for path in targets if path_exists(path)]
    if conflicts:
        raise RuntimeError("initialization refuses existing controller target: " + str(conflicts[0].relative_to(root)))
    if root.exists() and not is_git_repository(root) and not init_git:
        raise RuntimeError("project is not a Git repository; rerun with --init-git to initialize Git without a commit")
    if not root.exists():
        if not init_git:
            raise RuntimeError("new project directory requires --init-git")
        root.mkdir(parents=True)
    if not is_git_repository(root):
        result = subprocess.run(["git", "init"], cwd=root, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError("Git initialization failed: " + result.stderr.strip())
    config = dict(INIT_CONFIG); config["task_authority"] = authority_value
    write_json(root / ".agent/controller_config.json", config)
    write_json(root / ".agent/authority_approvals.json", {"approvals": []})
    write_json(root / ".agent/runtime/state.json", {"iteration": 0, "status": "READY"})
    authority.parent.mkdir(parents=True, exist_ok=True); authority.write_text(NEUTRAL_AUTHORITY, encoding="utf-8")
    for relative in INIT_ASSETS:
        destination = root / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    ignore = root / ".gitignore"; existing = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    missing = [entry for entry in RUNTIME_IGNORES if entry not in existing.splitlines()]
    if missing:
        suffix = "" if not existing or existing.endswith("\n") else "\n"
        ignore.write_text(existing + suffix + "\n".join(missing) + "\n", encoding="utf-8")
    config, configured_root = load_config(root / ".agent/controller_config.json")
    _, _, current, _, _ = locations(configured_root, config)
    supervised_init(configured_root, config, current, tabs, launcher, tabs_probe, tabs_layout_probe, tabs_coordinator_bootstrap_probe)
    print("Initialized local controller scaffolding in " + str(root))
    print("Next: configure role commands if needed; authorize a bounded task in " + authority_value + "; create an initial Git commit/HEAD; then run python .agent/orchestrate.py --dry-run.")
    return 0


def load_config(path: Path | None = None) -> tuple[dict, Path]:
    path = path or CONFIG_PATH; raw = path.read_bytes(); config = json.loads(raw)
    required = {"tab_host", "task_authority", "approval_record", "paths", "roles", "role_timeout_seconds"}
    if not isinstance(config, dict) or not required <= set(config): raise RuntimeError("configuration is malformed")
    if config["tab_host"] != "iterm2": raise RuntimeError("configuration tab_host must be iterm2; no other automatic tab host is supported")
    roles = config["roles"]
    # C1 intentionally supports exactly these semantic roles, with all project assets configurable.
    if not isinstance(roles, list) or [item.get("name") for item in roles] != ["coordinator", "developer", "reviewer"]: raise RuntimeError("C1 supports only coordinator, developer, reviewer role order")
    for item in roles:
        if not all(isinstance(item.get(key), str) and item[key] for key in ("name", "instruction", "schema")) or not isinstance(item.get("command"), list) or not isinstance(item.get("write_capable"), bool): raise RuntimeError("configuration role is malformed")
        if "session_command" in item and (not isinstance(item["session_command"], list) or not item["session_command"] or any(not isinstance(value, str) or not value for value in item["session_command"])): raise RuntimeError("configuration session command is malformed")
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


LOCK_IDENTITIES: dict[Path, tuple[int, int]] = {}


def acquire_lock(agent: Path) -> Path:
    lock = agent / "orchestrate.lock"
    try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error: raise RuntimeError(f"controller lock exists: {lock}; remove only after verifying it is stale") from error
    try:
        info = os.fstat(fd); os.write(fd, str(os.getpid()).encode())
        LOCK_IDENTITIES[lock] = (info.st_dev, info.st_ino)
    finally: os.close(fd)
    return lock


def lock_owned(lock: Path) -> bool:
    try:
        info = lock.stat()
        return LOCK_IDENTITIES.get(lock) == (info.st_dev, info.st_ino)
    except OSError: return False


def release_lock(lock: Path) -> None:
    identity = LOCK_IDENTITIES.pop(lock, None)
    try:
        info = lock.stat()
        if identity == (info.st_dev, info.st_ino): lock.unlink()
    except FileNotFoundError: pass


def archive(current: Path, history: Path, iteration: int, state: dict) -> None:
    target = history / f"{iteration:03d}"
    history.mkdir(parents=True, exist_ok=True)
    try: target.mkdir()
    except FileExistsError as error: raise RuntimeError(f"iteration {iteration} is already archived; refusing to overwrite history") from error
    for name in ("authoritative_task.md", "task_snapshot.json", "workflow_policy.json", "effective_policy.json", "approval_evidence.json", "dev_report.md", "review_report.md", "baseline.json", "after_developer.json", "review_identity.json", "human_stop.json", "supervised_session.json", "tabs.json", ".coordinator.json", ".developer.json", ".reviewer.json"):
        source = current / name
        if name in (".coordinator.json", ".developer.json", ".reviewer.json"):
            if not source.is_symlink() and source.is_file(): shutil.copy2(source, target / name, follow_symlinks=False)
        elif source.is_file(): shutil.copy2(source, target / name)
    session = load_supervised_session(current) if session_path(current).is_file() else {}
    for role_name, name in session.get("report_slots", {}).items():
        if role_name not in ("developer", "reviewer") or not isinstance(name, str) or not re.fullmatch(r"\.(developer|reviewer)-[0-9a-f]{32}\.json", name): raise RuntimeError("invalid report slot")
        source = current / name
        if os.path.lexists(source): (target / name).write_bytes(read_regular_evidence(source))
    write_json(target / "state.json", state)
def finish(current: Path, history: Path, state_path: Path, iteration: int, state: dict, status: str, reason: str | None = None) -> int:
    state.update(iteration=iteration, status=status, stopped_reason=reason); state.pop("phase", None); state.pop("active_iteration", None); archive(current, history, iteration, state); write_json(state_path, state); return 0
def human_stop(current: Path, history: Path, state_path: Path, iteration: int, state: dict, category: str, reason: str) -> int:
    if category not in HUMAN_STOP_CATEGORIES: raise RuntimeError(f"unknown human-stop category: {category}")
    write_json(current / "human_stop.json", {"category": category, "reason": reason, "state": "HUMAN_REQUIRED", "phase": state.get("phase"), "task_snapshot_sha256": state.get("task_snapshot_sha256")})
    result = finish(current, history, state_path, iteration, state, "HUMAN_REQUIRED", f"{category}: {reason}")
    session_path(current).unlink(missing_ok=True); tab_state(current).unlink(missing_ok=True)
    return result


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


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command")
    init = subcommands.add_parser("init", help="create a non-executing project-local controller scaffold")
    init.add_argument("--project-root", default=".")
    init.add_argument("--task-authority", default="docs/NEXT_PROMPT.md")
    init.add_argument("--init-git", action="store_true", help="initialize Git when the target is not already a repository; never commits")
    init.add_argument("--roles", default="coordinator,developer,reviewer")
    init.add_argument("--tabs", action="store_true", help="open supervised iTerm2 role tabs after successful initialization")
    init.add_argument("--tabs-probe", action="store_true", help="create one iTerm2 host diagnostic tab; requires --tabs")
    init.add_argument("--tabs-layout-probe", action="store_true", help="create three native iTerm2 layout diagnostic tabs; requires --tabs")
    init.add_argument("--tabs-coordinator-bootstrap-probe", action="store_true", help="deliver one read-only Coordinator Codex bootstrap; requires --tabs")
    start = subcommands.add_parser("start", help="start the staged Coordinator-only supervised session")
    start.add_argument("--tabs", action="store_true", help="launch the native Coordinator tab after supervised preflight")
    start.add_argument("--task-limit", type=int, choices=(1, 2), default=1, help="human-authorized task-cycle limit (default: 1)")
    start.add_argument("--attempt-limit", type=int, default=1, help="human-authorized attempts per task, 1 to 100 (default: 1)")
    for command in ("preview", "status", "cycle", "resume"):
        subcommands.add_parser(command, help=f"show supervised workflow {command}")
    trigger = subcommands.add_parser("trigger", help="send a role phrase to its recorded interactive session")
    trigger.add_argument("role"); trigger.add_argument("--ready", action="store_true", help="confirm that the intended tab is waiting at its Codex input prompt")
    ready_developer_parser = subcommands.add_parser("ready-developer", help="read-only readiness check for a specific rollover Developer attempt")
    ready_developer_parser.add_argument("--attempt-id", required=True)
    ready_developer_parser.add_argument("--delivery-id", help="recorded trigger ID for a controller-sent turn")
    launch = subcommands.add_parser("launch", help="explicitly launch the eligible staged role")
    launch.add_argument("role")
    accept = subcommands.add_parser("accept", help="validate a human-completed role handoff")
    accept.add_argument("role")
    subcommands.add_parser("proposal", help="display the pending Coordinator proposal and identities for human review")
    approve_next = subcommands.add_parser("approve-next", help="record the human decision for the exact displayed proposal; does not dispatch")
    approve_next.add_argument("--run-id", required=True)
    approve_next.add_argument("--iteration", type=int, required=True, help="completed attempt iteration shown by proposal")
    approve_next.add_argument("--proposal-sha256", required=True)
    approve_next.add_argument("--scope-sha256", help="exact displayed correction scope hash")
    approve_next.add_argument("--confirm-correction-scope", action="store_true", help="confirm original task scope and each mapped finding")
    stop = subcommands.add_parser("stop-proposal", help="record a human stop for the displayed completed attempt")
    stop.add_argument("--run-id", required=True); stop.add_argument("--iteration", type=int, required=True)
    subcommands.add_parser("rollover-correction", help="publish an approved correction and prepare the existing Developer tab; does not dispatch")
    subcommands.add_parser("rollover-next-task", help="publish an approved next task within the authorized budget; does not dispatch")
    parser.add_argument("--multi-cycle", action="store_true"); parser.add_argument("--max-iterations", type=int); parser.add_argument("--resume", action="store_true"); parser.add_argument("--dry-run", action="store_true"); args = parser.parse_args()
    if args.command == "init":
        if args.tabs_probe and not args.tabs: raise RuntimeError("--tabs-probe requires --tabs")
        if args.tabs_layout_probe and not args.tabs: raise RuntimeError("--tabs-layout-probe requires --tabs")
        if args.tabs_coordinator_bootstrap_probe and not args.tabs: raise RuntimeError("--tabs-coordinator-bootstrap-probe requires --tabs")
        if sum((args.tabs_probe, args.tabs_layout_probe, args.tabs_coordinator_bootstrap_probe)) > 1: raise RuntimeError("choose only one --tabs probe mode")
        parse_roles(args.roles); return init_project(args.project_root, args.task_authority, args.init_git, args.tabs, tabs_probe=args.tabs_probe, tabs_layout_probe=args.tabs_layout_probe, tabs_coordinator_bootstrap_probe=args.tabs_coordinator_bootstrap_probe)
    if args.command == "start":
        if not args.tabs: raise RuntimeError("start requires --tabs")
        config, root = load_config(Path.cwd().resolve() / ".agent/controller_config.json")
        authority, approval_record, current, history, state_path = locations(root, config)
        return start_supervised(root, config, authority, approval_record, current, history, state_path, task_limit=args.task_limit, attempt_limit=args.attempt_limit)
    if args.command in ("preview", "status", "cycle", "resume", "accept", "launch", "trigger", "proposal", "approve-next", "rollover-correction", "rollover-next-task", "stop-proposal", "ready-developer"):
        config, root = load_config(Path.cwd().resolve() / ".agent/controller_config.json")
        authority, approval_record, current, history, state_path = locations(root, config)
        if args.command == "ready-developer": return ready_developer(root, config, authority, approval_record, current, history, state_path, args.attempt_id, args.delivery_id)
        if args.command == "proposal": return pending_proposal(root, config, authority, approval_record, current, history, state_path)
        if args.command == "approve-next": return approve_proposal(root, config, authority, approval_record, current, history, state_path, args.run_id, args.iteration, args.proposal_sha256, args.scope_sha256, args.confirm_correction_scope)
        if args.command == "stop-proposal": return stop_proposal(root, config, authority, approval_record, current, history, state_path, args.run_id, args.iteration)
        if args.command == "rollover-correction": return rollover_correction(root, config, authority, approval_record, current, history, state_path)
        if args.command == "rollover-next-task": return rollover_next_task(root, config, authority, approval_record, current, history, state_path)
        if args.command == "trigger":
            name = ROLE_ALIASES.get(args.role.lower())
            if name is None: return refusal("trigger requires coordinator, developer, or reviewer")
            return trigger_staged_role(root, config, authority, approval_record, current, history, state_path, name, args.ready)
        if args.command == "launch":
            name = ROLE_ALIASES.get(args.role.lower())
            if name not in ("developer", "reviewer"): return refusal("launch requires developer or reviewer")
            return launch_staged_role(root, config, authority, current, history, state_path, name)
        if args.command == "accept":
            name = ROLE_ALIASES.get(args.role.lower())
            if name is None: raise RuntimeError("accept requires coordinator, developer, or reviewer")
            return supervised_accept(root, config, authority, approval_record, current, history, state_path, name)
        if args.command == "cycle": return supervised_cycle(root, config, authority, current, history, state_path)
        return supervised_view(root, config, current, history, state_path, args.command)
    if args.max_iterations is not None and not args.multi_cycle: parser.error("--max-iterations requires --multi-cycle")
    config, root = load_config(); authority, approval_record, current, history, state_path = locations(root, config); approval_entries(approval_record); state = json.loads(state_path.read_text())
    if state.get("config_sha256") not in (None, config["_sha256"]): raise RuntimeError("saved state belongs to a different controller configuration")
    maximum = args.max_iterations if args.multi_cycle and args.max_iterations is not None else (state.get("max_iterations", 1) if args.multi_cycle else 1)
    if args.dry_run: print(json.dumps({"root": str(root), "task_authority": str(authority.relative_to(root)), "roles": [item["name"] for item in config["roles"]], "max_iterations": maximum}, indent=2)); return 0
    lock = acquire_lock(state_path.parent)
    try:
        if os.path.lexists(current / "proposal_stop.json"):
            return refusal("human stopped this proposal decision", recovery="preserve the recorded stop and prior evidence; do not resume this run")
        try:
            locked_state = json.loads(read_regular_evidence(state_path))
            if not isinstance(locked_state, dict) or locked_state != state: raise RuntimeError("saved state changed before legacy lock acquisition")
            if "coordinator_tab" in locked_state: raise RuntimeError("legacy execution refuses a staged run")
            staged_session = session_path(current)
            if os.path.lexists(staged_session):
                session_data = json.loads(read_regular_evidence(staged_session))
                if not isinstance(session_data, dict): raise RuntimeError("saved session is malformed")
                if session_data.get("launch_mode") == "coordinator_only": raise RuntimeError("legacy execution refuses a staged run")
        except (OSError, UnicodeError, ValueError, TypeError, RuntimeError) as error:
            return refusal(str(error), "stale_or_mismatched_task_state", recovery="preserve evidence and use the staged control commands when applicable")
        if state.get("phase") and not args.resume: raise RuntimeError("use --resume for the saved active phase")
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
                for name in (".coordinator.json", ".developer.json", ".reviewer.json", "authoritative_task.md", "task_snapshot.json", "workflow_policy.json", "effective_policy.json", "approval_evidence.json", "dev_report.md", "review_report.md", "baseline.json", "after_developer.json", "human_stop.json"): (current / name).unlink(missing_ok=True)
                identity, policy_bytes = effective_policy(root, config)
                state["effective_policy"] = identity
                (current / "workflow_policy.json").write_bytes(policy_bytes); write_json(current / "effective_policy.json", identity)
                state["baseline"] = {"head": head, "manifest": base}; write_json(state_path, state)
            iteration, phase = state["active_iteration"], state["phase"]
            try: verify_active_policy(root, config, current, state)
            except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
            try:
                if phase == "coordinator":
                    output = current / ".coordinator.json"; prompt = read(project_path(root, role(config, "coordinator")["instruction"])) + "\nOwner input:\n" + read(current / "human_input.md")
                    if output.is_file():
                        try: result = validate_output(root, config, "coordinator", json.loads(output.read_text()))
                        except json.JSONDecodeError as error: raise RoleFailure("malformed saved coordinator checkpoint") from error
                    else: result = run_role(root, current, config, "coordinator", prompt)
                    try: verify_active_policy(root, config, current, state)
                    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
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
                    try: verify_active_policy(root, config, current, state)
                    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
                    (current / "dev_report.md").write_text(report("Developer report", result)); write_json(current / "after_developer.json", manifest(root, runtime))
                    if result["status"] != "DONE": return human_stop(current, history, state_path, iteration, state, result["human_category"] or "failed_or_incomplete_validation", result["summary"])
                    state["phase"] = "reviewer"; write_json(state_path, state)
                elif phase == "reviewer":
                    task = validate_snapshot(root, authority, current, config, state); output = current / ".reviewer.json"; prompt = read(project_path(root, role(config, "reviewer")["instruction"])) + "\nImmutable task snapshot:\n" + task + "\nDeveloper report:\n" + read(current / "dev_report.md")
                    if output.is_file():
                        try: result = validate_output(root, config, "reviewer", json.loads(output.read_text()))
                        except json.JSONDecodeError as error: raise RoleFailure("malformed saved reviewer checkpoint") from error
                    else: result = run_role(root, current, config, "reviewer", prompt)
                    try: verify_active_policy(root, config, current, state)
                    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as error: return refusal(str(error), "stale_or_mismatched_task_state")
                    escalation = review_escalation(result)
                    if escalation is not None: return human_stop(current, history, state_path, iteration, state, *escalation)
                    (current / "review_report.md").write_text(report("Reviewer report", result))
                    if result["verdict"] != "APPROVED": return human_stop(current, history, state_path, iteration, state, result["human_category"] or "failed_or_incomplete_validation", result.get("human_reason") or result["summary"])
                    state["last_authority_sha256"] = state["task_snapshot_sha256"]; finish(current, history, state_path, iteration, state, "READY"); completed += 1
                    if not args.multi_cycle: return 0
                else: return human_stop(current, history, state_path, iteration, state, "stale_or_mismatched_task_state", "unknown saved phase")
            except RoleFailure as error:
                try: verify_active_policy(root, config, current, state)
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as policy_error: return refusal(str(policy_error), "stale_or_mismatched_task_state")
                category = "indeterminate_write_invocation" if phase == "developer" else "failed_or_incomplete_validation"
                return human_stop(current, history, state_path, iteration, state, category, str(error))
            except (RuntimeError, json.JSONDecodeError) as error:
                try: verify_active_policy(root, config, current, state)
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as policy_error: return refusal(str(policy_error), "stale_or_mismatched_task_state")
                category = "unsafe_or_unexpected_diff" if "baseline" in str(error) or "Git" in str(error) else "stale_or_mismatched_task_state"
                return human_stop(current, history, state_path, iteration, state, category, str(error))
        return 0
    finally: release_lock(lock)


def main() -> int:
    try: return _main()
    except (RuntimeError, OSError, UnicodeError, json.JSONDecodeError, TypeError, KeyError) as error:
        if len(sys.argv) > 1 and sys.argv[1] in ("start", "accept", "launch", "trigger", "status", "preview", "cycle", "resume", "proposal", "approve-next", "rollover-correction", "rollover-next-task", "stop-proposal", "ready-developer"):
            return refusal(str(error), "stale_or_mismatched_task_state")
        raise


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (RuntimeError, OSError, json.JSONDecodeError) as error: print(f"orchestration stopped: {error}", file=sys.stderr); raise SystemExit(2)
