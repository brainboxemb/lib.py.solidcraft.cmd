"""SCPC end-to-end qualification against a REAL SolidCraft CLI (0.30.1).

Unlike the fast unit tests, this deliberately downloads/uses native SolidCraft
in CI. It verifies registry discovery, SCPC Python -> JSON -> editable .sc
and the actual evaluated BRep/feature timeline. It also proves an invalid
native command is rejected. No GUI and no Forge dependency are needed.

Use locally after installing SCPC and solidcraft-cli 0.30.1:
    python tests/native_smoke.py --output-dir output/native-smoke
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ENGINE = "0.30.1"


def run(*args, timeout=180, must_succeed=True):
    result = subprocess.run(
        [str(arg) for arg in args],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout,
    )
    if must_succeed and result.returncode:
        raise AssertionError(
            f"Command failed (exit {result.returncode}): {args!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def command_ids(payload):
    """Walk *native* registry JSON without assuming a specific wrapper key."""
    if isinstance(payload, dict):
        if isinstance(payload.get("id"), str):
            yield payload["id"]
        for value in payload.values():
            yield from command_ids(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from command_ids(value)


def verify(output, cli):
    output.mkdir(parents=True, exist_ok=True)

    version = run(cli, "--version").stdout
    if EXPECTED_ENGINE not in version:
        raise AssertionError(
            f"Tests qualify SolidCraft {EXPECTED_ENGINE}; installed CLI: {version!r}"
        )
    print(f"SolidCraft CLI: {version.strip()}")

    # Native registry: inspect the real installed engine instead of using a
    # frozen Python list of commands or parameters.
    registry_result = run(sys.executable, "-m", "scpc", "--commands", "--cli", cli)
    registry = json.loads(registry_result.stdout)
    (output / "command-registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ids = set(command_ids(registry))
    for needed in (
        "parameters.add", "sketch.create", "sketch.rectangle.two_point",
        "sketch.finish", "solid.extrude", "solid.fillet", "solid.hole",
    ):
        if needed not in ids:
            raise AssertionError(f"Installed native engine does not advertise {needed}")
    print(f"Native command registry: {len(ids)} IDs, Plate commands present")

    example = ROOT / "examples/plate/model.py"
    commands_file = output / "plate.json"
    native_file = output / "plate.sc"
    measurements_file = output / "measurements.json"

    # Exercise SCPC's *public CLI*, not only the in-process Script helper.
    run(sys.executable, "-m", "scpc", example, "--out", commands_file)
    document = json.loads(commands_file.read_text(encoding="utf-8"))
    assert len(document["commands"]) == 12
    assert [c["command"] for c in document["commands"][-4:]] == ["solid.hole"] * 4

    # The same trusted Python script is executed in the real native engine.
    # No custom Python geometry, matrices or simulated CAD.
    run(sys.executable, "-m", "scpc", example, "--run", "--save", native_file,
        "--cli", cli)
    assert native_file.is_file() and zipfile.is_zipfile(native_file)
    with zipfile.ZipFile(native_file) as archive:
        design = json.loads(archive.read("document.json"))
        container = json.loads(archive.read("container.json"))
        assert design["format"] == "solidcraft/48", design.get("format")
        assert container["format"] == "solidcraft-container/1"

    run(cli, "eval", native_file, "--json-out", measurements_file)
    measured = json.loads(measurements_file.read_text(encoding="utf-8"))
    assert measured["body_count"] == 1, measured
    body = measured["bodies"][0]
    assert body["name"] == "Plate", body["name"]
    for bound, expected in (
        ("min", [-50, -30, 0]), ("max", [50, 30, 10])
    ):
        for actual, wanted in zip(body["bbox"][bound], expected):
            assert abs(actual - wanted) < 0.001, (bound, actual, wanted)
    timeline = measured.get("timeline") or []
    assert timeline, "The saved native design contains no editable feature timeline"
    assert all(item.get("error") is None for item in timeline), timeline
    print("Native .sc document: one real Plate body, 100×60×10 mm, editable history")

    # Exercise native strict failure, not just JSON syntax validation.
    bad = output / "invalid-command.json"
    bad.write_text(json.dumps({
        "commands": [{"command": "scpc.this_is_not_a_solidcraft_command",
                      "params": {}}],
    }) + "\n", encoding="utf-8")
    rejected = run(cli, "run", bad, "--param-check", "strict",
                   must_succeed=False)
    (output / "invalid-command-result.txt").write_text(
        f"exit_code: {rejected.returncode}\n"
        f"stdout:\n{rejected.stdout}\nstderr:\n{rejected.stderr}",
        encoding="utf-8",
    )
    assert rejected.returncode != 0, (
        "The native CLI unexpectedly accepted an invalid command",
        rejected.stdout, rejected.stderr,
    )
    print("Native strict validation: invalid command correctly rejected")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="Keep native design, JSON, measurements and registry")
    parser.add_argument("--cli", default="solidcraft-cli",
                        help="SolidCraft 0.30.1 CLI executable")
    options = parser.parse_args(argv)
    cli = shutil.which(options.cli)
    if not cli:
        parser.error(f"{options.cli!r} is not on PATH")
    if options.output_dir:
        verify(options.output_dir.resolve(), cli)
    else:
        with tempfile.TemporaryDirectory(prefix="scpc-native-test-") as folder:
            verify(Path(folder), cli)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
