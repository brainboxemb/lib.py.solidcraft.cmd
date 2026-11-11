import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from scpc import Script, load_script
from scpc.discovery import commands, describe
from scpc.live import LiveError, send_batch
from scpc.native import run_cli, CliError
from scpc.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


class ScriptTests(unittest.TestCase):
    def test_exact_native_format_and_no_transformations(self):
        script = Script().add("sketch.create", plane="XY", name="Base")
        script.add("sketch.finish")
        self.assertEqual(script.to_dict(), {
            "commands": [
                {"command": "sketch.create", "params": {"plane": "XY", "name": "Base"}},
                {"command": "sketch.finish", "params": {}},
            ]
        })

    def test_parameter_json_detached_and_validated(self):
        values = [1, 2, 3]
        script = Script().add("view.some_future_command", position=values)
        values[0] = 99
        self.assertEqual(script.commands[0]["params"]["position"], [1, 2, 3])
        copy = script.commands
        copy[0]["params"]["position"][1] = 99
        self.assertEqual(script.commands[0]["params"]["position"], [1, 2, 3])
        with self.assertRaises(ValueError):
            script.add("solid.box", width=math.nan)
        with self.assertRaises(TypeError):
            script.add("solid.box", width=object())
        with self.assertRaises(ValueError):
            script.add("", width=1)
        self.assertEqual(len(script), 1)

    def test_export_cli_runner(self):
        src = ROOT / "examples/plate/model.py"
        script = load_script(src)
        self.assertEqual(len(script), 12)
        self.assertEqual(script.commands[-1]["command"], "solid.hole")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "out/plate.json"
            self.assertEqual(main([str(src), "--out", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), script.to_dict())

    def test_require_one_nonempty_script(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "model.py"
            p.write_text("from scpc import Script\na = Script()\nb = Script()\n")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                load_script(p)
            p.write_text("from scpc import Script\nscript = Script()\n")
            with self.assertRaisesRegex(ValueError, "contains no commands"):
                load_script(p)

    def test_cli_native_strict_not_python_validator(self):
        script = Script().add("sketch.create", plane="XY")
        runner_result = Mock(returncode=0, stdout="{}", stderr="")
        with patch("scpc.native.shutil.which", return_value="/bin/solidcraft-cli"), \
             patch("scpc.native.subprocess.run", return_value=runner_result) as runner:
            self.assertEqual(run_cli(script, save="out/design.sc"), "{}")
            args = runner.call_args.args[0]
            self.assertEqual(args[1], "run")
            self.assertIn("--param-check", args)
            self.assertIn("strict", args)
            self.assertIn("--save", args)
        with patch("scpc.native.shutil.which", return_value=None):
            with self.assertRaisesRegex(CliError, "not found"):
                run_cli(script)


class DiscoveryTests(unittest.TestCase):
    def test_registry_comes_from_native_cli(self):
        fake = Mock(returncode=0, stdout='{"commands":[{"id":"solid.extrude"}]}')
        with patch("scpc.discovery.shutil.which", return_value="cli"), \
             patch("scpc.discovery.subprocess.run", return_value=fake) as run:
            self.assertEqual(commands()["commands"][0]["id"], "solid.extrude")
            self.assertEqual(run.call_args.args[0], ["cli", "commands"])

    def test_command_schema_comes_from_live_engine(self):
        with patch("scpc.discovery.request", return_value={"input_schema": {}}) as req:
            self.assertEqual(describe("solid.extrude"), {"input_schema": {}})
            self.assertEqual(req.call_args.args[0], "engine.describe")
            self.assertEqual(req.call_args.kwargs["params"], {"command": "solid.extrude"})

    def test_batch_uses_native_strict_and_rollback(self):
        cmd = Script().add("sketch.finish").commands
        with patch("scpc.live.request", return_value={"completed": 1}) as req:
            send_batch(cmd)
            self.assertEqual(req.call_args.kwargs["params"], {
                "commands": cmd, "rollback": True, "param_check": "strict"
            })
        with patch("scpc.live.request", return_value={
            "completed": 0,
            "failed": {"index": 0, "command": "sketch.finish", "error": "bad"},
            "rolled_back": True
        }):
            with self.assertRaisesRegex(LiveError, "rolled back: True"):
                send_batch(cmd)


class ExampleModelTests(unittest.TestCase):
    def test_native_examples_are_independent_and_readable(self):
        for slug, count, expected_body in (
            ("plate", 12, "Plate"),
            ("corner-bracket", 17, "CornerBracket"),
        ):
            with self.subTest(slug=slug):
                source = ROOT / "examples" / slug / "model.py"
                text = source.read_text(encoding="utf-8")
                # Examples are not Forge-output wrappers or copies of JSON.
                self.assertIn("script.add(", text)
                self.assertNotIn("from scpf", text)
                self.assertNotIn("json.load(", text)
                native = load_script(source).to_dict()["commands"]
                self.assertEqual(len(native), count)
                extrusions = [
                    item["params"]["body_name"] for item in native
                    if item["command"] == "solid.extrude"
                ]
                self.assertEqual(extrusions, [expected_body])
                self.assertTrue(all(
                    set(item) == {"command", "params"} for item in native
                ))

    def test_corner_bracket_uses_exact_native_selection_and_features(self):
        path = ROOT / "examples/corner-bracket/model.py"
        commands = load_script(path).commands
        kinds = [item["command"] for item in commands]
        self.assertEqual(kinds.count("solid.fillet"), 1)
        self.assertEqual(kinds.count("solid.chamfer"), 3)
        self.assertEqual(kinds.count("solid.hole"), 0)
        fillet = next(item["params"] for item in commands
                      if item["command"] == "solid.fillet")
        self.assertEqual(fillet["radius"], 4)
        self.assertEqual(fillet["edges"], [[0, 0, 0]])
        sketch = next(item["params"] for item in commands
                      if item["command"] == "sketch.line")
        self.assertEqual(len(sketch["points"]), 9)
        self.assertTrue(sketch["closed"])
        self.assertEqual(len(sketch["ids"]), 9)


if __name__ == "__main__":
    unittest.main()
