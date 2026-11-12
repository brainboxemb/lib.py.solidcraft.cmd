#!/usr/bin/env python3
"""Build this library's own GitHub Pages website from real SCPC sources.

Unlike the general brainboxemb homepage, all site sources and the deployment
workflow live in lib.py.solidcraft.cmd. No CAD gallery is copied here.
"""
import argparse
from html import escape
import json
from pathlib import Path
import shutil

from scpc import load_script
from guides import GUIDES, CHEATSHEET

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/brainboxemb/lib.py.solidcraft.cmd"
FORGE_URL = "https://brainboxemb.github.io/lib.py.solidcraft.forge/"
CAD_URL = "https://brainboxemb.github.io/2026-011-02.cad.solidcraft/"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def layout(title, body, prefix="."):
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="SolidCraft Python Commands: native SolidCraft commands written in Python.">
  <title>{escape(title)} — SCPC</title>
  <link rel="stylesheet" href="{prefix}/style.css">
</head>
<body>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="{prefix}/"><strong>SCPC</strong> <span>SolidCraft Python Commands</span></a>
      <nav aria-label="Main navigation">
        <a href="{prefix}/">Overview</a>
        <a href="{prefix}/examples/plate/">Plate example</a>
        <a href="{prefix}/guide/">API Guide</a>
        <a href="{prefix}/cheatsheet/">Cheatsheet</a>
        <a href="{REPO_URL}">Source ↗</a>
      </nav>
    </div>
  </header>
  {body}
  <footer><div class="wrap footer-inner">
    <span>SCPC describes native commands; SolidCraft builds the CAD model.</span>
    <a href="{FORGE_URL}">Forge library</a>
    <a href="{CAD_URL}">CAD projects</a>
  </div></footer>
</body>
</html>
"""


def build(output, commit):
    model_path = ROOT / "examples" / "plate" / "model.py"
    source = model_path.read_text(encoding="utf-8")
    commands = load_script(model_path).to_dict()["commands"]
    if not commands or commands[-1]["command"] != "solid.hole":
        raise ValueError("The Plate example no longer matches the documented command sequence")

    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "site" / "style.css", output / "style.css")
    write(output / ".nojekyll", "")
    example_dir = output / "examples" / "plate"
    write(example_dir / "model.py", source)
    write(example_dir / "commands.json",
          json.dumps({"commands": commands}, ensure_ascii=False, indent=2) + "\n")
    write(output / "manifest.json",
          json.dumps({"source_commit": commit, "library": "scpc",
                      "example": "plate", "command_count": len(commands)}, indent=2) + "\n")

    quickstart = """script = Script()
script.add("sketch.create", plane="XY", name="Base")
script.add("sketch.rectangle.two_point", p0=[0, 0], p1=[100, 60])
script.add("sketch.finish")
script.add("solid.extrude", distance="10 mm", body_name="Plate")"""
    overview = f"""
