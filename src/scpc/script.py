"""Create *exactly* the native SolidCraft command JSON structure.

No command wrappers, custom geometry, matrix calculations or CAD rules.
The authoritative command IDs and parameters belong to SolidCraft.
"""
import json
from pathlib import Path


def _json_copy(value):
    # Reject unserialisable objects and NaN/Infinity early; also detach
    # mutable input values so later list/dict edits cannot change the plan.
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))


class Script:
    """Ordered native `{command, params}` entries.

    Example::

        script = Script()
        script.add("sketch.create", plane="XY", name="Base")
        script.add("sketch.finish")
        script.save("out/model.json")

    The original command ID and keyword parameter names are preserved.
    Validation against SolidCraft's current schema happens via
    `solidcraft-cli ... --param-check strict`, not a second hand-coded API.
    """

    def __init__(self):
        self._commands = []

    def add(self, command: str, /, **params):
        if not isinstance(command, str) or not command.strip():
            raise ValueError("A native SolidCraft command ID is required")
        if not all(isinstance(k, str) and k for k in params):
            raise ValueError("Parameter names must be nonempty strings")
        self._commands.append(_json_copy({"command": command, "params": params}))
        return self

    @property
    def commands(self):
        """Read-only-by-copy list in the native `engine.batch` format."""
        return _json_copy(self._commands)

    def to_dict(self):
        return {"commands": self.commands}

    def to_json(self, *, indent=2):
        return json.dumps(self.to_dict(), indent=indent,
                          ensure_ascii=False, allow_nan=False) + "\n"

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    def __len__(self):
        return len(self._commands)
