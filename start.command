#!/bin/bash
# macOS launcher. Also usable as: bash /path/to/Product/start.command
set -eu
PRODUCT_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="$PRODUCT_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ] || ! "$PYTHON" -c 'import flask' >/dev/null 2>&1; then
    echo 'Create the macOS Python environment first:'
    printf 'cd %q\n' "$PRODUCT_ROOT"
    echo 'python3 -m venv .venv'
    echo '.venv/bin/python -m pip install -r backend/requirements.txt'
    echo 'A Windows virtual environment cannot be reused on macOS.'
    exit 1
fi
exec "$PYTHON" - "$PRODUCT_ROOT" <<'PY'
import json
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

root = Path(sys.argv[1])
url = 'http://127.0.0.1:5000/'
process = None
logs = []
exit_code = 0

def interrupted(signum, frame):
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)
try:
    # Fail before launching; never stop an unrelated listener.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(('0.0.0.0', 5000))
        except OSError as error:
            raise RuntimeError('Port 5000 is unavailable. Stop the existing server or free the port, then retry. On macOS, AirPlay Receiver may use this port.') from error
    log_dir = root / 'startup-logs'
    log_dir.mkdir(exist_ok=True)
    run = uuid.uuid4().hex
    logs = [log_dir / f'{run}.stdout.log', log_dir / f'{run}.stderr.log']
    with logs[0].open('w', encoding='utf-8') as stdout, logs[1].open('w', encoding='utf-8') as stderr:
        process = subprocess.Popen([sys.executable, '-u', str(root / 'backend' / 'app.py')],
                                   cwd=root, stdout=stdout, stderr=stderr, start_new_session=True)
    deadline = time.monotonic() + 15
    ready = False
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Backend exited during startup (code {process.returncode}).')
        try:
            with opener.open(url + 'api/health', timeout=min(1, max(.01, deadline - time.monotonic()))) as response:
                health = json.load(response)
            ready = health.get('status') == 'ok' and health.get('dataset_loaded') is True
        except (OSError, ValueError):
            ready = False
        if ready:
            break
        time.sleep(.2)
    if not ready:
        raise RuntimeError('Backend did not become ready within 15 seconds.')
    if process.poll() is not None:
        raise RuntimeError('Backend exited before the browser could open.')
    print(f'Ready: {url} — keep this terminal open; press Ctrl+C to stop.', flush=True)
    try:
        subprocess.run(['open', url], check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        print(f'Could not open the browser. Open {url} manually.', flush=True)
    while process.poll() is None:
        time.sleep(.25)
    if process.returncode:
        raise RuntimeError(f'Backend exited with code {process.returncode}.')
except KeyboardInterrupt:
    print('\nStopping the backend started by this launcher.')
except Exception as error:
    exit_code = 1
    print(f'Startup error: {error}', file=sys.stderr)
    if logs and logs[1].exists():
        print('\n'.join(logs[1].read_text(encoding='utf-8', errors='replace').splitlines()[-15:]), file=sys.stderr)
finally:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for path in logs:
        print(f'Backend log: {path}')
sys.exit(exit_code)
PY
