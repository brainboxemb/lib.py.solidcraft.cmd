#!/usr/bin/env python3
"""Smoke-test published SCPC Pages content, provenance and internal links.

A green "HTML generated" test is insufficient: the source shown on each
model page and its native command JSON must be from the same verified run.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import zipfile

from scpc import load_script

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ("plate", "corner-bracket")
DOCS = ("api", "testing", "native-examples")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag in ("a", "link") and props.get("href"):
            self.links.append(props["href"])
        elif tag in ("img", "script") and props.get("src"):
            self.links.append(props["src"])


def check(out, sha):
    manifest = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
    assert manifest["source_commit"] == sha, "Published SHA differs from checked-out source"
    assert manifest["solidcraft_version"] == "0.30.1"
    assert manifest["native_verified"] is True
    assert set(manifest["examples"]) == set(EXAMPLES)
    homepage = (out / "index.html").read_text(encoding="utf-8")
    assert "SolidCraft Python Commands" in homepage
    assert "Not JSON by hand" in homepage
    assert "lib.py.solidcraft.forge/" in homepage
    assert "2026-011-02.cad.solidcraft/" in homepage
    assert "examples/plate/" in homepage and "examples/corner-bracket/" in homepage
    assert (out / ".nojekyll").is_file()

    for slug in EXAMPLES:
        page = out / "examples" / slug
        src = ROOT / "examples" / slug / "model.py"
        displayed = (page / "model.py").read_bytes()
        assert displayed == src.read_bytes(), slug
        expected = load_script(src).to_dict()
        actual = json.loads((page / "commands.json").read_text(encoding="utf-8"))
        assert expected == actual, slug
        assert len(actual["commands"]) == manifest["examples"][slug]["command_count"]
        assert (page / "preview.png").stat().st_size > 1000
        assert (page / "model.sc").stat().st_size > 1000
        assert zipfile.is_zipfile(page / "model.sc"), slug
        with zipfile.ZipFile(page / "model.sc") as z:
            assert json.loads(z.read("document.json"))["format"] == "solidcraft/48"
        measurements = json.loads((page / "measurements.json").read_text(encoding="utf-8"))
        assert measurements["body_count"] == 1
        assert measurements["timeline"] and all(
            item.get("error") is None for item in measurements["timeline"]
        )
        html = (page / "index.html").read_text(encoding="utf-8")
        assert "SCPC Python" in html
        assert "Real feature history" in html
        assert 'href="model.sc"' in html
        assert 'href="model.py"' in html
        assert 'href="commands.json"' in html
        for item in actual["commands"]:
            assert item["command"] in html
    for name in DOCS:
        html = (out / "guide" / name / "index.html").read_text(encoding="utf-8")
        assert "<h1" in html and "<pre" in html, name
        assert "lib.py.solidcraft.cmd" in html

    visited = 0
    for page in out.rglob("*.html"):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.links:
            if href.startswith(("https://", "http://", "#", "mailto:", "data:")):
                continue
            # Site URLs are relative to the page, so deployment under the
            # GitHub Pages project prefix /lib.py.solidcraft.cmd/ is safe.
            relative = href.split("#", 1)[0].split("?", 1)[0]
            target = (page.parent / relative).resolve()
            if target.is_dir():
                target /= "index.html"
            assert target.is_relative_to(out.resolve()), f"Link escapes site: {page}: {href}"
            assert target.is_file(), f"Broken internal link: {page.relative_to(out)} -> {href}"
            visited += 1
    assert visited >= 35, visited
    print(f"SCPC GitHub Pages: {2 + len(DOCS)} reference/model pages, {visited} valid local links")
    print(f"Verified native models: {', '.join(EXAMPLES)}; source commit: {sha}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("sha")
    args = parser.parse_args()
    check(args.site.resolve(), args.sha)
