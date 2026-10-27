"""Validate update policy without credentials, personal data, network or deployments."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=json.loads((root/'updates/policy.json').read_text())
assert p['schema']==1
assert p['kind'] in ('desktop','web','library','data')
assert p['dependency_updates']=='pull_request'
assert p['automatic_dependency_merge'] is False
assert p['preserve_user_data'] is True
assert p['production_requires_validated_release'] is True
assert p['automatic_data_approval'] is False
assert '.github/dependabot.yml' in (root/'docs/ATUALIZACOES.md').read_text()
assert 'docs/ATUALIZACOES.md' in (root/'README.md').read_text()
assert 'github-actions' in (root/'.github/dependabot.yml').read_text()
if p['kind']=='desktop':
 import subprocess,sys
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*update*.py','-v'])
 if result.returncode:raise SystemExit(result.returncode)
 config=json.loads((root/p['app']/'update-channel.json').read_text())
 assert 'PRIVATE KEY' not in config['public_key'] and 'PUBLIC KEY' in config['public_key']
if p['kind']=='web':
 import subprocess
 result=subprocess.run(['node','--test','tests/updates.test.mjs'])
 if result.returncode:raise SystemExit(result.returncode)
print('UPDATE_POLICY_PASS')
