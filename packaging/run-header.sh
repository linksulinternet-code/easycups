#!/bin/sh
# EasyCUPS: instalador autocontido. Não requer chmod quando aberto com sh.
set -eu
case "${1:-}" in
    --help|-h) echo 'EasyCUPS — sh EasyCUPS-1.2.0.run [--check | --extract PASTA]'; exit 0 ;;
    --check) EASYCUPS_CHECK_ONLY=1; export EASYCUPS_CHECK_ONLY ;;
    --extract) [ "$#" = 2 ] || { echo 'Use --extract PASTA'; exit 2; } ;;
    '') ;;
    *) echo 'Opção desconhecida. Use --help.' >&2; exit 2 ;;
esac
if [ -z "${1:-}" ] && [ ! -t 0 ] && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    self=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/$(basename -- "$0")
    if command -v gnome-terminal >/dev/null 2>&1; then exec gnome-terminal --wait -- sh "$self"; fi
    if command -v konsole >/dev/null 2>&1; then exec konsole --nofork -e sh "$self"; fi
    if command -v xterm >/dev/null 2>&1; then exec xterm -hold -e sh "$self"; fi
    echo 'Abra a pasta Downloads no terminal e execute: sh EasyCUPS-1.2.0.run' >&2
    exit 2
fi
for tool in awk tail base64 tar sha256sum mktemp; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Ferramenta necessária: $tool" >&2; exit 2; }
done
scratch=$(mktemp -d "${TMPDIR:-/tmp}/easycups.XXXXXXXX")
trap 'rm -rf -- "$scratch"' EXIT HUP INT TERM
line=$(awk '/^__EASYCUPS_PAYLOAD__$/ { print NR + 1; exit }' "$0")
[ -n "$line" ] || { echo 'Instalador incompleto.' >&2; exit 2; }
tail -n +"$line" "$0" | base64 -d > "$scratch/payload.tar.gz"
printf '%s  %s\n' '@PAYLOAD_SHA256@' "$scratch/payload.tar.gz" | sha256sum -c - >/dev/null || { echo 'Download corrompido. Baixe novamente.' >&2; exit 2; }
if [ "${1:-}" = --extract ]; then
    [ ! -e "$2" ] || { echo 'A pasta de destino já existe. Escolha outra.' >&2; exit 2; }
    mkdir -p -- "$2"
    tar -xzf "$scratch/payload.tar.gz" -C "$2"
    echo "Extraído em $2"; exit 0
fi
mkdir "$scratch/app"
tar -xzf "$scratch/payload.tar.gz" -C "$scratch/app"
sh "$scratch/app/packaging/bootstrap.sh"
exit 0
__EASYCUPS_PAYLOAD__
