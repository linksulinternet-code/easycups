#!/usr/bin/env python3
"""Publish a signed channel to its existing static Vercel project after CI gates."""
import base64
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def request(url, token=None, body=None):
    headers={'Accept':'application/json','User-Agent':'LinkSul-Release/1'}
    if token:headers['Authorization']='Bearer '+token
    if body is not None:headers['Content-Type']='application/json'
    req=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)


def publish():
    policy=json.loads((ROOT/'updates/policy.json').read_text())
    app=policy['app'];config=json.loads((ROOT/app/'update-channel.json').read_text())
    if not config.get('enabled'):raise ValueError('Canal não ativado.')
    required=('VERCEL_TOKEN','VERCEL_ORG_ID','VERCEL_PROJECT_ID','GITHUB_TOKEN','GITHUB_REPOSITORY','GITHUB_SHA')
    values={name:os.environ.get(name,'') for name in required}
    if not all(values.values()):raise ValueError('Configure os secrets/variables de publicação no ambiente protegido.')
    sha=values['GITHUB_SHA'];repo=values['GITHUB_REPOSITORY']
    if repo!=policy['repository']:raise ValueError('Repositório incorreto.')
    runs=request('https://api.github.com/repos/'+repo+'/actions/runs?'+urllib.parse.urlencode({'head_sha':sha,'per_page':100}),values['GITHUB_TOKEN'])['workflow_runs']
    for name in policy['required_workflows']:
        matching=[r for r in runs if r['head_sha']==sha and r['name']==name]
        latest=max(matching,key=lambda r:r['id']) if matching else None
        if latest is None or latest['status']!='completed' or latest['conclusion']!='success':
            raise ValueError('CI obrigatório ausente ou sem sucesso: '+name)
    team=values['VERCEL_ORG_ID'];project=values['VERCEL_PROJECT_ID'];token=values['VERCEL_TOKEN']
    query=urllib.parse.urlencode({'teamId':team})
    metadata=request('https://api.vercel.com/v9/projects/'+urllib.parse.quote(project,safe='')+'?'+query,token)
    if metadata.get('framework') is not None:raise ValueError('O canal exige projeto estático exclusivo.')
    domains=request('https://api.vercel.com/v9/projects/'+urllib.parse.quote(project,safe='')+'/domains?'+query,token)['domains']
    feed=urllib.parse.urlsplit(config['feed'])
    if feed.path != '/updates/'+app+'/latest.json' or feed.query or feed.fragment:
        raise ValueError('Caminho do canal inválido.')
    if feed.hostname not in [d['name'] for d in domains]:raise ValueError('Origem do canal não pertence ao projeto Vercel.')
    static=ROOT/'site/dist'
    if not (static/'index.html').is_file():raise ValueError('Site estático do canal ausente; configure antes de publicar.')
    channel=static/'updates'/app;channel.mkdir(parents=True,exist_ok=True)
    release=json.loads((ROOT/'dist/updates/latest.json').read_text())
    for name in ('latest.json','latest.json.sig',Path(urllib.parse.urlsplit(release['url']).path).name):
        (channel/name).write_bytes((ROOT/'dist/updates'/name).read_bytes())
    files=[]
    for file in sorted(static.rglob('*')):
        if file.is_symlink():raise ValueError('Link simbólico na saída pública.')
        if not file.is_file():continue
        rel=file.relative_to(static)
        if any(part.startswith('.') for part in rel.parts):raise ValueError('Arquivo oculto não permitido na publicação.')
        if file.stat().st_size>64*1024*1024:raise ValueError('Arquivo público excessivo.')
        files.append(dict(file=rel.as_posix(),data=base64.b64encode(file.read_bytes()).decode(),encoding='base64'))
    result=request('https://api.vercel.com/v13/deployments?'+query,token,dict(name=metadata['name'],project=project,target='production',files=files,
        projectSettings=dict(framework=None,buildCommand=None,installCommand=None,outputDirectory=None),meta=dict(app=app,source=sha)))
    deployment=result['id'];deadline=time.monotonic()+300
    while result.get('readyState') not in ('READY','ERROR','CANCELED') and time.monotonic()<deadline:
        time.sleep(5)
        result=request('https://api.vercel.com/v13/deployments/'+deployment+'?'+query,token)
    if result.get('readyState')!='READY':raise ValueError('Publicação não confirmada. Consulte o deployment antes de repetir: '+deployment)
    # Anonymous confirmation must match the exact signed release; never print credentials.
    with urllib.request.urlopen(config['feed'],timeout=30) as response:served=response.read(32769)
    if served!=(ROOT/'dist/updates/latest.json').read_bytes():raise ValueError('Canal servido não corresponde ao manifesto publicado: '+deployment)
    print('SIGNED_CHANNEL_PUBLISHED',deployment,release['version'])


if __name__=='__main__':publish()
