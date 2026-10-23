#!/usr/bin/env python3
"""Instala somente arquivos EasyCUPS no perfil atual. Nunca altera CUPS."""
import argparse, os, pathlib, shlex, shutil, sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    home = pathlib.Path.home()
    data = pathlib.Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    target = data / 'easycups'
    launcher = home / '.local/bin/easycups'
    desktop = data / 'applications/io.github.easycups.EasyCUPS.desktop'
    if os.geteuid() == 0:
        parser.error('Execute como usuário comum, sem sudo.')
    if args.uninstall:
        for path in (launcher, desktop):
            if path.exists(): path.unlink()
        if target.exists(): shutil.rmtree(target)
        print('EasyCUPS removido. Impressoras e CUPS preservados.')
        return
    source = pathlib.Path(__file__).resolve().parent / 'easycups'
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target / 'easycups', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('#!/bin/sh\ncd ' + shlex.quote(str(target)) + ' || exit 1\nexec python3 -m easycups "$@"\n')
    launcher.chmod(0o755)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    exec_path = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%','%%')
    desktop.write_text('[Desktop Entry]\nType=Application\nName=EasyCUPS\nComment=Gerencie impressoras CUPS\nExec="' + exec_path + '"\nIcon=printer\nTerminal=false\nCategories=Settings;HardwareSettings;\n')
    print('Instalado. Abra EasyCUPS no menu ou execute: ' + str(launcher))
if __name__ == '__main__': main()
