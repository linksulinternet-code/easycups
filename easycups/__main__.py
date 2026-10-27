# Apply only verified per-user updates before importing application modules.
if __name__ == "__main__":
    from pathlib import Path as _UpdatePath
    from .auto_update import bootstrap as _bootstrap_update
    _bootstrap_update(_UpdatePath(__file__).parent)

import argparse, json, shutil, sys
from . import __version__
from .core import run

def main():
    parser = argparse.ArgumentParser(description="EasyCUPS — gerenciador de impressoras Linux")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--doctor", action="store_true", help="diagnóstico JSON, sem alterações ou GTK")
    args = parser.parse_args()
    if args.doctor:
        commands = {k: bool(shutil.which(k)) for k in ("lpstat", "lpadmin", "lpinfo", "lp", "cancel", "pkexec")}
        ok, output = run(["lpstat", "-r"], timeout=10)
        print(json.dumps({"version": __version__, "commands": commands, "scheduler_running": ok and "scheduler is running" in output, "scheduler_output": output}, ensure_ascii=False, indent=2))
        return 0 if all(commands.values()) and ok else 1
    try:
        from .gui import A
    except (ImportError, ValueError) as error:
        print("Instale Python 3, PyGObject, GTK >= 4.10 e libadwaita >= 1.5 pela sua distro. Detalhe: " + str(error), file=sys.stderr)
        return 2
    return A().run()

if __name__ == "__main__":
    sys.exit(main())
