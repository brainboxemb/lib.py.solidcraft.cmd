# Testing SCPC — from Python calls to real SolidCraft geometry

There are three separate questions to answer when developing SCPC:

1. **Is the Python API correct?** Does `Script.add()` preserve the
   original native command ID and parameters, generate valid JSON and
   report useful errors?
2. **Does the control protocol work?** Does the client send correctly
   authenticated `engine.describe` and `engine.batch` messages,
   request strict validation and rollback, and relay native failures?
3. **Does SolidCraft actually build the intended model?** Does the
   installed native CLI accept the commands, save an editable `.sc`
   document, and evaluate the correct geometry and feature history?

These are **different tests**. Passing the Python tests is not evidence
that a model can be built by the native CAD engine.

## A. Offline Python + control-protocol tests

In your existing PowerShell/Conda environment, from the SCPC repository:

```powershell
conda activate brainboxemb-dev-tools
python -m pip install -e .
.\scripts\test.ps1
```

Or directly:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests cover the `Script` API, JSON immutability, model script
loading, command discovery plumbing, headless CLI argument construction
and authenticated live-control messages. GitHub Actions runs the documented
`scripts/test.ps1` on a **real Windows runner** as well as running the
Python tests on Linux. This detects Windows-specific installation, path
and PowerShell problems before the local developer has to diagnose them.

The live-control tests use a **local fake TCP endpoint** with temporary
`current.port` and token files. They test *real socket serialization*
without requiring an open SolidCraft GUI and without modifying a CAD
document. They intentionally do **not** simulate geometry.

## B. Real native SolidCraft 0.30.1 test

With `solidcraft-cli` on PATH:

```powershell
.\scripts\test.ps1 -Native
```

Or just the native qualification:

```powershell
python tests/native_smoke.py --output-dir output/native-smoke
```

The test performs this sequence:

- Confirm the installed SolidCraft CLI reports **0.30.1**.
- Call `python -m scpc --commands` and verify the actual engine
  advertises the native commands used by the example.
- Generate both the Plate and CornerBracket native command JSON directly
  from their independent `examples/<model>/model.py` files.
- Run **both** SCPC Python scripts in the **real SolidCraft engine**
  with strict native parameter validation, saving a separate `model.sc`
  in each model's directory.
- Confirm `plate.sc` is a valid native SolidCraft document.
- Evaluate both actual BReps: **Plate** has a 100 × 60 × 10 mm
  bounding box and 7 features; **CornerBracket** has X=−12..60,
  Y=−12..12, Z=−60..12 mm, approximately 36,771.09 mm³ of material,
  and 6 features (sketch, extrusion, fillet, three chamfers). These
  expected results come from independent native SolidCraft runs, not
  from the JSON itself.
- Deliberately run a Python SCPC script with an unknown native command
  and verify that **SCPC propagates SolidCraft's failure**. A JSON
  document being well formed is not sufficient.
- Confirm that **every command used** in both scripts is advertised
  by the current native `solidcraft-cli commands` registry and that
  it comes with a label and parameter documentation.

The output contains `plate/` and `corner-bracket/` with their own
  `model.sc`, `commands.json` and `measurements.json`. At the root are
  the authoritative `command-registry.json` and the
  `negative-tests/invalid-command-result.txt` report.

GitHub Actions runs these same tests using the official
**v0.30.1 Linux release**, downloaded and checksum-verified against
the release's `SHA256SUMS.txt`.

## C. Two independent CAD implementations

The [CAD project](https://github.com/brainboxemb/2026-011-02.cad.solidcraft)
has separate files for `models/basic/plate/scpf/model.py` and
`models/basic/plate/scpc/model.py`, and likewise for CornerBracket.

The CAD project's native CI builds both scripts independently with
SolidCraft 0.30.1 and compares their evaluated geometry and feature
timelines. SCPC must **never** read the JSON produced by SCPF. That
would test only serialization, not whether SCPC is actually usable.

## D. What remains manual

The live `--connect` function talks to a **running SolidCraft GUI**.
The fake-socket tests check its wire protocol, but cannot prove that
the installed GUI accepts a live batch or displays the resulting solid.

To test that locally, open a **new empty document** in SolidCraft,
enable the Assistant/agent connection preference, then:

```powershell
python -m scpc examples/plate/model.py --connect
```

Check the active document, features and body. SCPC does not start,
save or clear a GUI document automatically.

Similarly, `engine.describe` uses the **live** control channel;
the headless native test verifies `engine.commands` but does not
claim that native schemas from a running desktop GUI were exercised.

## Boundaries for future API development

Keep the public Python command surface small and direct:
`Script.add(native_id, **native_parameters)` is the core.
Prefer dynamic `engine.commands` / `engine.describe` to maintaining
hundreds of generated Python wrapper methods or parameter tables.
**All CAD geometry, edge selection and validation are SolidCraft's job.**
For each new API ability, add an offline test and, where CAD behavior
matters, an actual native CLI integration test.

## Important limitation of native strict checking (SolidCraft 0.30.1)

The native CLI's `--param-check strict` is useful but **not a complete
rejection of every unknown argument key**. In our real-engine test, an
extra `scpc_bad_field=123` on `sketch.create` was accepted and ignored.
This is native SolidCraft behavior, not something SCPC repairs.

The test stores `negative-tests/unknown-parameter-result.txt` to make
that behavior visible; it separately checks an unknown **command ID**
is rejected. Do not claim that a green `--param-check strict` proves
every parameter name is valid. For critical models, verify the evaluated
native geometry and feature timeline as well.
