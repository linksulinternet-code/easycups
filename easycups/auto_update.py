"""Signed per-user updates. No root, telemetry, or modification of system packages."""
import base64
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.parse
import urllib.request

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_MANIFEST = 32768


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise ValueError('Versão inválida; somente versões finais x.y.z.')
    return tuple(map(int, value.split('.')))


def https_url(value, origin=None):
    p = urllib.parse.urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError('Canal de atualização precisa de HTTPS sem credenciais na URL.')
    if origin and (p.scheme, p.netloc) != (origin.scheme, origin.netloc):
        raise ValueError('Arquivo fora da origem de atualização aprovada.')
    return p


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl, urllib.parse.urlsplit(req.full_url))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, limit):
    https_url(url)
    req = urllib.request.Request(url, headers={'User-Agent': 'LinkSul-Updater/1', 'Cache-Control': 'no-cache'})
    opener = urllib.request.build_opener(SameOriginRedirect())
    with opener.open(req, timeout=15) as response:
        https_url(response.url, urllib.parse.urlsplit(url))
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Atualização excede o tamanho permitido.')
    return data


def verify(payload, signature, public_key):
    if len(payload) > MAX_MANIFEST:
        raise ValueError('Manifesto excessivo.')
    raw = base64.b64decode(signature, validate=True)
    if len(raw) != 64:
        raise ValueError('Assinatura inválida.')
    with tempfile.TemporaryDirectory(prefix='linksul-verify-') as tmp:
        root = Path(tmp)
        (root/'key.pem').write_text(public_key)
        (root/'manifest').write_bytes(payload)
        (root/'signature').write_bytes(raw)
        result = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', str(root/'key.pem'),
                                 '-rawin', '-in', str(root/'manifest'), '-sigfile', str(root/'signature')],
                                capture_output=True, timeout=10)
        if result.returncode:
            raise ValueError('Assinatura da atualização não confere.')


def manifest(payload, signature, config):
    verify(payload, signature, config['public_key'])
    data = json.loads(payload)
    if data.get('schema') != 1 or data.get('app') != config['app'] or data.get('channel') != 'stable':
        raise ValueError('Canal ou aplicativo incompatível.')
    version(data['version'])
    if data.get('python_min') != [3, 10] or sys.version_info < (3, 10):
        raise ValueError('Atualize o Python pelo gerenciador do sistema.')
    https_url(data['url'], https_url(config['feed']))
    if not re.fullmatch('[a-f0-9]{64}', data.get('sha256', '')):
        raise ValueError('Hash inválido.')
    if type(data.get('size')) is not int or not 0 < data['size'] <= MAX_ARCHIVE:
        raise ValueError('Tamanho inválido.')
    return data


