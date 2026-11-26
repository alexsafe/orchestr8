#!/usr/bin/env python3
"""Native iTerm2 one-tab and three-tab layout probe bridge."""
import asyncio, json, shlex, sys, time

LAYOUT_TITLES = ["ORCHESTR8 · Coordinator", "ORCHESTR8 · Developer", "ORCHESTR8 · Reviewer"]
BOOTSTRAP_TITLE = "ORCHESTR8 · Coordinator · bootstrap probe"
BOOTSTRAP_PROMPT = "Read .agent/roles/coordinator.md. Write no artifact. Wait for a human Start project: <human initial brief> message."
COORDINATOR_START_TITLE = "ORCHESTR8 · Coordinator · waiting for Start project…"
COORDINATOR_START_PROMPT = "Read .agent/roles/coordinator.md. Wait for a human Start project: <human initial brief> message."
TRIGGER_SETTLE_SECONDS = 1.0

def native_probe(request):
    try:
        import iterm2
    except ImportError:
        return {"ok": False, "reason": "iterm2 module unavailable; create an isolated .venv and install the project, then authorize iTerm2 Python API"}
    async def main(connection):
        app = await iterm2.async_get_app(connection)
        window = app.current_terminal_window
        if window is None:
            return {"ok": False, "reason": "no active iTerm2 control window; run from iTerm2 and authorize its Python API"}
        started = time.monotonic()
        tab = await window.async_create_tab()
        if tab is None:
            return {"ok": False, "reason": "iTerm2 default-profile session closed immediately; close any partial tab and use a fresh target"}
        await tab.async_set_title(request["title"])
        return {"ok": True, "host": "iterm2", "window": str(window.window_id), "tab": str(tab.tab_id), "elapsed_seconds": round(time.monotonic() - started, 3), "reason": "confirmed"}
    try:
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok": False, "reason": "iTerm2 native probe failed; verify isolated .venv and iTerm2 API authorization: " + str(error)}

def layout_probe(request):
    try:
        import iterm2
    except ImportError:
        return {"ok": False, "reason": "iterm2 module unavailable; create an isolated .venv and install the project, then authorize iTerm2 Python API"}
    async def main(connection):
        app = await iterm2.async_get_app(connection)
        window = app.current_terminal_window
        if window is None:
            return {"ok": False, "reason": "layout preflight failed: no active iTerm2 control window; run from iTerm2 and authorize its Python API"}
        started, tabs = time.monotonic(), []
        for step, title in enumerate(LAYOUT_TITLES, start=1):
            try:
                tab = await window.async_create_tab()
            except Exception as error:
                return {"ok": False, "reason": f"layout step {step} ({title}) creation failed: {error}; close partial tabs and use a fresh target"}
            if tab is None:
                return {"ok": False, "reason": f"layout step {step} ({title}) creation returned None; close partial tabs and use a fresh target"}
            try:
                await tab.async_set_title(title)
            except Exception as error:
                return {"ok": False, "reason": f"layout step {step} ({title}) title failed: {error}; close partial tabs and use a fresh target"}
            try:
                tabs.append(str(tab.tab_id))
            except Exception as error:
                return {"ok": False, "reason": f"layout step {step} ({title}) identifier failed: {error}; close partial tabs and use a fresh target"}
        return {"ok": True, "window": str(window.window_id), "tabs": tabs, "elapsed_seconds": round(time.monotonic() - started, 3), "result": "confirmed"}
    try:
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok": False, "reason": "layout probe failed before confirmation; close partial tabs and use a fresh target: " + str(error)}

def coordinator_bootstrap_probe(request):
    try:
        import iterm2
    except ImportError:
        return {"ok": False, "reason": "iterm2 module unavailable; create an isolated .venv and install the project, then authorize iTerm2 Python API"}
    command = "codex -C " + shlex.quote(request["cwd"]) + " -s read-only " + shlex.quote(BOOTSTRAP_PROMPT) + "\n"
    async def main(connection):
        try:
            app = await iterm2.async_get_app(connection)
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap preflight app discovery failed: {error}; close partial tabs and use a fresh target"}
        if app is None:
            return {"ok": False, "reason": "bootstrap preflight app discovery returned None; close partial tabs and use a fresh target"}
        try:
            window = app.current_terminal_window
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap preflight active-window discovery failed: {error}; close partial tabs and use a fresh target"}
        if window is None:
            return {"ok": False, "reason": "bootstrap preflight failed: no active iTerm2 control window; close partial tabs and use a fresh target after authorizing its Python API"}
        started = time.monotonic()
        try:
            tab = await window.async_create_tab()
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap step tab creation failed: {error}; close partial tabs and use a fresh target"}
        if tab is None:
            return {"ok": False, "reason": "bootstrap step tab creation returned None; close partial tabs and use a fresh target"}
        try:
            await tab.async_set_title(BOOTSTRAP_TITLE)
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap step title failed: {error}; close partial tabs and use a fresh target"}
        try:
            session = tab.current_session
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap step session retrieval failed: {error}; close partial tabs and use a fresh target"}
        if session is None:
            return {"ok": False, "reason": "bootstrap step session retrieval returned None; close partial tabs and use a fresh target"}
        try:
            await session.async_send_text(command)
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap step command delivery failed: {error}; close partial tabs and use a fresh target"}
        try:
            return {"ok": True, "window": str(window.window_id), "tab": str(tab.tab_id), "session": str(session.session_id), "elapsed_seconds": round(time.monotonic() - started, 3), "result": "unverified_bootstrap_delivered"}
        except Exception as error:
            return {"ok": False, "reason": f"bootstrap step identifier retrieval failed: {error}; close partial tabs and use a fresh target"}
    try:
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok": False, "reason": "bootstrap probe failed before confirmation; close partial tabs and use a fresh target: " + str(error)}

