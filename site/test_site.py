#!/usr/bin/env python3
"""Check that published SCPC Pages output matches the actual Python model."""
import json
from pathlib import Path
import sys

from scpc import load_script
from build import GUIDES, CHEATSHEET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PAGES = "https://brainboxemb.github.io/lib.py.solidcraft.cmd/"


def check(site, sha):
    index = (site / "index.html").read_text(encoding="utf-8")
    example = (site / "examples" / "plate" / "index.html").read_text(encoding="utf-8")
    manifest = json.loads((site / "manifest.json").read_text(encoding="utf-8"))
    source = (site / "examples" / "plate" / "model.py").read_text(encoding="utf-8")
    original = (ROOT / "examples" / "plate" / "model.py").read_text(encoding="utf-8")
    native = json.loads((site / "examples" / "plate" / "commands.json").read_text(encoding="utf-8"))
    expected = load_script(ROOT / "examples" / "plate" / "model.py").to_dict()

    assert (site / ".nojekyll").exists()
    assert (site / "style.css").is_file()
    assert manifest["source_commit"] == sha
    assert manifest["library"] == "scpc"
    assert source == original
    assert native == expected
    assert len(native["commands"]) == manifest["command_count"] == 12
    assert native["commands"][-1]["command"] == "solid.hole"
    assert sha in index
    assert "SCPC" in index and "SolidCraft Python Commands" in index
    assert "examples/plate/" in index
    assert "commands.json" in example and "model.py" in example
    assert "../../style.css" in example
    assert 'href="./guide/"' in index
    assert 'href="./cheatsheet/"' in index
    assert 'href="guide/"' in index
    assert 'href="cheatsheet/"' in index
    assert "docs/api.md" not in index and "docs/testing.md" not in index

    # The full API and testing instructions must be readable on SCPC Pages
    # itself, not only through links to raw Markdown on GitHub.
    guide_index = (site / "guide" / "index.html").read_text(encoding="utf-8")
    cheatsheet = (site / "cheatsheet" / "index.html").read_text(encoding="utf-8")
    assert "API Guide" in guide_index and "Quick cheatsheet" in guide_index
    assert "../../style.css" not in guide_index
    assert "../style.css" in guide_index
    assert "Script()" in cheatsheet and "Script.load(path)" in cheatsheet
    assert "../guide/" in cheatsheet
    assert len(GUIDES) >= 5
    assert sum(len(entries) for _, entries in CHEATSHEET) >= 10
    for chapter in GUIDES:
        page = (site / "guide" / chapter["slug"] / "index.html").read_text(encoding="utf-8")
        assert chapter["title"] in page and chapter["slug"] + "/" in guide_index
        assert 'class="guide-sidebar"' in page and 'class="guide-article"' in page
        assert "../../style.css" in page
        assert len(page) > 2200, chapter["slug"]
    script_page = (site / "guide" / "script" / "index.html").read_text(encoding="utf-8")
    execution_page = (site / "guide" / "execution" / "index.html").read_text(encoding="utf-8")
    discovery_page = (site / "guide" / "discovery" / "index.html").read_text(encoding="utf-8")
    testing_page = (site / "guide" / "verification" / "index.html").read_text(encoding="utf-8")
    for term in ("Script.add", "Script.load", "Script.from_json", "load_script"):
        assert term in script_page, term
    for term in ("--out", "--run", "--connect", "rollback"):
        assert term in execution_page, term
    assert "engine.describe" in discovery_page and "--commands" in discovery_page
    assert "native_smoke.py" in testing_page and "100 × 60 × 10 mm" in testing_page
    assert "../../guide/verification/" in example
    assert not (site / "models").exists(), "CAD model gallery belongs in the CAD repository"
    print(f"OK: independent SCPC Pages, {len(native['commands'])} native commands at {sha}")


if __name__ == "__main__":
    check(Path(sys.argv[1]), sys.argv[2])
