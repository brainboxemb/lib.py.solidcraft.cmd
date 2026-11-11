# Reading the SolidCraft command API through real models

This is a practical guide to the **native SolidCraft command format**,
not another CAD modelling framework. We use two small models to distinguish
what Python handles from what the actual SolidCraft engine handles.

## The two examples

| Example | Native commands | Result | Features in saved design |
| --- | ---: | --- | --- |
| [Plate](../examples/plate/model.py) | 12 | 100 × 60 × 10 mm | Sketch → Extrude → Fillet → 4 × Hole |
| [CornerBracket](../examples/corner-bracket/model.py) | 17 | X=−12..60, Y=−12..12, Z=−60..12 mm | Sketch → Extrude → Fillet → 3 × Chamfer |

Each Python file defines one `Script` and uses `script.add()` with
**unmodified SolidCraft command IDs and parameter names**.

You can open each complete source file and follow every command without
chasing another model, wrapper class or generated command file.

## 1. Native command JSON: one stable structure

For example, Python:

```python
script.add("sketch.create", plane="XY", name="Plate footprint")
```

produces the native entry:

```json
{
  "command": "sketch.create",
  "params": {
    "plane": "XY",
    "name": "Plate footprint"
  }
}
```

A full native command file is an ordered document:

```json
{
  "commands": [
    {"command": "sketch.create", "params": {"plane": "XY"}},
    {"command": "sketch.finish", "params": {}}
  ]
}
```

These are **native commands**, not SolidCraft `.sc` design files.
The real SolidCraft engine reads the commands, performs the CAD
operations and can save the resulting editable `.sc` design.

## 2. Parameters and expressions

The Plate first registers three SolidCraft parameters:

```python
for name, value in (("length", 100), ("width", 60), ("thickness", 10)):
    script.add("parameters.add", name=name, expression=str(value), unit="mm")
```

The sketch then uses those native expressions:

```python
script.add("sketch.rectangle.two_point",
           p0=["-length / 2", "-width / 2"],
           p1=["length / 2", "width / 2"])
```

Notice that **Python does not compute** `-length / 2`.
SolidCraft evaluates that expression. The extrusion similarly uses
`distance="thickness"`.

**Important difference:** the Plate's fillet and hole placement
currently use explicit numeric edge and position selectors. Changing
the Plate dimensions may therefore require reviewing those points,
even though its sketch and extrusion use named parameters.

## 3. Sketches, features and selected edges

The CornerBracket uses an **XZ-plane** `sketch.line`, with
`closed=True` and named points. Its 9-point outline includes the
two arms and their cut-off ends. The model then executes:

```python
script.add("sketch.finish")
script.add("solid.extrude", distance="bracket_width",
           direction="symmetric", body_name="CornerBracket")
script.add("solid.fillet", edges=[[0, 0, 0]],
           radius=4, body="CornerBracket")
```

The coordinate `[0, 0, 0]` is a **native SolidCraft edge selector**.
It is not the centre of a Python CSG cutter. SolidCraft determines
which topological edge to fillet. The later three
`solid.chamfer` commands similarly use explicit edge selectors.

This is why an SCPC model can be a useful way to learn the API:
it shows precisely which sketch, feature and selection commands
SolidCraft receives. **SCPC does not fix or transform these choices.**

The CornerBracket currently has **no screw holes**. Those operations
were deliberately removed from the reference model.

## 4. Ask the installed SolidCraft version

On a machine with `solidcraft-cli 0.30.1` installed:

```powershell
python -m scpc --commands > output/commands.json
```

This prints SolidCraft's **real native command registry**, not an
SCPC-maintained command table. In the pinned CI release (0.30.1),
it contains **570 entries**. Each entry contains information such as
`id`, `label`, `tab`, `panel`, `params` (a **text description**),
and whether the command is currently enabled.

**Do not mistake `params` in that registry for a typed JSON Schema.**
The typed input/output descriptions come from the live
`engine.describe` method, which requires an authenticated control
connection to the SolidCraft GUI:

```powershell
python -m scpc --describe solid.extrude
```

The registry can be explored without launching the GUI; getting
the full live schema cannot currently be guaranteed in headless SCPC.

## 5. Confirm with the real CAD engine

```powershell
python -m scpc examples/plate/model.py --out output/plate.json
python -m scpc examples/corner-bracket/model.py --out output/bracket.json

python -m scpc examples/plate/model.py --run --save output/plate.sc
python -m scpc examples/corner-bracket/model.py --run --save output/bracket.sc
```

A valid JSON file alone proves almost nothing about the resulting CAD
model. To test geometry, topology and feature history **automatically**
without creating an extra Python geometry implementation:

```powershell
.\scripts\test.ps1 -Native
```

It runs both examples with native strict validation, confirms the
`.sc` archive format, checks actual BRep bounds and feature types,
and deliberately checks a command failure. It stores the results
under `output/native-smoke/`.

The [CAD examples repository](https://github.com/brainboxemb/2026-011-02.cad.solidcraft)
also contains independent Forge (SCPF) and native-command (SCPC)
versions of both models. Its CI checks that the actual native results
match—not merely that the JSON is structurally valid.

## What this does *not* test yet

- A **live** `engine.describe` reply from a running desktop GUI.
- A successful live `--connect` batch inside a real open GUI document.
- Visual correctness of arbitrary parameter changes, especially when
  numeric edge-selection coordinates must also be updated.

Those cases must be tested separately and should not be described as
automatically verified by the headless tests. Keeping these boundaries
explicit prevents false confidence in our Python API.

## Observed strict-validation caveat

SolidCraft 0.30.1 rejects unknown native command IDs, but our real
native test found that `sketch.create` can accept an **extra unknown
parameter key** under `--param-check strict`. Avoid relying solely on
strict mode to catch typos in parameter names. Read the native registry,
query live schemas where available, and always verify the resulting BRep
and feature history for important models.
