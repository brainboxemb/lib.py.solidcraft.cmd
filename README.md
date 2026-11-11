# SCPC — SolidCraft Python Commands

**Documentation and verified examples:** [SCPC GitHub Pages](https://brainboxemb.github.io/lib.py.solidcraft.cmd/) · [API](https://brainboxemb.github.io/lib.py.solidcraft.cmd/guide/api/) · [Tests](https://brainboxemb.github.io/lib.py.solidcraft.cmd/guide/testing/)

**Native SolidCraft commands, written conveniently in Python.** This
repository is separate from
[SCPF — SolidCraft Python Forge](https://github.com/brainboxemb/lib.py.solidcraft.forge).

SCPC is deliberately thin: it creates the same `{"commands":[{"command":...,"params":...}]}`
structure that SolidCraft accepts. **All command IDs and parameter names are
native SolidCraft names.** SCPC does not calculate CAD geometry, implement
transformation matrices or define a second modelling API.

## Install

From this repository root in your existing Conda/Python environment:

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Test the API and scripts before building a UI

For local development, run **fast Python and local-control protocol tests**
without opening SolidCraft:

```powershell
.\scripts\test.ps1
```

To also test with your installed **native SolidCraft 0.30.1** CLI:

```powershell
.\scripts\test.ps1 -Native
```

The native test runs our Plate Python script through the actual CAD engine,
saves editable `.sc` documents for **Plate and CornerBracket**, measures
both geometries, checks their complete feature timelines and verifies that SolidCraft **rejects invalid commands and parameters**.
It also checks that native command discovery comes from the installed CLI.

GitHub Actions independently runs **both** test levels on every PR:
an offline Python/socket suite and a verified native SolidCraft 0.30.1 run.
The CAD models repository additionally compares the separately authored
SCPF and SCPC Plate and CornerBracket geometries.

See the small [public Python API reference](docs/api.md) and the
[testing instructions and test coverage](docs/testing.md).
The future VS Code Command Explorer is deliberately out of scope for now.

## Write a native SolidCraft model

```python
from scpc import Script

script = Script()
script.add("sketch.create", plane="XY", name="Base")
script.add("sketch.rectangle.two_point",
           p0=[0, 0], p1=[100, 60])
script.add("sketch.finish")
script.add("solid.extrude", distance="10 mm", body_name="Plate")
```

There is **no** `main()` or `show()`; simply define exactly one
`Script` instance called `script` (or any other variable name).
Study both native command models:
[Plate](examples/plate/model.py) — a sketch, extrusion, R2 fillet and
four holes; and [CornerBracket](examples/corner-bracket/model.py) — a
named polygonal sketch, symmetric extrusion, R4 fillet and three chamfers.
They use the same small SCPC API, with no Forge dependency.

Export native JSON without starting SolidCraft:

```powershell
python -m scpc examples/plate/model.py --out output/plate.json
# or: scpc examples/plate/model.py --out output/plate.json
```

Run the same script with the installed native SolidCraft CLI, using
**strict parameter validation**:

```powershell
python -m scpc examples/plate/model.py --run --save output/plate.sc
```

Or apply to an **already open, empty** SolidCraft desktop design using
its authenticated local control channel:

```powershell
python -m scpc examples/plate/model.py --connect
```

This does not launch SolidCraft or save the active design. For a failed
batch, SolidCraft normally rolls back the changes.

## Learn the official command API

```powershell
# Read all native command IDs and documentation from your installed version
python -m scpc --commands

# With a connected SolidCraft GUI, inspect a command's native schema
python -m scpc --describe solid.extrude
```

These use **`solidcraft-cli commands`** (`engine.commands`) and
**`engine.describe`**, respectively. SCPC does not keep a hardcoded
command catalog. Therefore the authority for parameters, units and
validation remains the installed SolidCraft engine.

## GitHub Pages documentation

The [SCPC library website](https://brainboxemb.github.io/lib.py.solidcraft.cmd/)
is built automatically from this repository's Python source and Markdown guides.
It publishes native-verified models (editable `.sc`, commands, renders and
feature histories) only from the **same checked-out and verified source commit**.

Pages deployment is a separate CI job: Python, Windows PowerShell and real
SolidCraft 0.30.1 tests must all succeed before the site builds and
publishes to the `gh-pages` branch. The page builder uses
`site/requirements.txt` and `site/build.py`. See `site/test_site.py`
for the source/provenance and internal-link checks.

The [brainboxemb homepage](https://brainboxemb.github.io/) already has a
**SolidCraft Commands** link beside Forge and the CAD models. GitHub Pages
must have its publishing source set to `gh-pages` / `/ (root)`.

## What comes next

The CAD repository
[2026-011-02.cad.solidcraft](https://github.com/brainboxemb/2026-011-02.cad.solidcraft)
already has independent `scpf/model.py` and `scpc/model.py` variants
for Plate and CornerBracket.
The latter must describe native commands *directly*, not simply load
Forge's generated JSON. CI should compare real native geometry and
editable history, not merely compare whether JSON parses.

A future **Command Explorer** can search `engine.commands`, query
`engine.describe`, present parameter forms, export a Python SCPC script
and execute native commands. A separate UI is optional; it should be
based on the command schemas, not a maintained list of special cases.

**Compatibility:** the initial experiments use SolidCraft **0.30.1**.
The native CLI's `--param-check strict` checks the command contracts.
Do not assume a successful Python/JSON export means a CAD command
is valid or has the intended geometrical effect.