def coordinator_start(request):
    try:
        import iterm2
    except ImportError:
        return {"ok": False, "reason": "iterm2 module unavailable; create an isolated .venv and install the project, then authorize iTerm2 Python API"}
    prompt = "Read " + request["instruction"] + " and effective workflow policy " + request["current"] + "/workflow_policy.json. Policy decisions: " + request.get("policy_guidance", "") + ". Wait for a human Start project: <human initial brief> message. Configured task authority: " + request["authority"] + "; current directory: " + request["current"] + "; immutable snapshot: " + request["current"] + "/authoritative_task.md; initial report: " + request["current"] + "/.coordinator.json; Developer report: " + request["current"] + "/dev_report.md; Reviewer report: " + request["current"] + "/review_report.md; final summary: " + request["current"] + "/coordinator_summary.md."
    command = shlex.join(request["command"]) + " -C " + shlex.quote(request["cwd"]) + " -s workspace-write " + shlex.quote(prompt) + "\n"
    async def main(connection):
        try:
            app = await iterm2.async_get_app(connection)
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start preflight app discovery failed: {error}; close partial tabs and use a fresh target"}
        if app is None:
            return {"ok": False, "reason": "Coordinator start preflight app discovery returned None; close partial tabs and use a fresh target"}
        try:
            window = app.current_terminal_window
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start preflight active-window discovery failed: {error}; close partial tabs and use a fresh target"}
        if window is None:
            return {"ok": False, "reason": "Coordinator start preflight found no active iTerm2 control window; close partial tabs and use a fresh target"}
        started = time.monotonic()
        try:
            tab = await window.async_create_tab()
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start tab creation failed: {error}; close partial tabs and use a fresh target"}
        if tab is None:
            return {"ok": False, "reason": "Coordinator start tab creation returned None; close partial tabs and use a fresh target"}
        try:
            await tab.async_set_title(COORDINATOR_START_TITLE)
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start title failed: {error}; close partial tabs and use a fresh target"}
        try:
            session = tab.current_session
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start session retrieval failed: {error}; close partial tabs and use a fresh target"}
        if session is None:
            return {"ok": False, "reason": "Coordinator start session retrieval returned None; close partial tabs and use a fresh target"}
        try:
            await session.async_send_text(command)
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start command delivery failed: {error}; close partial tabs and use a fresh target"}
        try:
            return {"ok": True, "window": str(window.window_id), "tab": str(tab.tab_id), "session": str(session.session_id), "elapsed_seconds": round(time.monotonic() - started, 3), "result": "coordinator_delivery_confirmed"}
        except Exception as error:
            return {"ok": False, "reason": f"Coordinator start identifier retrieval failed: {error}; close partial tabs and use a fresh target"}
    try:
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok": False, "reason": "Coordinator start failed before confirmation; close partial tabs and use a fresh target: " + str(error)}

def staged_role_start(request):
    try:
        import iterm2
        async def main(connection):
            app = await iterm2.async_get_app(connection)
            windows = app.terminal_windows if app is not None else []
            window = next((item for item in windows if str(item.window_id) == request["window"]), None)
            if window is None: return {"ok": False, "reason": "recorded Coordinator window is unavailable"}
            started = time.monotonic()
            tab = await window.async_create_tab()
            if tab is None: raise RuntimeError("tab creation returned no tab")
            await tab.async_set_title(request["title"])
            session = tab.current_session
            if session is None: raise RuntimeError("tab has no session")
            await session.async_send_text(request["command"] + "\n")
            return {"ok": True, "window": str(window.window_id), "tab": str(tab.tab_id), "session": str(session.session_id), "elapsed_seconds": round(time.monotonic()-started, 3), "result": "role_delivery_confirmed"}
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok": False, "reason": "role delivery incomplete or uncertain: " + str(error)}

def update_role_label(request):
    try:
        import iterm2
        async def main(connection):
            app = await iterm2.async_get_app(connection)
            window = next((w for w in app.terminal_windows if str(w.window_id) == request["window"]), None)
            tab = next((t for t in window.tabs if str(t.tab_id) == request["tab"]), None) if window else None
            session = next((s for s in tab.sessions if str(s.session_id) == request["session"]), None) if tab else None
            if session is None: return {"ok":False, "reason":"recorded window, tab or session unavailable"}
            await tab.async_set_title(request["title"])
            return {"ok":True, **{key:request[key] for key in ("window", "tab", "session", "title")}}
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok":False, "reason":"label update failed: " + str(error)}