<main class="wrap">
  <section class="hero">
    <p class="kicker">SOLIDCRAFT · PYTHON · NATIVE COMMANDS</p>
    <h1>Write SolidCraft commands in Python.</h1>
    <p class="lead">SCPC is a small, direct interface to SolidCraft's native command API.
       Build an ordered command script without manually writing JSON or creating
       a second CAD modelling language.</p>
    <div class="actions">
      <a class="button button-primary" href="guide/">Read the API Guide →</a>
      <a class="button button-secondary" href="examples/plate/">Explore the Plate example →</a>
      <a class="button button-secondary" href="{REPO_URL}">View source on GitHub ↗</a>
    </div>
    <div class="hero-graphic" aria-hidden="true">
      <div class="graphic-code">sketch.create<br>sketch.rectangle.two_point<br>sketch.finish<br>solid.extrude</div>
      <div class="graphic-arrow">→</div>
      <svg viewBox="0 0 240 160" role="presentation">
        <path d="M20 75 L137 37 220 73 101 116Z" fill="#b5e2ee" stroke="#72c9d8" stroke-width="2"/>
        <path d="M20 75 V92 L101 134 V116Z" fill="#378bab" stroke="#72c9d8" stroke-width="2"/>
        <path d="M101 116 L220 73 V92 L101 134Z" fill="#206b90" stroke="#72c9d8" stroke-width="2"/>
        <ellipse cx="79" cy="75" rx="14" ry="7" fill="#123959" stroke="#77cbd7" stroke-width="2"/>
        <ellipse cx="167" cy="78" rx="14" ry="7" fill="#123959" stroke="#77cbd7" stroke-width="2"/>
      </svg>
    </div>
  </section>

  <section class="three" aria-label="How SCPC works">
    <article class="tile"><span class="step">01</span><h2>Describe</h2>
      <p>Use <code>Script.add(native_command, **params)</code>. IDs and parameters
      follow SolidCraft itself, not SCPC-specific geometry rules.</p></article>
    <article class="tile"><span class="step">02</span><h2>Export</h2>
      <p>Generate the native <code>{{"commands":[...]}}</code> JSON, with the original
      order and parameter names preserved.</p></article>
    <article class="tile"><span class="step">03</span><h2>Execute</h2>
      <p>Run with the verified native CLI or send a batch to an already-open
      SolidCraft GUI document. The CAD engine performs the modelling.</p></article>
  </section>

  <section class="split">
    <div>
      <p class="kicker dark">A MINIMAL EXAMPLE</p>
      <h2>Native operations, readable Python</h2>
      <p>This is the same command vocabulary exposed by SolidCraft.
      There is no mandatory <code>main()</code> or <code>show()</code>.</p>
      <p><a href="examples/plate/">See the complete Plate script, command JSON and verification details →</a></p>
    </div>
    <pre><code>{escape(quickstart)}</code></pre>
  </section>

  <section class="resources">
    <h2>Learn and test</h2>
    <div class="resource-grid">
      <a href="guide/"><strong>SCPC API Guide →</strong>
        <span>Six chapters covering the Python API, native commands, execution, discovery and verification.</span></a>
      <a href="cheatsheet/"><strong>Quick cheatsheet →</strong>
        <span>Common Script calls and CLI commands with runnable examples.</span></a>
      <a href="guide/verification/"><strong>Verification &amp; testing →</strong>
        <span>Python tests, authenticated control protocol and real SolidCraft 0.30.1 checks.</span></a>
      <a href="{FORGE_URL}"><strong>SolidCraft Forge (SCPF) ↗</strong>
        <span>A separate higher-level Python modelling interface.</span></a>
      <a href="{CAD_URL}"><strong>CAD projects ↗</strong>
        <span>Actual models and independent SCPF/SCPC comparisons.</span></a>
    </div>
    <p class="source-note">Built from source commit <code>{escape(commit)}</code>.</p>
  </section>
</main>"""
    write(output / "index.html", layout("Overview", overview))

    timeline = "".join(
        f'<li><code>{escape(item["command"])}</code></li>' for item in commands)
    detail = f"""
<main class="wrap">
  <p class="crumb"><a href="../../">← Overview</a> / Plate example</p>
  <section class="example-intro">
    <p class="kicker dark">NATIVE COMMAND SCRIPT</p>
    <h1>Plate with rounded edges and holes</h1>
    <p>A complete SCPC Plate fixture: parameters, sketch, extrusion, fillet
       and four native hole commands. Its JSON is produced from the actual
       Python source on every build, not copied by hand.</p>
    <p class="badge">{len(commands)} native commands · tested with SolidCraft 0.30.1 in CI</p>
  </section>
  <div class="example-grid">
    <section class="panel"><h2>Python source</h2>
      <pre><code>{escape(source)}</code></pre>
      <a href="model.py">View model.py →</a>
    </section>
    <section class="panel"><h2>Native command sequence</h2>
      <ol class="command-list">{timeline}</ol>
      <p><a class="button button-primary" href="commands.json">View generated JSON →</a></p>
    </section>
  </div>
  <section class="notice"><strong>Verification boundaries.</strong>
    The Python API and JSON format are tested independently of the actual
    CAD geometry. A separate CI job runs the native SolidCraft 0.30.1 engine,
    checks the resulting Plate and its feature history, and reports failures.
    <a href="../../guide/verification/">Read the test methodology →</a>
  </section>
