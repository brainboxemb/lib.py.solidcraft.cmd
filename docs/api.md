# SCPC native command API — v0.1

SCPC stands for **SolidCraft Python Commands**. It is intentionally
not a second Forge, a geometry engine, or a standalone CAD format.

## Create a command script

```python
from scpc import Script

script = Script()

script.add("sketch.create", name="Base", plane="XY")
script.add("sketch.rectangle.two_point", p0=[0, 0], p1=[100, 60])
script.add("sketch.finish")
script.add("solid.extrude", distance="10 mm", body_name="Plate")
```

Each `add()` call appends one *native* `{command, params}` entry.
It accepts exactly the keyword parameters that SolidCraft itself accepts.
There is **no** translation such as `radius=` into a custom SCPC
`Fillet` class. The method returns the same `Script`, so it can be
chained; order is preserved.

`script.commands` returns a detached list of native command entries.
`script.to_dict()` returns `{"commands": [...]}`. `script.to_json()`
returns readable UTF-8 JSON text, and `script.save(path)` writes it.
The `Script` constructor does not connect to SolidCraft or open files.
It rejects invalid JSON types and nonfinite numbers, but **does not
claim to validate the meaning of native command parameters**.

## Load and execute a Python model

`load_script(path)` evaluates a **trusted** Python source file that
defines exactly one nonempty `Script`. Never run unknown/untrusted
Python models. There is no mandatory `main()` or `show()`.

```powershell
python -m scpc examples/plate/model.py --out output/plate.json
python -m scpc examples/plate/model.py --run --save output/plate.sc
python -m scpc examples/plate/model.py --connect
```

- `--out` only exports native JSON; no CAD engine is started.
- `--run` uses the installed `solidcraft-cli` headlessly with
  `--param-check strict`, optionally saving a native document.
- `--connect` submits one `engine.batch` with strict parameters and
  rollback to the already open, authenticated **desktop GUI**.
  It does not open a new document. A timed-out batch may still be
  running, so do not retry blindly.

You can call `run_cli(script, save=...)` and
`send_batch(script.commands)` directly from Python, without using
the command-line interface.

## Discover the installed command API

```powershell
python -m scpc --commands
python -m scpc --describe solid.extrude
```

`commands()` returns the installed `solidcraft-cli commands` registry
as native JSON data. `describe("solid.extrude")` queries the running GUI's
`engine.describe`, returning its native command schema and documentation.
The second operation requires an authenticated open GUI session.

Do not use SCPC to maintain a parallel handwritten command registry.
A future Command Explorer should be a UI over this *same* low-level
API, not a second backend.

## Testing

See [testing.md](testing.md) for offline API/socket tests, actual native
SolidCraft 0.30.1 verification of **Plate and CornerBracket**, and dual
SCPC/SCPF model tests. The [native command examples](native-examples.md)
show how to read the generated command plans and reason about SolidCraft
sketches, features and edge selectors.
