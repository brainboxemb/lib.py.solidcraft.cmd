#!/usr/bin/env python3
"""Build SCPC GitHub Pages from its real source, docs and native verification.

No copy of Forge, CAD engine, third-party interactive viewer or model math.
Only official SolidCraft 0.30.1 CAD evidence from the matching Git revision
may be shown as a verified native render.
"""
import argparse
from html import escape
import json
from pathlib import Path
import shutil
import zipfile

import markdown

from scpc import load_script

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/brainboxemb/lib.py.solidcraft.cmd"
FORGE = "https://brainboxemb.github.io/lib.py.solidcraft.forge/"
CAD = "https://brainboxemb.github.io/2026-011-02.cad.solidcraft/"
ENGINE = "0.30.1"

EXAMPLES = {
    "plate": {
        "title": "Plate — sketch, extrusion and holes",
        "description": "A fully editable plate using named parameters, a rectangular sketch, R2 fillets and four holes.",
        "lesson": "Start with native sketch and feature commands. The sketch dimensions are expressions; the fillet/hole selectors are explicit coordinates.",
        "label": "12 commands",
    },
    "corner-bracket": {
        "title": "CornerBracket — profile and chamfers",
        "description": "An L-shaped bracket from a named XZ sketch, a symmetric extrusion, an R4 fillet and three chamfers.",
        "lesson": "Understand an exact native feature history, including topological edge selectors. No screw holes are present.",
        "label": "17 commands",
    },
}

DOCS = {
    "api": ("Python API", "The public Script API, JSON export, native CLI and GUI connection.", "docs/api.md"),
    "testing": ("Testing", "Python tests, fake local control protocol and real SolidCraft CAD tests.", "docs/testing.md"),
    "native-examples": ("Native commands explained", "Step through sketches, features, parameters and edge selection.", "docs/native-examples.md"),
}


def html_page(title, content, *, root_prefix="./"):
    esc = escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="SCPC: Python scripting for native SolidCraft commands, verified examples, API and tests.">
<title>{esc(title)} · SCPC — SolidCraft Python Commands</title>
<link rel="stylesheet" href="{root_prefix}style.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="mast"><div class="shell mast-inner">
<a class="brand" href="{root_prefix}"><span class="symbol">SCPC</span><span>SolidCraft <strong>Python Commands</strong></span></a>
<nav aria-label="Main">
<a href="{root_prefix}">Overview</a>
<a href="{root_prefix}guide/api/">API</a>
<a href="{root_prefix}guide/testing/">Testing</a>
<a href="{root_prefix}guide/native-examples/">Native examples</a>
<a href="{REPO}">GitHub ↗</a>
</nav></div></header>
<main class="shell" id="main">{content}</main>
<footer><div class="shell foot">
<span>SCPC creates native command plans. <strong>SolidCraft</strong> makes the CAD geometry.</span>
<span><a href="https://brainboxemb.github.io/">brainboxemb</a> ·
<a href="{FORGE}">Forge (SCPF)</a> · <a href="{CAD}">CAD models</a></span>
</div></footer></body></html>
"""


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def verify_native(path, sha):
    meta = json.loads((path / "verification.json").read_text(encoding="utf-8"))
    if (meta.get("source_commit") != sha or
            meta.get("solidcraft_version") != ENGINE or
            meta.get("verified") is not True):
        raise ValueError("Native evidence does not match SCPC source revision and SolidCraft 0.30.1")
    for slug in EXAMPLES:
        entry = path / slug
        for name in ("model.sc", "measurements.json", "preview.png", "commands.json"):
            file = entry / name
            if not file.is_file() or file.stat().st_size == 0:
                raise ValueError(f"Native evidence missing: {file}")
        if not zipfile.is_zipfile(entry / "model.sc"):
            raise ValueError(f"{slug}: native model.sc is not a ZIP")
        with zipfile.ZipFile(entry / "model.sc") as archive:
            doc = json.loads(archive.read("document.json"))
            container = json.loads(archive.read("container.json"))
            if doc.get("format") != "solidcraft/48" or container.get("format") != "solidcraft-container/1":
                raise ValueError(f"{slug}: invalid native SolidCraft file")
        results = json.loads((entry / "measurements.json").read_text(encoding="utf-8"))
        if results.get("body_count") != 1 or not results.get("timeline") or any(x.get("error") for x in results["timeline"]):
            raise ValueError(f"{slug}: model has invalid actual SolidCraft geometry or timeline")
    return meta


def build(out, sha, native):
    verify_native(native, sha)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "site/style.css", out / "style.css")
    write(out / ".nojekyll", "")
    provenance = {
        "source_commit": sha,
        "solidcraft_version": ENGINE,
        "native_verified": True,
        "examples": {},
    }
    cards = []
    for slug, info in EXAMPLES.items():
        dest = out / "examples" / slug
        dest.mkdir(parents=True, exist_ok=True)
        source = ROOT / "examples" / slug / "model.py"
        plan = load_script(source).to_dict()
        original = json.loads((native / slug / "commands.json").read_text(encoding="utf-8"))
        if plan != original:
            raise ValueError(f"{slug}: native evidence is for different Python command content")
        if not plan["commands"]:
            raise ValueError(f"{slug}: no native commands")
        measured = json.loads((native / slug / "measurements.json").read_text(encoding="utf-8"))
        if measured["body_count"] != 1:
            raise ValueError(f"{slug}: expected exactly one BRep body")

        shutil.copy2(source, dest / "model.py")
        shutil.copy2(native / slug / "model.sc", dest / "model.sc")
        shutil.copy2(native / slug / "preview.png", dest / "preview.png")
        shutil.copy2(native / slug / "measurements.json", dest / "measurements.json")
        write(dest / "commands.json", json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        command_list = "".join(
            f'<li><code>{escape(x["command"])}</code></li>'
            for x in plan["commands"]
        )
        features = "".join(
            f'<li><span>{escape(x["name"])}</span><small>{escape(x["type"])}</small></li>'
            for x in measured["timeline"]
        )
        source_url = f"{REPO}/blob/main/examples/{slug}/model.py"
        body = f"""<div class="crumb"><a href="../../">← Examples</a> / {escape(info['title'])}</div>