</main>"""
    write(example_dir / "index.html",
          layout("Plate example", detail, prefix="../.."))

    # Documentation is a first-class part of SCPC Pages, as in the SCPF
    # library site. Keep chapter content in one maintained source: guides.py.
    guide_cards = []
    for chapter in GUIDES:
        slug = chapter["slug"]
        sidebar = "".join(
            f'<a href="../{escape(item["slug"])}/">{escape(item["title"])}</a>'
            for item in GUIDES
        )
        body = (
            '<main class="wrap guide-layout">'
            '<aside class="guide-sidebar" aria-label="API chapters">'
            '<h2>API Guide</h2><a href="../">All chapters</a>'
            + sidebar + '</aside>'
            '<article class="guide-article">'
            + f'<p class="crumb"><a href="../">← API Guide</a> / {escape(chapter["title"])}</p>'
            + f'<h1>{escape(chapter["title"])}</h1>'
            + f'<p class="guide-lead">{escape(chapter["summary"])}</p>'
            + chapter["body"] + '</article></main>'
        )
        write(output / "guide" / slug / "index.html",
              layout(chapter["title"], body, prefix="../.."))
        guide_cards.append(
            f'<article class="reference"><h2><a href="{escape(slug)}/">'
            f'{escape(chapter["title"])}</a></h2>'
            f'<p>{escape(chapter["summary"])}</p></article>'
        )

    guide_index = (
        '<main class="wrap"><section class="hero small">'
        '<p class="kicker">SCPC PYTHON LIBRARY</p><h1>API Guide</h1>'
        '<p class="lead">Learn the public Python interface and the native '
        'SolidCraft command workflow, with tested examples and clear limits. '
        'For a fast lookup, use the cheatsheet.</p>'
        '<div class="actions"><a class="button button-primary" '
        'href="../cheatsheet/">Quick cheatsheet →</a></div>'
        '</section><div class="reference-grid">'
        + "".join(guide_cards) + '</div></main>'
    )
    write(output / "guide" / "index.html",
          layout("API Guide", guide_index, prefix=".."))

    sections = []
    for heading, items in CHEATSHEET:
        entries = []
        for title, description, snippet, chapter in items:
            entries.append(
                '<article class="reference">'
                f'<h3><code>{escape(title)}</code></h3>'
                f'<p>{escape(description)}</p>'
                f'<pre><code>{escape(snippet)}</code></pre>'
                f'<a href="../guide/{escape(chapter)}/">Read explanation →</a>'
                '</article>'
            )
        sections.append(
            '<section class="cheat-section">'
            f'<h2>{escape(heading)}</h2>'
            '<div class="reference-grid">' + "".join(entries) + '</div></section>'
        )
    cheatsheet_page = (
        '<main class="wrap"><p class="crumb"><a href="../">← Overview</a> / Cheatsheet</p>'
        '<section class="hero small"><p class="kicker">SCPC QUICK REFERENCE</p>'
        '<h1>Cheatsheet</h1>'
        '<p class="lead">The small public Script interface and native CLI '
        'commands at a glance. For context and limitations, read the '
        '<a href="../guide/">complete API Guide</a>.</p></section>'
        '<div class="notice"><strong>About native parameters.</strong> '
        'Command IDs and parameter schemas belong to your installed SolidCraft '
        'engine; query them using <code>--commands</code> and '
        '<code>--describe</code>. These examples are not a complete '
        'catalogue of SolidCraft commands.</div>'
        + "".join(sections) + '</main>'
    )
    write(output / "cheatsheet" / "index.html",
          layout("Cheatsheet", cheatsheet_page, prefix=".."))
    print(f"SCPC Pages: {len(commands)} commands, {len(GUIDES)} API chapters, "
          f"cheatsheet, commit {commit}, output {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    build(args.out, args.source_sha)
