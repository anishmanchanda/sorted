"""Reject generated code before it ever runs: import allowlist, banned builtins, no dunder access."""

import ast

ALLOWED_IMPORTS = {"re", "datetime", "decimal", "html", "json", "dateutil", "typing"}
BANNED_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr",
    "delattr", "input", "breakpoint", "help", "exit", "quit", "memoryview", "os", "sys", "subprocess",
    "socket", "requests", "shutil", "pathlib", "importlib", "builtins",
}
BANNED_ATTRS = {"system", "popen", "unlink", "remove", "rmdir", "rmtree", "kill", "fork", "spawn"}


def check(code: str) -> list[str]:
    """Problems found; empty list means the code may be run in the sandbox."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    problems = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Import):
            roots = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            roots = [(node.module or "").split(".")[0]] if node.level == 0 else ["<relative>"]
        else:
            roots = []
        problems += [f"line {line}: import of {r!r} not allowed" for r in roots if r not in ALLOWED_IMPORTS]
        if isinstance(node, ast.Name) and (node.id in BANNED_NAMES or node.id.startswith("__")):
            problems.append(f"line {line}: use of {node.id!r} not allowed")
        if isinstance(node, ast.Attribute) and (node.attr.startswith("__") or node.attr in BANNED_ATTRS):
            problems.append(f"line {line}: attribute {node.attr!r} not allowed")
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            problems.append(f"line {line}: global/nonlocal not allowed")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "extract" for n in tree.body):
        problems.append("module must define extract(text)")
    return problems
