"""On-site SCPC API Guide and cheatsheet, based on the library's public API.

This is deliberately a guide to the thin native command interface, not a
hand-maintained description of SolidCraft's command registry or a second CAD API.
"""
from html import escape


def code(source):
    """Render examples as escaped, copyable code snippets."""
    return '<pre><code>' + escape(source.strip()) + '</code></pre>'


GUIDES = [
    {
        "slug": "getting-started",
        "title": "Getting started",
        "summary": "Install SCPC, write a small Plate, export native commands and run them.",
        "body": """
<h2 id="purpose">Why SCPC exists</h2>
<p><strong>SCPC</strong> (SolidCraft Python Commands) creates the exact native
<code>{"commands":[{"command":"…","params":{…}}]}</code> data structure
accepted by SolidCraft. You write ordinary Python for loops, variables and
reuse, but every <code>script.add()</code> names a real SolidCraft operation.
There is no separate geometry language.</p>
<p><strong>SCPF (Forge)</strong> provides higher-level modelling objects,
while <strong>SCPC</strong> exposes native commands directly. Both can create
editable SolidCraft designs, but they are deliberately independent.</p>
<h2 id="install">Install on your machine</h2>
<p>From the root of <code>lib.py.solidcraft.cmd</code>, activate your normal
Python environment and install the library in editable mode:</p>
""" + code(r"""
conda activate brainboxemb-dev-tools
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
""") + """
<h2 id="first-model">Write your first script</h2>
<p>Save the following as <code>model.py</code>. A Python source file defines
one non-empty <code>Script</code>; it does not require a
<code>main()</code> function or <code>show()</code>.</p>
""" + code(r"""
from scpc import Script

script = Script()
script.add("sketch.create", plane="XY", name="Base")
script.add("sketch.rectangle.two_point", p0=[0, 0], p1=[100, 60])
script.add("sketch.finish")
script.add("solid.extrude", distance="10 mm", body_name="Plate")
""") + """
<p>The real <a href="../../examples/plate/">Plate example</a> also defines
parameters, rounds its vertical edges and adds four holes; that example is
part of the native CI tests.</p>
<h2 id="export">Export, inspect and execute</h2>
""" + code(r"""
python -m scpc model.py --out output/plate.json
python -m scpc model.py --run --save output/plate.sc
""") + """
<p><code>--out</code> only exports JSON. <code>--run</code> uses the
installed <code>solidcraft-cli</code> and can save an editable
<code>.sc</code> design. You can run the JSON file later, without
re-running the Python source:</p>
""" + code(r"""
python -m scpc output/plate.json --run --save output/replayed.sc
""") + """
<div class="notice"><strong>Two separate checks.</strong>
Python accepting a command and SolidCraft accepting the command are not
the same as proving the finished geometry is correct. See
<a href="../verification/">Verification and testing</a>.</div>
""",
    },
    {
        "slug": "script",
        "title": "Script API and JSON",
        "summary": "Script.add(), native parameters, export, import and trusted Python loading.",
        "body": """
<h2 id="add">Build an ordered native command sequence</h2>
<p><code>Script.add(command, **params)</code> appends one command and
returns the same Script, so calls can be chained. The command ID and keyword
names are passed through unchanged. They are <em>SolidCraft's</em>
names rather than aliases invented by SCPC.</p>
""" + code(r"""
from scpc import Script

script = Script()
script.add("sketch.create", plane="XY", name="Base")
script.add("sketch.finish")
assert len(script) == 2
""") + """
<h2 id="read">Inspect and save commands</h2>
<p><code>script.commands</code> returns a detached copy of the ordered
command entries. <code>to_dict()</code> returns the full native document;
<code>to_json()</code> serialises it to readable UTF-8 JSON;
<code>save(path)</code> creates the destination directory if needed and
writes the file.</p>
""" + code(r"""
commands = script.commands
document = script.to_dict()   # {"commands": [...]}
json_text = script.to_json()
script.save("output/commands.json")
""") + """
<h2 id="import">Import JSON without running Python</h2>
<p>SCPC can reopen the native JSON format directly, which is useful for
comparing generated scripts or replaying a fixed command sequence.
Import is structural, not CAD validation.</p>
""" + code(r"""
restored = Script.load("output/commands.json")
restored = Script.from_json(json_text)
restored = Script.from_dict(document)
""") + """
<p>The input must have exactly a top-level <code>commands</code> array;
every entry must contain a nonempty <code>command</code> string and a
<code>params</code> object. Malformed JSON, extra structural fields,
unsupported Python values and non-finite numbers are rejected. The
original order and parameter values are preserved.</p>
<h2 id="load-model">Loading a Python model</h2>
<p><code>load_script("model.py")</code> executes a <strong>trusted</strong>
Python file and finds its single nonempty Script instance. Loading
<code>.json</code> with <code>Script.load()</code> does <em>not</em>
execute Python. Never evaluate an unknown Python model as untrusted input.</p>
""" + code(r"""
from scpc import load_script

plan = load_script("examples/plate/model.py")
print(len(plan), plan.commands[0]["command"])
""") + """
<h2 id="scope">What this API does not do</h2>
<p>SCPC does not implement geometry, named edge selectors, automatic
coordinate transforms or separate <code>Fillet</code> and
<code>Hole</code> Python classes. It only serialises native command
requests. The native engine decides whether an operation is valid.</p>
""",
    },
    {
        "slug": "native-commands",
        "title": "Native commands and features",
        "summary": "Sketches, extrusion, fillet and holes through the real SolidCraft vocabulary.",
        "body": """
<h2 id="vocabulary">Use SolidCraft's command IDs</h2>
<p>SCPC does not freeze a list of command IDs or parameters. Obtain the
authoritative registry and schemas from the <em>installed</em> SolidCraft
version (see <a href="../discovery/">Command discovery</a>).
The examples below are verified with SolidCraft <strong>0.30.1</strong>;
other versions may differ.</p>
<h2 id="sketch">Create and finish a sketch</h2>
<p>Every command is explicit. First create the XY sketch, draw its
rectangle and finish the sketch before extruding.</p>
""" + code(r"""
script.add("sketch.create", plane="XY", name="Plate footprint")
script.add("sketch.rectangle.two_point",
           p0=[-50, -30], p1=[50, 30])
script.add("sketch.finish")
script.add("solid.extrude", distance="10 mm", body_name="Plate")
""") + """
<h2 id="parameters">Native model parameters</h2>
<p>Names and expressions remain editable in the SolidCraft document.
These are native commands, not properties interpreted by SCPC.</p>
""" + code(r"""
for name, value in (("length", 100), ("width", 60), ("thickness", 10)):
    script.add("parameters.add", name=name,
               expression=str(value), unit="mm")
""") + """
<h2 id="features">Fillet and hole features</h2>
<p>In the tested Plate example, fillet selection uses native edge pick
coordinates. Hole positions likewise use the native command parameters.
SCPC does not translate a higher-level edge or face selection model.</p>
""" + code(r"""
script.add("solid.fillet", body="Plate", radius=2,
           edges=[[-50, -30, 5], [50, -30, 5],
                  [50, 30, 5], [-50, 30, 5]])

for x, y in ((-35, -15), (35, -15), (35, 15), (-35, 15)):
    script.add("solid.hole", position=[x, y, 10],
               diameter=8, targets=["Plate"])
""") + """
<p>See the <a href="../../examples/plate/">full Plate source and the
native JSON sequence</a> side by side. It is tested by actually
evaluating the generated SolidCraft model, not just its command count.</p>
<h2 id="strict">Native validation, not guesswork</h2>
<p>The CLI is invoked with <code>--param-check strict</code>.
That is a native check, but it does not guarantee every unexpected
parameter is rejected or every geometrical outcome matches your intent.
Verify the actual saved BRep, feature history and dimensions.</p>
""",
    },
    {
        "slug": "execution",
        "title": "CLI and GUI execution",
        "summary": "Export-only, headless native SolidCraft and authenticated live GUI batches.",
        "body": """
<h2 id="export">Export without starting SolidCraft</h2>
""" + code(r"""
python -m scpc examples/plate/model.py --out output/plate.json
""") + """
<p>This creates only the command JSON. It does not change any open GUI
document and does not test SolidCraft's geometry engine.</p>
<h2 id="native">Run the native command-line engine</h2>
""" + code(r"""
python -m scpc examples/plate/model.py --run --save output/plate.sc
python -m scpc output/plate.json --run --save output/plate-replay.sc
""") + """
<p><code>--run</code> requires the installed
<code>solidcraft-cli</code>. Use <code>--cli PATH</code> if the CLI is
not on PATH. <code>--save</code> is valid only with
<code>--run</code>. SCPC executes the command list through SolidCraft
with native strict parameter checking and propagates errors.</p>
<h2 id="desktop">Apply commands to the open desktop GUI</h2>
""" + code(r"""
python -m scpc examples/plate/model.py --connect
python -m scpc output/plate.json --connect
""") + """
<p>This sends the ordered commands as one authenticated
<code>engine.batch</code> request to an <strong>already running</strong>
SolidCraft desktop process, operating on its current design.
Enable <em>Preferences → Assistant → Let AI agents connect</em> in
SolidCraft. SCPC does not launch the app, create or clear a document,
or save the active file automatically.</p>
<p>SCPC requests <code>param_check=strict</code> and
<code>rollback=true</code> for the batch. If a step fails, the
native error and reported rollback result are shown. If a request
times out, the GUI operation may still be running: check the open
document before attempting the same batch again.</p>
<h2 id="python">Call the same functions directly from Python</h2>
""" + code(r"""
from scpc import run_cli, send_batch

run_cli(script, save="output/plate.sc")
send_batch(script.commands)
""") + """
<div class="notice"><strong>Different execution modes:</strong>
<code>--out</code> is offline serialisation; <code>--run</code> is a
separate native headless session; <code>--connect</code> changes the
currently open GUI document. Choose the mode intentionally.</div>
""",
    },
    {
        "slug": "discovery",
        "title": "Discovering the SolidCraft API",
        "summary": "Inspect installed native command IDs and live command input/output schemas.",
        "body": """
<h2 id="registry">List the installed native command registry</h2>
<p>Instead of maintaining a parallel command catalogue, SCPC asks your
installed native CLI what it supports:</p>
""" + code(r"""
python -m scpc --commands
# Or, inside Python:
from scpc import commands
registry = commands()
""") + """
<p>This calls <code>solidcraft-cli commands</code>. The exact
result structure is defined by the SolidCraft version on your machine.
No SCPC-generated signatures or hand-written parameter tables are used.</p>
<h2 id="schema">Get a command's live schema</h2>
<p>With an authenticated, running SolidCraft desktop session,
<code>engine.describe</code> returns the native input/output
description for one command:</p>
""" + code(r"""
python -m scpc --describe solid.extrude
# Or, inside Python:
from scpc import describe
schema = describe("solid.extrude")
""") + """
<p><code>--describe</code> uses the authenticated local GUI connection.
It is not a standalone offline command. A missing GUI connection or
unavailable schema is a real limitation; never invent parameters.</p>
<h2 id="explorer">Command Explorer: later, not a dependency</h2>
<p>A future Explorer can search the command registry, display the native
parameter schema and export SCPC source. It should use the same
<code>commands()</code> and <code>describe()</code> API, with a
raw JSON editor when a typed field is unknown. The library works
without a GUI, VS Code extension or Explorer.</p>
<h2 id="versions">Compatibility</h2>
<p>The native regression tests currently qualify SolidCraft
<strong>0.30.1</strong>. For a different version, inspect its
<code>commands</code> and <code>engine.describe</code> results, then
test the actual geometry. A syntactically valid exported script is not
a guarantee of compatibility.</p>
""",
    },
    {
        "slug": "verification",
        "title": "Verification and testing",
        "summary": "Separate Python, local protocol and real CAD-engine tests; understand what each proves.",
        "body": """
<h2 id="offline">1. Offline Python and local socket tests</h2>
""" + code(r"""
.\scripts\test.ps1
# Or:
python -m unittest discover -s tests -p "test_*.py" -v
""") + """
<p>These verify the Script data contract, CLI arguments, JSON
round-trips and fake authenticated localhost socket exchanges for
<code>engine.describe</code> and <code>engine.batch</code>.
The fake endpoint tests only the wire protocol; it does not create
or inspect CAD geometry.</p>
<h2 id="native">2. Run the real native SolidCraft engine</h2>
""" + code(r"""
.\scripts\test.ps1 -Native
# Or, with solidcraft-cli 0.30.1 installed:
python tests/native_smoke.py --output-dir output/native-smoke
""") + """
<p>The native test checks the installed version and command registry,
exports the Python Plate, runs it headlessly, opens its saved editable
<code>.sc</code> container and evaluates its body and feature history.
It independently replays the exported JSON and checks that both
results have matching bounding boxes and timeline length.
An intentionally invalid command must be rejected.</p>
<p>The expected Plate is one body measuring
<strong>100 × 60 × 10 mm</strong>, with an error-free native
feature timeline.</p>
<h2 id="ci">3. Continuous integration</h2>
<p>GitHub Actions runs the Python/socket suite on Linux, the
documented PowerShell entry point on Windows and an actual
checksum-verified SolidCraft 0.30.1 native CLI run.
The CAD repository also compares independently authored
SCPF and SCPC models. The Pages site is published only after the
library's required CI jobs succeed.</p>
<h2 id="manual">4. The desktop GUI still needs manual inspection</h2>
<p>Automated protocol tests do not prove an open GUI accepts a live
request or that a feature is displayed as intended. For live
testing, open an <strong>empty design</strong>, enable the Assistant
connection, execute a known example with <code>--connect</code>,
and inspect its bodies and feature tree.</p>
<div class="notice"><strong>Principle:</strong>
Valid Python is not necessarily valid SolidCraft JSON; valid JSON is
not necessarily a successful native command; successful commands do
not by themselves prove the intended geometry.</div>
""",
    },
]


