"""Exercise the actual newline-delimited control transport without the GUI.

These tests use a tiny local *fake* SolidCraft endpoint. They test SCPC's
authentication, request format and error handling — not CAD geometry.
The separate native smoke test uses the real SolidCraft engine.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from scpc.live import LiveError, request, send_batch


@contextmanager
def fake_host(answer):
    """Start one local socket conversation, with its own token and port files."""
    with tempfile.TemporaryDirectory() as folder:
        control = Path(folder)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(3)
        port = listener.getsockname()[1]
        (control / "current.port").write_text(str(port), encoding="ascii")
        (control / f"{port}.token").write_text("test-token", encoding="ascii")
        requests = []
        errors = []

        def serve():
            try:
                with listener.accept()[0] as client:
                    client.settimeout(3)
                    with client.makefile("rb") as stream:
                        request_data = json.loads(stream.readline())
                    requests.append(request_data)
                    reply = answer(request_data) if callable(answer) else answer
                    if reply is not None:
                        client.sendall(
                            json.dumps(reply).encode("utf-8") + b"\n"
                        )
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            yield control, requests
        finally:
            listener.close()
            thread.join(timeout=4)
            if thread.is_alive():
                raise AssertionError("Fake SolidCraft host did not terminate")
            if errors:
                raise AssertionError(f"Fake host crashed: {errors!r}")


class NativeControlContract(unittest.TestCase):
    def test_describe_uses_authenticated_local_protocol(self):
        native_schema = {
            "command": "solid.extrude",
            "input_schema": {"type": "object", "properties": {"distance": {}}},
        }
        with fake_host({"id": 1, "ok": True, "result": native_schema}) as (
            directory, captured
        ):
            with patch.dict("os.environ", {"SOLIDCRAFT_CONTROL_DIR": str(directory)}):
                result = request("engine.describe", params={"command": "solid.extrude"},
                                 timeout=3)
        self.assertEqual(result, native_schema)
        self.assertEqual(captured, [{
            "id": 1,
            "method": "engine.describe",
            "token": "test-token",
            "params": {"command": "solid.extrude"},
        }])

    def test_batch_contains_exact_command_plan_strict_and_rollback(self):
        commands = [
            {"command": "sketch.create", "params": {"plane": "XY"}},
            {"command": "sketch.finish", "params": {}},
        ]
        with fake_host({"id": 1, "ok": True, "result": {"completed": 2}}) as (
            directory, captured
        ):
            result = send_batch(commands, directory=directory)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(captured[0]["method"], "engine.batch")
        self.assertEqual(captured[0]["token"], "test-token")
        self.assertEqual(captured[0]["params"], {
            "commands": commands, "rollback": True, "param_check": "strict"
        })

    def test_native_failed_step_propagates_error_and_rollback_status(self):
        failure = {
            "id": 1, "ok": True,
            "result": {"completed": 0, "failed": {
                "index": 0, "command": "solid.extrude", "error": "no sketch",
            }, "rolled_back": True},
        }
        with fake_host(failure) as (directory, _):
            with self.assertRaisesRegex(LiveError, "solid.extrude: no sketch"):
                send_batch([{"command": "solid.extrude", "params": {}}],
                           directory=directory)

    def test_authentication_and_protocol_failures_are_explicit(self):
        with fake_host({"id": 1, "ok": False, "error": "invalid token"}) as (
            directory, _
        ):
            with self.assertRaisesRegex(LiveError, "invalid token"):
                request("engine.commands", directory=directory, timeout=3)

        with fake_host({"id": 17, "ok": True, "result": {}}) as (
            directory, _
        ):
            with self.assertRaisesRegex(LiveError, "Unexpected SolidCraft reply"):
                request("engine.commands", directory=directory, timeout=3)

    def test_no_gui_connection_for_invalid_input(self):
        with self.assertRaisesRegex(LiveError, "1..10000"):
            send_batch([])
        with self.assertRaisesRegex(LiveError, "Invalid native command"):
            send_batch([{"params": {}}])


if __name__ == "__main__":
    unittest.main()
