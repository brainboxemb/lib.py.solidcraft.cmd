"""Optionally execute the generated JSON through the official native CLI."""
import shutil
import subprocess
import tempfile
from pathlib import Path


class CliError(RuntimeError):
    """The installed SolidCraft CLI is missing or rejected a command script."""


def run_cli(script, *, executable="solidcraft-cli", save=None, timeout=300):
    """Run with strict *native* parameter checking in a headless session.

    This does not change the open SolidCraft GUI. Native error output is
    preserved verbatim; no second command validator is implemented here.
    """
    tool = shutil.which(executable)
    if not tool:
        raise CliError(f"{executable} not found on PATH")
    with tempfile.TemporaryDirectory(prefix="scpc-") as directory:
        path = Path(directory) / "commands.json"
        script.save(path)
        args = [tool, "run", str(path), "--param-check", "strict", "--results"]
        if save is not None:
            output = Path(save).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            args += ["--save", str(output)]
        try:
            result = subprocess.run(args, check=False, capture_output=True,
                                    text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CliError(f"Cannot execute SolidCraft CLI: {exc}") from exc
        if result.returncode:
            raise CliError(
                f"Native SolidCraft command run failed (exit {result.returncode}):\n"
                f"{result.stderr or result.stdout}"
            )
        return result.stdout
