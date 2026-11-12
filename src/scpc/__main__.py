"""SCPC — export and execute explicit native SolidCraft Python command scripts."""
import argparse
from pathlib import Path

from .runner import load_script
from .script import Script
from .native import run_cli, CliError
from .live import send_batch, LiveError
from .discovery import commands, describe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", nargs="?", type=Path,
                        help="Trusted SCPC Python model.py or native commands.json")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--out", type=Path, help="Export standard native JSON")
    actions.add_argument("--run", action="store_true",
                         help="Run headless via solidcraft-cli (strict validation)")
    actions.add_argument("--connect", nargs="?", const="auto", metavar="PORT",
                         help="Apply to the open GUI as a rollback batch")
    actions.add_argument("--commands", action="store_true",
                         help="Print the SolidCraft CLI command registry")
    actions.add_argument("--describe", metavar="ID",
                         help="Show a command's live native input/output schema")
    parser.add_argument("--save", type=Path,
                        help="With --run, also save an editable .sc design")
    parser.add_argument("--cli", default="solidcraft-cli",
                        help="Path/name of the native SolidCraft CLI")
    args = parser.parse_args(argv)
    if args.save and not args.run:
        parser.error("--save requires --run")
    if args.commands:
        if args.script:
            parser.error("--commands does not accept a script")
        import json
        print(json.dumps(commands(executable=args.cli), indent=2))
        return 0
    if args.describe:
        if args.script:
            parser.error("--describe does not accept a script")
        import json
        print(json.dumps(describe(args.describe), indent=2))
        return 0
    if args.script is None:
        parser.error("a model.py file is required")
    if not (args.out or args.run or args.connect):
        parser.error("choose --out, --run or --connect")
    if args.script.suffix.lower() == ".json":
        # JSON is data, never executed as Python. Keep the explicit .json
        # extension to prevent ambiguous or unsafe source interpretation.
        try:
            script = Script.load(args.script)
        except (OSError, ValueError) as exc:
            parser.exit(1, f"SCPC JSON: {exc}\n")
        if not len(script):
            parser.exit(1, "SCPC JSON: the command document is empty\n")
    else:
        script = load_script(args.script)
    if args.out is not None:
        path = script.save(args.out)
        print(f"{path}: {len(script)} native SolidCraft commands")
        return 0
    if args.run:
        try:
            print(run_cli(script, executable=args.cli, save=args.save))
        except CliError as exc:
            parser.exit(1, f"SCPC CLI: {exc}\n")
        return 0
    try:
        result = send_batch(script.commands, connect=args.connect)
    except LiveError as exc:
        parser.exit(1, f"SCPC live: {exc}\n")
    print(f"Applied {result['completed']} native commands to the open design")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
