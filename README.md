# SCPC — SolidCraft Python Commands

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
See [Plate](examples/plate/model.py) for a complete model.

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

## What comes next

The CAD repository
[2026-011-02.cad.solidcraft](https://github.com/brainboxemb/2026-011-02.cad.solidcraft)
will have independent `scpf/model.py` and `scpc/model.py` variants.
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