<section class="heading"><p class="eyebrow">Native SolidCraft 0.30.1 · Verified CAD example</p>
<h1>{escape(info['title'])}</h1><p>{escape(info['description'])}</p></section>
<div class="example-layout"><figure class="preview">
<img src="preview.png" alt="SolidCraft 0.30.1 native render of {escape(slug)}" loading="lazy">
<figcaption>Actual native SolidCraft 0.30.1 snapshot, built and measured from this source revision.</figcaption></figure>
<section class="card"><h2>What this demonstrates</h2><p>{escape(info['lesson'])}</p>
<p><strong>{len(plan['commands'])} native commands</strong> ·
<strong>{len(measured['timeline'])} editable features</strong></p>
<div class="links">
<a class="btn" href="model.py">Python model</a>
<a class="btn minor" href="commands.json">Command JSON</a>
<a class="btn minor" href="model.sc" download>Editable .sc</a>
<a class="btn minor" href="{source_url}">GitHub source ↗</a></div></section></div>
<div class="cols"><section class="card"><h2>Native command sequence</h2>
<ol class="command-list">{command_list}</ol></section>
<section class="card"><h2>Real feature history</h2><ol class="feature-list">{features}</ol>
<p class="small">Generated and evaluated by SolidCraft, not recreated in Python.</p>
<a href="measurements.json">Native measurements (JSON) →</a></section></div>
<section class="card"><h2>Independent SCPC Python source</h2>
<p>These are the exact native commands sent to SolidCraft. This file does not import Forge or decompile its JSON.</p>
<pre><code>{escape(source.read_text(encoding="utf-8"))}</code></pre></section>
<section class="card"><h2>How to run</h2><pre><code>python -m scpc examples/{slug}/model.py --out output/{slug}.json
python -m scpc examples/{slug}/model.py --run --save output/{slug}.sc</code></pre></section>"""
        write(dest / "index.html", html_page(info["title"], body, root_prefix="../../"))
        provenance["examples"][slug] = {
            "source": f"examples/{slug}/model.py",
            "commands": f"examples/{slug}/commands.json",
            "native": f"examples/{slug}/model.sc",
            "preview": f"examples/{slug}/preview.png",
            "native_verified": True,
            "command_count": len(plan["commands"]),
        }
        cards.append(f"""<article class="model-card"><img src="examples/{slug}/preview.png" alt="Native CAD model {escape(slug)}" loading="lazy">
