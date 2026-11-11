"""Ask SolidCraft for its authoritative command registry/schemas.

Do not freeze a second manual catalog of native command IDs or parameters.
"""
import json
import shutil
import subprocess

from .live import request


def commands(*, executable="solidcraft-cli", timeout=15):
    """Return the raw result of `solidcraft-cli commands` (engine.commands).

    The exact payload follows the installed SolidCraft version.
    """
    cli = shutil.which(executable)
    if not cli:
        raise RuntimeError(f"{executable} not found; cannot discover commands")
    result = subprocess.run(
        [cli, "commands"], check=True, capture_output=True, text=True,
        timeout=timeout,
    )
    return json.loads(result.stdout)


def describe(command, *, connect="auto"):
    """Use SolidCraft's live `engine.describe` for input/output schemas."""
    if not isinstance(command, str) or not command.strip():
        raise ValueError("Command ID required")
    return request("engine.describe", params={"command": command},
                   connect=connect)
