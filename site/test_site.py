#!/usr/bin/env python3
"""Check that published SCPC Pages output matches the actual Python model."""
import json
from pathlib import Path
import sys

from scpc import load_script

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
    assert "docs/api.md" in index and "docs/testing.md" in index
    assert not (site / "models").exists(), "CAD model gallery belongs in the CAD repository"
    print(f"OK: independent SCPC Pages, {len(native['commands'])} native commands at {sha}")


if __name__ == "__main__":
    check(Path(sys.argv[1]), sys.argv[2])