<div><span class="badge">{escape(info['label'])} · verified</span>
<h3><a href="examples/{slug}/">{escape(info['title'])} →</a></h3>
<p>{escape(info['description'])}</p>
<a href="examples/{slug}/">Source, commands and native model →</a></div></article>""")

    for slug, (title, summary, filename) in DOCS.items():
        content = (ROOT / filename).read_text(encoding="utf-8")
        for other in DOCS:
            content = content.replace(f"]({other}.md)", f"](../{other}/)")
        # Native example references in docs are relative to docs/ but
        # published model sources live under /examples/<slug>/.
        for example in EXAMPLES:
            content = content.replace(
                f"](../examples/{example}/model.py)",
                f"](../../examples/{example}/model.py)",
            )
        article = markdown.markdown(content, extensions=["fenced_code", "tables"])
        body = f"""<div class="crumb"><a href="../../">← Overview</a> / {escape(title)}</div>
<section class="heading"><p class="eyebrow">SCPC reference</p><h1>{escape(title)}</h1>
<p>{escape(summary)}</p></section>
<article class="card article">{article}</article>
<p class="after"><a href="{REPO}/blob/main/{filename}">Edit this documentation on GitHub →</a></p>"""
        write(out / "guide" / slug / "index.html", html_page(title, body, root_prefix="../../"))

    code = """from scpc import Script

script = Script()
script.add("sketch.create", plane="XY", name="Base")
script.add("sketch.rectangle.two_point", p0=[0, 0], p1=[100, 60])
script.add("sketch.finish")
script.add("solid.extrude", distance="10 mm", body_name="Plate")"""
    body = f"""<section class="hero"><div>
<p class="eyebrow">SOLIDCRAFT · PYTHON · NATIVE COMMANDS</p>
<h1>Write SolidCraft commands.<br><span>Not JSON by hand.</span></h1>
<p class="intro">SCPC is a small Python library for composing the <strong>original SolidCraft commands</strong>. No replacement geometry engine, no matrices, and no duplicated CAD feature API.</p>
<div class="links"><a class="btn" href="guide/api/">Explore the Python API →</a>
<a class="btn minor" href="{REPO}">View the GitHub repository ↗</a></div>
<p class="hero-note">Tested using <strong>SolidCraft 0.30.1</strong>. Actual CAD geometry is built by SolidCraft itself.</p>
</div><div class="code-window"><div class="code-top"><span class="lights">● ● ●</span> model.py</div>
<pre><code>{escape(code)}</code></pre></div></section>
<section class="section-title"><p class="eyebrow">HOW SCPC FITS</p><h2>One engine. Two Python approaches.</h2>
<p>Use <a href="{FORGE}">SCPF Forge</a> for parametrized objects and assemblies. Use SCPC to learn, compose and execute individual native commands. Both ultimately use SolidCraft.</p></section>
<div class="cols"><a class="card tile" href="guide/api/"><span class="badge">LIBRARY</span>
<h3>Python command API →</h3><p><code>Script.add()</code>, native JSON, strict CLI execution and GUI batches.</p></a>
<a class="card tile" href="guide/testing/"><span class="badge">VERIFICATION</span>
<h3>Testing &amp; reproducibility →</h3><p>Offline unit tests, real local protocol and native CAD measurements.</p></a></div>
<section class="section-title"><p class="eyebrow">PROVEN NATIVE MODELS</p><h2>Read the complete commands</h2>
<p>Both examples are actually executed and verified with the native SolidCraft CAD engine.
The screenshots and feature timelines are from the same source revision.</p></section>
<div class="models">{''.join(cards)}</div>
<section class="card next"><h2>Run it yourself</h2><pre><code>python -m pip install -e .
python -m scpc examples/plate/model.py --out output/plate.json
.\\scripts\\test.ps1
.\\scripts\\test.ps1 -Native</code></pre>
<p>For detailed explanations of sketches, expression parameters, fillets and chamfers:
<a href="guide/native-examples/">Native commands explained →</a></p>
<p class="small">The optional VS Code Command Explorer is a later experiment, not a prerequisite for using SCPC.</p></section>"""
    write(out / "index.html", html_page("Overview", body))
    write(out / "provenance.json", json.dumps(provenance, indent=2) + "\n")
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--native", required=True, type=Path)
    args = parser.parse_args()
    build(args.out.resolve(), args.source_sha, args.native.resolve())
