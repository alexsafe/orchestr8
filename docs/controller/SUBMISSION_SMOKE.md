# Disposable interactive submission smoke

Use only after authorization for a disposable Codex session and its provider request. This is a single transport attempt, not a project task or supervised cycle. It does not prove a full workflow.

1. Create an empty directory with `mktemp -d /private/tmp/orchestr8-input-XXXXXX`. In one new iTerm tab, run `codex -s read-only -C <that-directory>`. Wait until the interactive input is ready. Do not enter a prompt. Codex may retain its normal session records and contact its configured provider.
2. From a separate control terminal in the source checkout, use the existing `.venv` and list iTerm destinations with the command below. Visually identify the new tab and its session; stop if its IDs cannot be identified unambiguously. Do not use an existing role or smoke tab.

```sh
.venv/bin/python - <<'PY'
import iterm2
async def main(connection):
    app = await iterm2.async_get_app(connection)
    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                print('window=', window.window_id, 'tab=', tab.tab_id,
                      'session=', session.session_id,
                      'name=', await session.async_get_variable('name'),
                      'job=', await session.async_get_variable('jobName'))
iterm2.run_until_complete(main)
PY
```

3. In the control terminal, set `WINDOW_ID`, `TAB_ID` and `SESSION_ID` to those exact IDs. Run this command **once**; it prints the unique marker and the bridge's JSON response. Do not manually enter the prompt or press Enter in the Codex tab.

```sh
WINDOW_ID='<window ID>' TAB_ID='<tab ID>' SESSION_ID='<session ID>' .venv/bin/python - <<'PY'
import json, os, subprocess, uuid
marker = 'ORCH8_DIAG_' + uuid.uuid4().hex
request = {'mode': 'role_trigger', 'window': os.environ['WINDOW_ID'],
           'tab': os.environ['TAB_ID'], 'session': os.environ['SESSION_ID'],
           'payload': f'Reply exactly {marker}. Do not use tools or write files.'}
print('Expected marker:', marker, flush=True)
result = subprocess.run(['.venv/bin/python', '.agent/iterm_probe.py'],
                        input=json.dumps(request), text=True, capture_output=True, timeout=15)
print('Bridge exit:', result.returncode, 'stdout:', result.stdout, 'stderr:', result.stderr)
PY
```

4. Observe the intended tab. Record the bridge JSON, destination IDs, marker, and the visible result. `sends` contains each response status and monotonic start/end times in seconds; their difference is the call duration. Confirm exactly one text send and one Return, both `OK`, with at least one second between the text response and the Return request. The bridge waits one second after the text response, then rechecks the destination and foreground job before sending Return. This delay is a candidate, not an established Codex threshold. Two `OK` statuses acknowledge iTerm requests only. **Observed submission** requires the human to see Codex start processing without Enter. **Observed completion** requires seeing the requested marker as Codex's response. Neither is automatically acknowledged by the bridge. No visible processing within 60 seconds, a wrong destination, an error or a missing/non-OK status is a failure or inconclusive result. Preserve the evidence and do not resend, manually submit, or retry.
5. Close the disposable tab after recording observations. Remove the temporary directory with `rmdir <that-directory>` only if empty; preserve any unexpected contents for inspection. Do not modify existing smoke targets or controller runtime.
