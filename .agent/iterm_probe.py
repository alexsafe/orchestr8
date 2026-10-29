#!/usr/bin/env python3
"""One-tab native iTerm2 probe bridge; reads one JSON request, writes one JSON response."""
import asyncio, json, sys, time

def probe(request):
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

try:
    request = json.loads(sys.stdin.read())
    if not isinstance(request, dict) or not isinstance(request.get("title"), str): raise ValueError("missing title")
except (json.JSONDecodeError, ValueError):
    print(json.dumps({"ok": False, "reason": "malformed native probe request"}, sort_keys=True))
else:
    print(json.dumps(probe(request), sort_keys=True))
