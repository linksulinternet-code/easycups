"""Publication gates are exercised without GitHub/Vercel credentials or network."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('channel_publish',ROOT/'tools/publish_update.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class PublicationGates(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'updates').mkdir();(self.root/'sample').mkdir()
        (self.root/'updates/policy.json').write_text(json.dumps(dict(app='sample',repository='example/sample',required_workflows=['required-ci'])))
        (self.root/'sample/update-channel.json').write_text(json.dumps(dict(enabled=True,feed='https://downloads.example.invalid/updates/sample/latest.json')))
        self.env=patch.dict(os.environ,dict(VERCEL_TOKEN='synthetic-token',VERCEL_ORG_ID='synthetic-team',VERCEL_PROJECT_ID='synthetic-project',GITHUB_TOKEN='synthetic-token',GITHUB_REPOSITORY='example/sample',GITHUB_SHA='a'*40))
        self.env.start();self.path=patch.object(p,'ROOT',self.root);self.path.start()

    def tearDown(self):self.path.stop();self.env.stop();self.tmp.cleanup()

    def test_missing_credentials_or_wrong_repository_never_calls_network(self):
        with patch.object(p,'request') as request:
            with patch.dict(os.environ,{'VERCEL_TOKEN':''}):
                with self.assertRaises(ValueError):p.publish()
            with patch.dict(os.environ,{'GITHUB_REPOSITORY':'other/repo'}):
                with self.assertRaises(ValueError):p.publish()
            request.assert_not_called()

    def test_missing_failed_or_wrong_commit_ci_prevents_deployment(self):
        cases=[[],[dict(name='required-ci',head_sha='a'*40,id=1,status='completed',conclusion='failure')],[dict(name='required-ci',head_sha='b'*40,id=1,status='completed',conclusion='success')]]
        for runs in cases:
            with patch.object(p,'request',return_value={'workflow_runs':runs}) as request:
                with self.assertRaises(ValueError):p.publish()
                self.assertEqual(request.call_count,1)

    def test_wrong_framework_or_domain_prevents_deployment(self):
        ci={'workflow_runs':[dict(name='required-ci',head_sha='a'*40,id=1,status='completed',conclusion='success')]}
        for metadata,domain in (({'framework':'nextjs'},None),({'framework':None},{'domains':[{'name':'other.example.invalid'}]})):
            with patch.object(p,'request',side_effect=[ci,metadata,domain]) as request:
                with self.assertRaises(ValueError):p.publish()
                self.assertTrue(all(call.args[2:] == () for call in request.call_args_list))

    def test_static_site_missing_stops_before_creation(self):
        ci={'workflow_runs':[dict(name='required-ci',head_sha='a'*40,id=1,status='completed',conclusion='success')]}
        with patch.object(p,'request',side_effect=[ci,{'framework':None},{'domains':[{'name':'downloads.example.invalid'}]}]) as request:
            with self.assertRaises(ValueError):p.publish()
            self.assertEqual(request.call_count,3)