CHEATSHEET = [
    ("Build a command script", [
        ("Script() + add()", "Append native command IDs, in order.",
         'script = Script()\nscript.add("sketch.create", plane="XY", name="Base")',
         "script"),
        ("script.commands", "Get a detached copy of the command list.",
         "entries = script.commands", "script"),
        ("to_dict() / to_json()", "Export native data without running CAD.",
         "document = script.to_dict()\ntext = script.to_json()", "script"),
        ("save(path)", "Write native command JSON.",
         'script.save("output/commands.json")', "script"),
    ]),
    ("Reopen existing commands", [
        ("Script.load(path)", "Import JSON as data, without executing Python.",
         'plan = Script.load("output/commands.json")', "script"),
        ("from_json() / from_dict()", "Import a native JSON string or dictionary.",
         "plan = Script.from_json(text)\nplan = Script.from_dict(document)", "script"),
        ("load_script(path)", "Load ONE non-empty Script from trusted Python.",
         'plan = load_script("model.py")', "script"),
    ]),
    ("Run and inspect", [
        ("--out", "Export native command JSON without CAD.",
         "python -m scpc model.py --out output/plate.json", "execution"),
        ("--run --save", "Run in native CLI and save editable SolidCraft .sc.",
         "python -m scpc model.py --run --save output/plate.sc", "execution"),
        ("JSON replay", "Run previously exported commands, not Python source.",
         "python -m scpc output/plate.json --run", "execution"),
        ("--connect", "Apply one authenticated batch to an open GUI.",
         "python -m scpc model.py --connect", "execution"),
        ("--commands", "Query the installed native command registry.",
         "python -m scpc --commands", "discovery"),
        ("--describe", "Read one command schema from the running GUI.",
         "python -m scpc --describe solid.extrude", "discovery"),
    ]),
]
