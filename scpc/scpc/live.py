"""Small client for SolidCraft's *existing* authenticated local control API.

Calls `engine.describe` and `engine.batch` directly. It does not
invent a Python-side CAD evaluator or transform command parameters.
"""
import json
import os
from pathlib import Path
import socket
import sys


class LiveError(RuntimeError):
    """SolidCraft desktop connection or native command failed."""


def _control_dir():
    if os.environ.get("SOLIDCRAFT_CONTROL_DIR"):
        return Path(os.environ["SOLIDCRAFT_CONTROL_DIR"]).expanduser()
    if sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA")
        if not appdata:
            raise LiveError("LOCALAPPDATA is not defined")
        return Path(appdata) / "SolidCraft" / "control"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/SolidCraft/control"
    return Path(os.environ.get("XDG_DATA_HOME",
                               str(Path.home() / ".local/share"))) / "solidcraft/control"


def _port(connect, directory):
    if connect in (True, "auto"):
        file = directory / "current.port"
        try:
            result = int(file.read_text(encoding="ascii").strip())
        except (OSError, ValueError) as exc:
            raise LiveError(
                f"No SolidCraft port in {file}. Start the GUI and enable "
                "Preferences > Assistant > Let AI agents connect."
            ) from exc
    else:
        value = str(connect)
        if value.startswith("127.0.0.1:"):
            value = value.removeprefix("127.0.0.1:")
        try:
            result = int(value)
        except ValueError as exc:
            raise LiveError("Use --connect [127.0.0.1:]PORT") from exc
    if not 1 <= result <= 65535:
        raise LiveError(f"Invalid SolidCraft control port {result}")
    return result


def request(method, *, params=None, connect="auto", directory=None, timeout=3610):
    """Send one request to the native GUI; no implicit doc.new/save."""
    control = Path(directory) if directory else _control_dir()
    port = _port(connect, control)
    token = os.environ.get("SOLIDCRAFT_CONTROL_TOKEN")
    if not token:
        token_file = control / f"{port}.token"
        try:
            token = token_file.read_text(encoding="ascii").strip()
        except OSError as exc:
            raise LiveError(f"Missing SolidCraft token at {token_file}") from exc
    if not token:
        raise LiveError("Empty SolidCraft authentication token")
    data = {"id": 1, "method": method, "token": token}
    if params is not None:
        data["params"] = params
    payload = (json.dumps(data, allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")
    if len(payload) > 16 * 1024 * 1024:
        raise LiveError("Control request is larger than 16 MiB")
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.settimeout(timeout)
            client.sendall(payload)
            with client.makefile("rb") as stream:
                line = stream.readline(16 * 1024 * 1024 + 1)
    except (OSError, socket.timeout) as exc:
        if isinstance(exc, socket.timeout):
            raise LiveError(
                "SolidCraft timed out. The command may still be running; "
                "inspect the GUI before retrying."
            ) from exc
        raise LiveError(f"Cannot connect to SolidCraft GUI: {exc}") from exc
    if not line or len(line) > 16 * 1024 * 1024:
        raise LiveError("Invalid or oversized SolidCraft response")
    try:
        reply = json.loads(line)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LiveError("Invalid JSON from SolidCraft") from exc
    if reply.get("id") != 1 or "ok" not in reply:
        raise LiveError(f"Unexpected SolidCraft reply: {reply!r}")
    if not reply["ok"]:
        raise LiveError(f"SolidCraft rejected {method}: {reply.get('error', reply)}")
    return reply.get("result")


def send_batch(commands, *, connect="auto", directory=None, rollback=True):
    """Apply native commands to the ACTIVE GUI design, with rollback on failure."""
    if not isinstance(commands, list) or not 1 <= len(commands) <= 10000:
        raise LiveError("engine.batch requires 1..10000 commands")
    for index, entry in enumerate(commands):
        if (not isinstance(entry, dict)
                or not isinstance(entry.get("command"), str)
                or not isinstance(entry.get("params", {}), dict)):
            raise LiveError(f"Invalid native command entry at index {index}")
    result = request("engine.batch", params={
        "commands": commands, "rollback": rollback, "param_check": "strict",
    }, connect=connect, directory=directory)
    if not isinstance(result, dict):
        raise LiveError(f"Malformed engine.batch result: {result!r}")
    if "failed" in result:
        fail = result["failed"]
        raise LiveError(
            f"Native command failed at step {fail.get('index')}: "
            f"{fail.get('command')}: {fail.get('error')}; "
            f"rolled back: {result.get('rolled_back')}"
        )
    if result.get("completed") != len(commands):
        raise LiveError(
            f"Native batch completed only {result.get('completed')} "
            f"of {len(commands)} commands"
        )
    return result
