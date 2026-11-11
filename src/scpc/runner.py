"""Load one trusted SCPC model.py; never interpret untrusted Python.

The file declares exactly one `Script` instance, usually `script = Script()`.
No show(), special model base class or main() function is required.
"""
import runpy
import sys
from contextlib import contextmanager
from pathlib import Path

from .script import Script


@contextmanager
def _project_imports(file):
    # Allow models/<category>/<name>/scpc/model.py to import from the
    # CAD project's shared components/ package if explicitly needed.
    roots = [file.parent]
    for parent in file.parents:
        if parent.name == "models":
            roots.append(parent.parent)
            break
    original = sys.path[:]
    try:
        for root in reversed(roots):
            folder = str(root)
            if folder in sys.path:
                sys.path.remove(folder)
            sys.path.insert(0, folder)
        yield
    finally:
        sys.path[:] = original


def load_script(path):
    file = Path(path).resolve()
    with _project_imports(file):
        namespace = runpy.run_path(str(file), run_name="__scpc_model__")
    candidates = {id(value): value for value in namespace.values()
                  if isinstance(value, Script)}
    if len(candidates) != 1:
        raise ValueError(
            f"{file}: expected exactly one Script instance, found {len(candidates)}"
        )
    script = next(iter(candidates.values()))
    if not len(script):
        raise ValueError(f"{file}: the Script contains no commands")
    return script
