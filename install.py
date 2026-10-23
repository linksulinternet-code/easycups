#!/usr/bin/env python3
"""Instalador EasyCUPS por usuário, com assistente gráfico opcional."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

APP_ID = 'io.github.easycups.EasyCUPS'

def paths():
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME precisa ser um caminho absoluto.')
    return data / 'easycups', home / '.local/bin/easycups', data / f'applications/{APP_ID}.desktop'

def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'

def install_files():
    if os.geteuid() == 0:
        raise ValueError('Execute como usuário comum, sem sudo.')
    source = Path(__file__).resolve().parent / 'easycups'
    if not (source / '__main__.py').is_file():
        raise ValueError('Instalador incompleto. Baixe novamente pelo site oficial.')
    target, launcher, desktop = paths()
    if target.is_symlink() or launcher.is_symlink() or desktop.is_symlink():
        raise ValueError('Um destino é um link simbólico. Revise a instalação anterior antes de continuar.')
    target.parent.mkdir(parents=True, exist_ok=True)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Preparar antes de substituir; conservar a instalação anterior se a cópia falhar.
    with tempfile.TemporaryDirectory(prefix='.easycups-', dir=target.parent) as temp:
        staged = Path(temp) / 'new'
        staged.mkdir()
        shutil.copytree(source, staged / 'easycups', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy2(Path(__file__), staged / 'uninstall.py')
        old = Path(temp) / 'previous'
        launcher_previous = launcher.read_bytes() if launcher.exists() else None
        desktop_previous = desktop.read_bytes() if desktop.exists() else None
        existed = target.exists()
        if existed: target.rename(old)
        try:
            staged.rename(target)
            launcher.write_text('#!/bin/sh\ncd ' + shlex.quote(str(target)) + ' || exit 1\nexec python3 -m easycups "$@"\n')
            launcher.chmod(0o755)
            desktop.write_text('[Desktop Entry]\nType=Application\nName=EasyCUPS\nComment=Instale e gerencie sua impressora\nExec=' + desktop_quote(launcher) + '\nIcon=printer\nTerminal=false\nCategories=Settings;HardwareSettings;\nStartupNotify=true\n')
        except Exception:
            if target.exists(): shutil.rmtree(target)
            if existed: old.rename(target)
            for dest, previous in ((launcher, launcher_previous), (desktop, desktop_previous)):
                if previous is None: dest.unlink(missing_ok=True)
                else: dest.write_bytes(previous)
            raise
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(desktop.parent)], capture_output=True)
    return launcher

def uninstall_files():
    if os.geteuid() == 0: raise ValueError('Execute como usuário comum, sem sudo.')
    target, launcher, desktop = paths()
    if target.is_symlink(): raise ValueError('Destino inesperado: link simbólico.')
    for path in (launcher, desktop): path.unlink(missing_ok=True)
    if target.exists(): shutil.rmtree(target)

def graphical():
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import Adw, Gtk
        if (Adw.get_major_version(), Adw.get_minor_version()) < (1,5):
            raise ValueError('libadwaita 1.5 ou posterior é necessária.')
    except (ImportError, ValueError) as error:
        print('Abra o instalador .run para preparar as dependências. ' + str(error), file=sys.stderr)
        return 2
    class Wizard(Adw.Application):
        def __init__(self):
            super().__init__(application_id=APP_ID + '.Installer')
            self.connect('activate', self.activate_window)
        def activate_window(self, *_):
            window = Adw.ApplicationWindow(application=self, title='Instalar EasyCUPS', default_width=540, default_height=510)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=30, margin_bottom=30, margin_start=32, margin_end=32)
            box.append(Gtk.Image(icon_name='printer-symbolic', pixel_size=68))
            title = Gtk.Label(label='Sua impressora, mais fácil.')
            title.add_css_class('title-1'); box.append(title)
            body = Gtk.Label(label='O computador está pronto. Vamos criar o atalho do EasyCUPS no seu menu de aplicativos.\n\nSuas impressoras e configurações serão preservadas.', wrap=True, justify=Gtk.Justification.CENTER)
            box.append(body)
            button = Gtk.Button(label='Instalar EasyCUPS'); button.add_css_class('suggested-action'); box.append(button)
            status = Gtk.Label(label='Instalação no seu usuário • sem senha nesta etapa', wrap=True)
            status.add_css_class('dim-label'); box.append(status)
            def clicked(*_):
                try: launcher = install_files()
                except (OSError, ValueError) as error:
                    status.set_label('Não foi possível instalar: ' + str(error)); return
                title.set_label('Pronto para começar!')
                body.set_label('EasyCUPS já aparece no menu. Ligue a impressora por USB ou conecte-a à mesma rede Wi-Fi. Depois, clique em “Procurar minha impressora”.')
                status.set_label('Instalação concluída. A impressão será configurada dentro do aplicativo.')
                button.set_label('Abrir EasyCUPS')
                button.disconnect(handler)
                def launch(*_):
                    try: subprocess.Popen([str(launcher)], start_new_session=True)
                    except OSError as error: status.set_label(str(error)); return
                    self.quit()
                button.connect('clicked', launch)
            handler = button.connect('clicked', clicked)
            window.set_content(box); window.present()
    return Wizard().run([])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui', action='store_true', help='abrir assistente gráfico')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    try:
        if args.uninstall:
            uninstall_files(); print('EasyCUPS removido. Impressoras e CUPS preservados.'); return 0
        if args.gui: return graphical()
        launcher = install_files(); print('Instalado. Abra EasyCUPS no menu ou execute: ' + str(launcher)); return 0
    except (OSError, ValueError) as error:
        print('Instalação não concluída: ' + str(error), file=sys.stderr); return 1
if __name__ == '__main__': sys.exit(main())
