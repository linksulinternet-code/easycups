#!/bin/sh
# Executado como usuário; somente o gerenciador de pacotes recebe privilégios.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ "$(id -u)" = 0 ]; then
    echo 'Abra o instalador como usuário comum, sem sudo. A senha será solicitada quando necessária.' >&2
    exit 1
fi
check_environment() {
    command -v python3 >/dev/null 2>&1 || return 1
    python3 -c 'import sys; assert sys.version_info >= (3,9); import gi; gi.require_version("Gtk","4.0"); gi.require_version("Adw","1"); from gi.repository import Gtk,Adw; assert (Gtk.get_major_version(),Gtk.get_minor_version()) >= (4,10); assert (Adw.get_major_version(),Adw.get_minor_version()) >= (1,5)' >/dev/null 2>&1 || return 1
    for tool in openssl lpstat lpadmin lpinfo lp cancel pkexec; do command -v "$tool" >/dev/null 2>&1 || return 1; done
}
manager=''
# Imutáveis devem usar seus mecanismos próprios; não tentar apt/dnf internos.
if [ -e /run/ostree-booted ] || [ -e /etc/NIXOS ]; then
    echo 'Sistema imutável/declarativo: use o método de pacotes da sua distribuição. Nada foi alterado.' >&2
    exit 2
fi
if command -v apt-get >/dev/null 2>&1; then
    manager=apt-get
    set -- apt-get install -y openssl python3 python3-gi 'gir1.2-gtk-4.0' 'gir1.2-adw-1' cups cups-client cups-filters pkexec
elif command -v dnf >/dev/null 2>&1; then
    manager=dnf
    set -- dnf install -y openssl python3 python3-gobject gtk4 libadwaita cups cups-client cups-filters polkit
elif command -v zypper >/dev/null 2>&1; then
    manager=zypper
    set -- zypper --non-interactive install openssl python3 python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 cups cups-client cups-filters polkit
elif command -v pacman >/dev/null 2>&1; then
    manager=pacman
    set -- pacman -S --needed openssl python python-gobject gtk4 libadwaita cups cups-filters polkit
elif command -v apk >/dev/null 2>&1; then
    manager=apk
    set -- apk add openssl python3 py3-gobject3 gtk4.0 libadwaita cups cups-client cups-filters polkit
elif command -v xbps-install >/dev/null 2>&1; then
    manager=xbps-install
    set -- xbps-install -S openssl python3 python3-gobject gtk4 libadwaita cups cups-filters polkit
fi
if [ "${EASYCUPS_CHECK_ONLY:-0}" = 1 ]; then
    echo "Gerenciador: ${manager:-não reconhecido}"
    if check_environment; then echo 'Ambiente pronto.'; exit 0; fi
    echo 'O instalador precisará preparar as dependências.'
    exit 3
fi
if ! check_environment; then
    [ -n "$manager" ] || { echo 'Gerenciador não reconhecido. Consulte https://easycups.vercel.app/#ajuda' >&2; exit 2; }
    echo 'EasyCUPS — Preparar o computador'
    echo 'Serão instalados Python, interface gráfica, CUPS e autorização administrativa pelo repositório da sua distro.'
    echo 'O gerenciador de pacotes poderá iniciar o CUPS. Impressoras existentes serão preservadas.'
    printf 'Comando: '; printf '%s ' "$@"; printf '\n'
    printf 'Continuar? [s/N] '
    read -r answer || exit 1
    case "$answer" in s|S|sim|SIM) ;; *) echo 'Cancelado. Nada foi instalado.'; exit 1 ;; esac
    if command -v sudo >/dev/null 2>&1; then
        sudo -- "$@"
    elif command -v pkexec >/dev/null 2>&1; then
        pkexec -- "$@"
    elif command -v doas >/dev/null 2>&1; then
        doas -- "$@"
    else
        echo 'Não há sudo, pkexec ou doas. Peça ao administrador para instalar as dependências acima.' >&2
        exit 2
    fi
    if ! check_environment; then
        echo 'A preparação não ficou completa. Sua distro precisa oferecer GTK 4.10+ e libadwaita 1.5+.' >&2
        echo 'Não será adicionado repositório de terceiros. Consulte https://easycups.vercel.app/#ajuda' >&2
        exit 2
    fi
fi
exec python3 install.py --gui
