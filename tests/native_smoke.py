"""End-to-end SCPC qualification against REAL SolidCraft 0.30.1.

This is intentionally separate from the mocked Python/GUI-protocol tests:
SCPC Python -> native command JSON -> strict CLI -> editable native .sc ->
actual BRep measurements, feature history and negative command checks.

Usage (native solidcraft-cli 0.30.1 on PATH):
    python tests/native_smoke.py --output-dir output/native-smoke
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ENGINE = "0.30.1"

# Verified physical reference values from the CAD project's independent
# SCPF/SCPC SolidCraft 0.30.1 evaluations. Do not derive them from
# SCPC JSON — they are the expected RESULT of the native geometry.
MODELS = {
    "plate": {
        "command_count": 12,
        "body": "Plate",
        "min": [-50.0, -30.0, 0.0],
        "max": [50.0, 30.0, 10.0],
        "feature_types": [
            "Sketch", "ExtrudeFeature", "FilletFeature",
            "HoleFeature", "HoleFeature", "HoleFeature", "HoleFeature",
        ],
    },
    "corner-bracket": {
        "command_count": 17,
        "body": "CornerBracket",
        "min": [-12.0, -12.0, -60.0],
        "max": [60.0, 12.0, 12.0],
        "volume_mm3": 36771.08743744507,
        "feature_types": [
            "Sketch", "ExtrudeFeature", "FilletFeature",
            "ChamferFeature", "ChamferFeature", "ChamferFeature",
        ],
    },
}


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


def native_registry(output, cli):
    # CLI emits a LIST of real native command records in SolidCraft 0.30.1,
    # including id, label, panel and human-readable native param descriptions.
    reply = run(sys.executable, "-m", "scpc", "--commands", "--cli", cli)
    records = json.loads(reply.stdout)
    assert isinstance(records, list), type(records)
    assert len(records) > 400, f"Native CLI registry unexpectedly small: {len(records)}"
    by_id = {}
    for item in records:
        assert isinstance(item, dict), item
        name = item.get("id")
        assert isinstance(name, str) and name, item
        assert name not in by_id, f"Duplicate native command: {name}"
        assert isinstance(item.get("label"), str), name
        assert isinstance(item.get("params"), str), name
        by_id[name] = item
    (output / "command-registry.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Native SolidCraft command registry: {len(by_id)} unique IDs")
    return by_id


def verify_model(model, config, output, cli, registry):
    folder = output / model
    folder.mkdir(parents=True, exist_ok=True)
    source = ROOT / "examples" / model / "model.py"
    if not source.is_file():
        raise AssertionError(f"Missing independent SCPC example: {source}")
    commands_file = folder / "commands.json"
    native_file = folder / "model.sc"
    measurements_file = folder / "measurements.json"

    # Public Python CLI: the command script is written without running
    # SolidCraft and without importing the Forge model.
    run(sys.executable, "-m", "scpc", source, "--out", commands_file)
    plan = json.loads(commands_file.read_text(encoding="utf-8"))
    commands = plan["commands"]
    assert len(commands) == config["command_count"], (model, len(commands))
    assert all(set(entry) == {"command", "params"}
               and isinstance(entry["params"], dict) for entry in commands)
    for index, entry in enumerate(commands):
        name = entry["command"]
        assert name in registry, (
            f"{model}: step {index} uses unknown SolidCraft command {name!r}"
        )
        # This checks that our tests really can discover native parameter
        # docs from SolidCraft, without maintaining a SCPC command schema.
        assert registry[name]["label"].strip(), (model, name)

    # Execute the SAME Python script through the actual native engine.
    run(sys.executable, "-m", "scpc", source, "--run", "--save",
        native_file, "--cli", cli)
    assert native_file.is_file() and zipfile.is_zipfile(native_file), model
    with zipfile.ZipFile(native_file) as archive:
        design = json.loads(archive.read("document.json"))
        container = json.loads(archive.read("container.json"))
        assert design["format"] == "solidcraft/48"
        assert container["format"] == "solidcraft-container/1"

    run(cli, "eval", native_file, "--json-out", measurements_file)
    measured = json.loads(measurements_file.read_text(encoding="utf-8"))
    assert measured["body_count"] == 1, (model, measured)
    body = measured["bodies"][0]
    assert body["name"] == config["body"], (model, body["name"])
    for bound in ("min", "max"):
        for actual, wanted in zip(body["bbox"][bound], config[bound]):
            assert abs(actual - wanted) < 0.001, (model, bound, actual, wanted)
    if "volume_mm3" in config:
        assert abs(body["volume_mm3"] - config["volume_mm3"]) < 0.01, (
            model, body["volume_mm3"], config["volume_mm3"]
        )
    timeline = measured.get("timeline") or []
    assert timeline, f"{model}: no editable native timeline"
    assert all(entry.get("error") is None for entry in timeline), timeline
    actual_types = [entry["type"] for entry in timeline]
    assert actual_types == config["feature_types"], (
        model, actual_types, config["feature_types"]
    )
    print(f"{model}: {len(commands)} native commands, "
          f"{body['name']} BRep, expected bounds and {len(timeline)} editable features")


def verify_strict_rejection(output, cli):
    # Test both the native CLI's strict semantics AND that SCPC propagates
    # the native failure to its caller, rather than silently returning OK.
    folder = output / "negative-tests"
    folder.mkdir(exist_ok=True)
    invalid_model = folder / "model.py"
    invalid_model.write_text(
        'from scpc import Script\n'
        'script = Script()\n'
        'script.add("scpc.this_is_not_a_solidcraft_command")\n',
        encoding="utf-8",
    )
    rejected = run(sys.executable, "-m", "scpc", invalid_model,
                   "--run", "--cli", cli, must_succeed=False)
    (folder / "invalid-command-result.txt").write_text(
        f"exit_code: {rejected.returncode}\n"
        f"stdout:\n{rejected.stdout}\nstderr:\n{rejected.stderr}",
        encoding="utf-8",
    )
    assert rejected.returncode != 0, "SCPC unexpectedly accepted invalid command"
    assert "SCPC CLI:" in rejected.stderr, (
        "SCPC did not expose the native error", rejected.stderr
    )
    # A VALID command ID with an INVALID parameter must also fail under
    # native --param-check strict. SCPC never keeps its own param tables.
    invalid_params = folder / "invalid-params.py"
    invalid_params.write_text(
        'from scpc import Script\n'
        'script = Script()\n'
        'script.add("sketch.create", plane="XY", scpc_bad_field=123)\n',
        encoding="utf-8",
    )
    rejected_param = run(
        sys.executable, "-m", "scpc", invalid_params,
        "--run", "--cli", cli, must_succeed=False,
    )
    (folder / "invalid-params-result.txt").write_text(
        f"exit_code: {rejected_param.returncode}\n"
        f"stdout:\n{rejected_param.stdout}\nstderr:\n{rejected_param.stderr}",
        encoding="utf-8",
    )
    assert rejected_param.returncode != 0, (
        "SolidCraft's strict checking accepted unknown sketch.create parameter",
        rejected_param.stdout, rejected_param.stderr,
    )
    assert "SCPC CLI:" in rejected_param.stderr
    print("SCPC headless runner: invalid command AND invalid native params rejected")


def verify(output, cli):
    output.mkdir(parents=True, exist_ok=True)
    version = run(cli, "--version").stdout
    if EXPECTED_ENGINE not in version:
        raise AssertionError(
            f"Tests qualify SolidCraft {EXPECTED_ENGINE}; installed CLI: {version!r}"
        )
    print(f"Native SolidCraft: {version.strip()}")
    registry = native_registry(output, cli)
    for name, config in MODELS.items():
        verify_model(name, config, output, cli, registry)
    verify_strict_rejection(output, cli)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="Keep .sc, JSON, measurements and native registry")
    parser.add_argument("--cli", default="solidcraft-cli",
                        help="SolidCraft 0.30.1 CLI executable")
    args = parser.parse_args(argv)
    cli = shutil.which(args.cli)
    if not cli:
        parser.error(f"{args.cli!r} is not on PATH")
    if args.output_dir:
        verify(args.output_dir.resolve(), cli)
    else:
        with tempfile.TemporaryDirectory(prefix="scpc-native-") as folder:
            verify(Path(folder), cli)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