def send_role_trigger(request):
    evidence = {"window":request["window"], "tab":request["tab"], "session":request["session"], "sends":[]}
    try:
        import iterm2
        async def main(connection):
            async def send(label, value):
                entry = {"step":label, "started_monotonic":time.monotonic()}
                evidence["sends"].append(entry)
                try:
                    response = await iterm2.rpc.async_send_text(connection, request["session"], value, True)
                    entry["finished_monotonic"] = time.monotonic()
                    if not response.HasField("send_text_response") or not response.send_text_response.HasField("status"):
                        raise RuntimeError("missing send-text response status")
                    status = response.send_text_response.status
                    entry["status"] = iterm2.api_pb2.SendTextResponse.Status.Name(status)
                    if status != iterm2.api_pb2.SendTextResponse.OK:
                        raise RuntimeError("iTerm send-text status: " + entry["status"])
                except Exception:
                    entry.setdefault("finished_monotonic", time.monotonic())
                    raise
            app = await iterm2.async_get_app(connection)
            window = next((item for item in app.terminal_windows if str(item.window_id) == request["window"]), None)
            if window is None: return {"ok":False, "reason":"recorded window is unavailable"}
            tab = next((item for item in window.tabs if str(item.tab_id) == request["tab"]), None)
            if tab is None: return {"ok":False, "reason":"recorded tab is unavailable in the recorded window"}
            session = next((item for item in tab.sessions if str(item.session_id) == request["session"]), None)
            if session is None: return {"ok":False, "reason":"recorded session is unavailable in the recorded tab"}
            job = await session.async_get_variable("jobName")
            if not isinstance(job, str) or not job.strip() or job.strip().lower().rsplit("/", 1)[-1] in ("sh", "bash", "zsh", "fish", "login"):
                return {"ok":False, "reason":"destination appears exited or its foreground job is unknown"}
            # iTerm's typed-input API targets this session; a separate CR requests Return.
            # Neither RPC establishes that Codex consumed or submitted the prompt.
            await send("text", request["payload"])
            evidence["settle"] = {"requested_seconds":TRIGGER_SETTLE_SECONDS, "started_monotonic":time.monotonic()}
            try:
                await asyncio.sleep(TRIGGER_SETTLE_SECONDS)
            finally:
                evidence["settle"]["finished_monotonic"] = time.monotonic()
            app = await iterm2.async_get_app(connection)
            window = next((item for item in app.terminal_windows if str(item.window_id) == request["window"]), None)
            tab = next((item for item in window.tabs if str(item.tab_id) == request["tab"]), None) if window else None
            session = next((item for item in tab.sessions if str(item.session_id) == request["session"]), None) if tab else None
            if session is None:
                return {"ok":False, "reason":"destination disappeared during input settling; submission is uncertain", **evidence}
            job_after_text = await session.async_get_variable("jobName")
            if job_after_text != job:
                return {"ok":False, "reason":"foreground job changed after prompt delivery; submission is uncertain", **evidence}
            await send("carriage_return", "\r")
            return {"ok":True, **evidence, "result":"trigger_delivery_confirmed", "submission":"carriage_return_sent"}
        return iterm2.run_until_complete(main)
    except Exception as error:
        return {"ok":False, "reason":"trigger delivery incomplete or uncertain: " + str(error), **evidence}

try:
    request = json.loads(sys.stdin.read())
    if not isinstance(request, dict): raise ValueError("request is not an object")
    if request.get("mode") == "layout_default_profile_tabs":
        if request.get("titles") != LAYOUT_TITLES: raise ValueError("invalid layout titles")
        response = layout_probe(request)
    elif request.get("mode") == "coordinator_bootstrap" and isinstance(request.get("cwd"), str) and request["cwd"]:
        response = coordinator_bootstrap_probe(request)
    elif request.get("mode") == "coordinator_start" and all(isinstance(request.get(key), str) and request[key] for key in ("cwd", "instruction", "current", "authority")) and isinstance(request.get("command"), list) and request["command"] and all(isinstance(item, str) and item for item in request["command"]):
        response = coordinator_start(request)
    elif request.get("mode") == "role_trigger" and all(isinstance(request.get(key), str) and request[key] for key in ("window", "tab", "session", "payload")):
        response = send_role_trigger(request)
    elif request.get("mode") == "role_label" and all(isinstance(request.get(key), str) and request[key] for key in ("window", "tab", "session", "title")):
        response = update_role_label(request)
    elif request.get("mode") == "staged_role_start" and all(isinstance(request.get(key), str) and request[key] for key in ("window", "title", "command")):
        response = staged_role_start(request)
    elif request.get("mode") == "default_profile_tab_only" and isinstance(request.get("title"), str):
        response = native_probe(request)
    else:
        raise ValueError("invalid native probe request")
except (json.JSONDecodeError, ValueError):
    print(json.dumps({"ok": False, "reason": "malformed native probe request"}, sort_keys=True))
else:
    print(json.dumps(response, sort_keys=True))