def unpack(blob, destination, app):
    """Extract regular package files only; reject links, traversal and archive bombs."""
    total, seen = 0, set()
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (len(seen) >= 5000 or member.name in seen or name.is_absolute() or '..' in name.parts
                    or not name.parts or name.parts[0] != app or '\\' in member.name
                    or not (member.isdir() or member.isfile()) or member.size < 0):
                raise ValueError('Estrutura de atualização insegura.')
            seen.add(member.name)
            total += member.size
            if total > MAX_EXPANDED:
                raise ValueError('Conteúdo descompactado excessivo.')
            target = destination.joinpath(*name.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, target.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                target.chmod(0o600)
    if not (destination/app/'__main__.py').is_file() or not (destination/app/'__init__.py').is_file():
        raise ValueError('Pacote de aplicativo incompleto.')
    # Compile without executing the downloaded code or writing bytecode.
    for file in (destination/app).rglob('*.py'):
        compile(file.read_bytes(), str(file), 'exec')


def state_root(app):
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME precisa ser absoluto.')
    root = data/app/'updates'
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_uid != os.getuid():
        raise ValueError('Pasta de atualização não pertence ao usuário.')
    root.chmod(0o700)
    return root


def atomic_json(path, data):
    fd, name = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def stage(config, current, fetch=download):
    if os.getuid() == 0:
        raise ValueError('Atualização deve rodar como usuário comum.')
    if not config.get('enabled'):
        return 'Canal ainda não ativado pelo mantenedor.'
    root = state_root(config['app'])
    with (root/'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'Outra atualização está em andamento.'
        payload = fetch(config['feed'], MAX_MANIFEST)
        signature = fetch(config['feed']+'.sig', 1024)
        data = manifest(payload, signature, config)
        active = selected(config, current)
        floor = active['version'] if active else current
        if version(data['version']) <= version(floor):
            return 'Você já usa a versão disponível.'
        failed = root/'failed.json'
        if failed.is_file() and json.loads(failed.read_text()).get('sha256') == data['sha256']:
            return 'Esta atualização falhou ao iniciar; aguardando uma versão corrigida.'
        blob = fetch(data['url'], MAX_ARCHIVE)
        if len(blob) != data['size'] or hashlib.sha256(blob).hexdigest() != data['sha256']:
            raise ValueError('Download incompleto ou modificado; versão anterior preservada.')
        # An immutable, hash-addressed copy is reverified before every launch.
        archive = root/(data['sha256']+'.tar.gz')
        if archive.is_symlink():
            raise ValueError('Destino de atualização inválido.')
        with tempfile.TemporaryDirectory(prefix='.stage-', dir=root) as tmp:
            unpack(blob, Path(tmp), config['app'])
            temporary = Path(tmp)/'package.tar.gz'
            temporary.write_bytes(blob)
            temporary.chmod(0o600)
            os.replace(temporary, archive)
        atomic_json(root/'active.json', {'payload':base64.b64encode(payload).decode(),
                                         'signature':signature.decode('ascii')})
        return 'Atualização preparada. Será usada na próxima abertura.'


def selected(config, bundled):
    root = state_root(config['app'])
    path = root/'active.json'
    if not path.is_file() or path.is_symlink():
        return None
    saved = json.loads(path.read_text())
    payload = base64.b64decode(saved['payload'], validate=True)
    data = manifest(payload, saved['signature'].encode('ascii'), config)
    if version(data['version']) <= version(bundled):
        return None
    archive = root/(data['sha256']+'.tar.gz')
    if archive.is_symlink() or archive.stat().st_size != data['size']:
        raise ValueError('Cópia local incompleta.')
    blob = archive.read_bytes()
    if hashlib.sha256(blob).hexdigest() != data['sha256']:
        raise ValueError('Cópia local modificada.')
    return data


def bootstrap(package):
    """Called before application imports. Ignore network failures; retain installed code."""
    if os.getuid() == 0 or len(sys.argv) > 1:
        return
    try:
        config = json.loads((Path(package)/'update-channel.json').read_text())
        current = config['bundled_version']
        version(current)
    except (OSError, ValueError, KeyError):
        return
    if not config.get('enabled'):
        return
    # A child already launched from a verified update must not recurse.
    if os.environ.pop('LINKSUL_UPDATE_CHILD', '') != config['app']:
        try:
            data = selected(config, current)
            if data:
                root = state_root(config['app'])
                with tempfile.TemporaryDirectory(prefix='.run-', dir=root) as tmp:
                    blob = (root/(data['sha256']+'.tar.gz')).read_bytes()
                    unpack(blob, Path(tmp), config['app'])
                    env = dict(os.environ, LINKSUL_UPDATE_CHILD=config['app'])
                    # Wait in this launcher so the temporary package lives until exit.
                    result = subprocess.run([sys.executable, '-I', '-c',
                        'import sys,runpy;root,app=sys.argv[1:];sys.argv=[app];sys.path.insert(0,root);runpy.run_module(app,run_name="__main__",alter_sys=True)',
                        tmp, config['app']], env=env)
                    if result.returncode != 0:
                        atomic_json(root/'failed.json', {'sha256':data['sha256']})
                        (root/'active.json').unlink(missing_ok=True)
                        return  # Launch the bundled application after a failed update.
                    raise SystemExit(result.returncode)
        except (OSError, ValueError, KeyError, SyntaxError, tarfile.TarError, subprocess.SubprocessError):
            pass  # Local corruption/offline must not block the installed application.
    def work():
        try:
            if config.get('enabled'):
                stage(config, current)
        except (OSError, ValueError, KeyError, SyntaxError, tarfile.TarError, subprocess.SubprocessError):
            pass
    threading.Thread(target=work, daemon=True, name='linksul-update').start()
