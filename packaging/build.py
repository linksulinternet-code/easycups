#!/usr/bin/env python3
"""Gera downloads autocontidos e pacote Debian a partir do código atual."""
from pathlib import Path
import base64, gzip, hashlib, io, json, os, shutil, subprocess, tarfile, tempfile
ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.2.0'
DIST = ROOT / 'site/dist/downloads'

def payload():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
        for parent in ['easycups', 'packaging', 'tests']:
            for path in sorted((ROOT / parent).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts:
                    info = tar.gettarinfo(str(path), arcname=str(path.relative_to(ROOT)))
                    info.uid = info.gid = 0; info.uname = info.gname = ''; info.mtime = 0
                    with path.open('rb') as file: tar.addfile(info, file)
        for name in ['install.py', 'README.md', 'NOTICE.md']:
            path = ROOT / name
            info = tar.gettarinfo(str(path), arcname=name)
            info.uid = info.gid = 0; info.uname = info.gname = ''; info.mtime = 0
            with path.open('rb') as file: tar.addfile(info, file)
    return gzip.compress(buffer.getvalue(), mtime=0)

def build_deb(output):
    with tempfile.TemporaryDirectory(prefix='easycups-deb-') as temp:
        root = Path(temp)
        package = root / 'usr/lib/easycups/easycups'
        shutil.copytree(ROOT / 'easycups', package, ignore=shutil.ignore_patterns('__pycache__'))
        commands = root / 'usr/bin'; commands.mkdir(parents=True)
        launcher = commands / 'easycups'
        launcher.write_text('#!/bin/sh\ncd /usr/lib/easycups || exit 1\nexec /usr/bin/python3 -m easycups "$@"\n'); launcher.chmod(0o755)
        applications = root / 'usr/share/applications'; applications.mkdir(parents=True)
        (applications / 'io.github.easycups.EasyCUPS.desktop').write_text('[Desktop Entry]\nType=Application\nName=EasyCUPS\nComment=Instale e gerencie sua impressora\nExec=easycups\nIcon=printer\nTerminal=false\nCategories=Settings;HardwareSettings;\nStartupNotify=true\n')
        docs = root / 'usr/share/doc/easycups'; docs.mkdir(parents=True)
        for name in ['README.md', 'NOTICE.md']: shutil.copy2(ROOT / name, docs / name)
        control = root / 'DEBIAN'; control.mkdir()
        (control / 'control').write_text(f'''Package: easycups
Version: {VERSION}
Architecture: all
Maintainer: EasyCUPS <linksulbak@gmail.com>
Section: utils
Priority: optional
Homepage: https://easycups.vercel.app
Depends: python3 (>= 3.9), python3-gi, gir1.2-gtk-4.0 (>= 4.10), gir1.2-adw-1 (>= 1.5), cups, cups-client, cups-filters, pkexec
Description: Assistente de impressoras CUPS para Linux
 Interface em portugues para descobrir impressoras, configurar IPP,
 gerenciar filas e consultar o servico de impressao.
''')
        env = {**os.environ, 'SOURCE_DATE_EPOCH': '1792713600'}
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(root), str(output)], check=True, env=env)

def main():
    DIST.mkdir(parents=True, exist_ok=True)
    data = payload()
    source = DIST / f'easycups-{VERSION}.tar.gz'; source.write_bytes(data)
    header = (ROOT / 'packaging/run-header.sh').read_text().replace('@PAYLOAD_SHA256@', hashlib.sha256(data).hexdigest())
    runner = DIST / f'EasyCUPS-{VERSION}.run'
    runner.write_text(header + base64.encodebytes(data).decode('ascii'))
    runner.chmod(0o755)
    deb = DIST / f'easycups_{VERSION}_all.deb'; build_deb(deb)
    artifacts = [runner, deb, source]
    (DIST / 'SHA256SUMS').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in artifacts))
    release = {'version':VERSION, 'repository':'https://github.com/linksulinternet-code/easycups', 'artifacts':{path.suffix: {'file':'downloads/'+path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in artifacts}}
    (ROOT / 'site/dist/release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2)+'\n')
    print('Downloads preparados:', ', '.join(p.name for p in artifacts))
if __name__ == '__main__': main()
