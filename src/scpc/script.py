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

    @classmethod
    def from_dict(cls, document):
        """Import the exact native {"commands": [...]} format.

        Reject unexpected fields rather than silently changing or dropping
        native commands. This only checks JSON structure, not CAD semantics.
        """
        if not isinstance(document, dict) or set(document) != {"commands"}:
            raise ValueError("Expected a native document containing only 'commands'")
        entries = document["commands"]
        if not isinstance(entries, list):
            raise ValueError("Native 'commands' must be a list")
        script = cls()
        for index, entry in enumerate(entries):
            if (not isinstance(entry, dict)
                    or set(entry) != {"command", "params"}
                    or not isinstance(entry["params"], dict)):
                raise ValueError(
                    f"Invalid native command at index {index}: "
                    "expected 'command' and object 'params'"
                )
            try:
                script.add(entry["command"], **entry["params"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid native command at index {index}: {exc}"
                ) from exc
        return script

    @classmethod
    def from_json(cls, text):
        """Parse a native command document; never evaluate Python source."""
        try:
            return cls.from_dict(json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid native command JSON: {exc}") from exc

    @classmethod
    def load(cls, path):
        """Read commands saved as native JSON by SCPC or SolidCraft."""
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

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
