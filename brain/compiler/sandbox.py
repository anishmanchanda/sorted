"""Run generated code in a separate subprocess: empty environment (no API keys, no proxies), sockets
disabled before the ability is imported, CPU/file-size rlimits, a temp working directory and a timeout.

ponytail: process-level isolation only. A Docker `--network none` container is the planned upgrade.
"""

import json
import os
import resource
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER = r'''
import io, json, socket, sys

def _blocked(*a, **k):
    raise PermissionError("network is disabled in the sandbox")

socket.socket = socket.create_connection = socket.getaddrinfo = socket.socketpair = _blocked
sys.path.insert(0, sys.argv[1])
inputs = json.load(sys.stdin)
real_stdout, sys.stdout = sys.stdout, io.StringIO()
results = []
try:
    import ability
    for text in inputs:
        try:
            results.append({"ok": True, "value": ability.extract(text)})
        except Exception as e:
            results.append({"ok": False, "error": f"{type(e).__name__}: {e}"[:300]})
except Exception as e:
    results = [{"ok": False, "error": f"import failed: {type(e).__name__}: {e}"[:300]} for _ in inputs]
sys.stdout = real_stdout
print(json.dumps(results, default=str))
'''


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))


def run(code: str, inputs: list[str], timeout: float = 15.0) -> list[dict]:
    """[{ok: True, value: ...} | {ok: False, error: str}] per input."""
    with tempfile.TemporaryDirectory(prefix="sorted-sandbox-") as tmp:
        Path(tmp, "ability.py").write_text(code)
        Path(tmp, "runner.py").write_text(RUNNER)
        env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
        try:
            proc = subprocess.run([sys.executable, "-I", str(Path(tmp, "runner.py")), tmp], input=json.dumps(inputs),
                                  capture_output=True, text=True, cwd=tmp, env=env, timeout=timeout,
                                  preexec_fn=_limits)
        except subprocess.TimeoutExpired:
            return [{"ok": False, "error": f"timeout after {timeout}s"} for _ in inputs]
        if proc.returncode != 0:
            return [{"ok": False, "error": f"sandbox exited {proc.returncode}: {proc.stderr[-300:]}"} for _ in inputs]
        return json.loads(proc.stdout)
