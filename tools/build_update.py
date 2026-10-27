#!/usr/bin/env python3
"""Build a code-only update and sign metadata with the maintainer's Ed25519 key."""
import ast
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
policy = json.loads((ROOT/'updates/policy.json').read_text())
app = policy['app']
if not re.fullmatch('[a-z][a-z0-9_]+', app):
    raise ValueError('Pacote inválido.')
config = json.loads((ROOT/app/'update-channel.json').read_text())
if not config.get('enabled'):
    raise ValueError('Defina o canal HTTPS antes de publicar atualizações.')
from urllib.parse import urlsplit
feed = urlsplit(config['feed'])
if feed.scheme != 'https' or not feed.hostname or feed.username or feed.password or feed.query or feed.fragment:
    raise ValueError('Canal HTTPS inválido.')
version = config['bundled_version']
if not re.fullmatch(r'\d+\.\d+\.\d+', version):
    raise ValueError('Versão final x.y.z obrigatória.')
tag=os.environ.get('GITHUB_REF','')
if tag.startswith('refs/tags/') and tag.removeprefix('refs/tags/') not in (version,'v'+version):
    raise ValueError('Tag de release diverge do pacote.')
parsed = ast.parse((ROOT/app/'__init__.py').read_text())
actual = next(ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets))
if actual != version:
    raise ValueError('Versão do canal diverge do aplicativo.')
out = ROOT/'dist/updates';out.mkdir(parents=True,exist_ok=True)
name = f'{app}-{version}.tar.gz'
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode='w') as tar:
    for path in sorted((ROOT/app).rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc':continue
        if path.is_symlink():raise ValueError('Link simbólico no pacote.')
        if not path.is_file():continue
        rel = path.relative_to(ROOT).as_posix()
        if path.stat().st_size > 64*1024*1024:raise ValueError('Arquivo excessivo.')
        info = tarfile.TarInfo(rel);info.size=path.stat().st_size;info.mode=0o600
        with path.open('rb') as f:tar.addfile(info,f)
blob=gzip.compress(buffer.getvalue(),mtime=0)
if len(blob)>64*1024*1024:raise ValueError('Pacote excessivo.')
(out/name).write_bytes(blob)
manifest=dict(schema=1,app=app,channel='stable',version=version,python_min=[3,10],
              url=config['feed'].rsplit('/',1)[0]+'/'+name,size=len(blob),sha256=hashlib.sha256(blob).hexdigest())
payload=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
(out/'latest.json').write_bytes(payload)
key=os.environ.get('LINKSUL_UPDATE_SIGNING_KEY','')
if not key:raise ValueError('Chave de assinatura ausente; nenhum canal deve ser promovido.')
signed=subprocess.run(['openssl','pkeyutl','-sign','-inkey','/dev/stdin','-rawin','-in',str(out/'latest.json')],input=key.encode(),capture_output=True,timeout=10,check=True).stdout
(out/'latest.json.sig').write_bytes(base64.b64encode(signed))
# Fail closed if the configured secret does not correspond to the installed public key.
import importlib.util
spec=importlib.util.spec_from_file_location('update_verify',ROOT/app/'auto_update.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
u.manifest(payload,base64.b64encode(signed),config)
print('Pacote e manifesto assinados. Publicar somente estes três arquivos no canal HTTPS aprovado.')
