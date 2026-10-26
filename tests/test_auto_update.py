"""Real Ed25519 signatures; no network, system packages, or user application data."""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = next(ROOT.glob('*/auto_update.py'), ROOT/'tools/auto_update.py')
spec = importlib.util.spec_from_file_location('updater_under_test', MODULE)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class Updates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = tempfile.TemporaryDirectory()
        cls.key = Path(cls.keys.name)/'key.pem'
        subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(cls.key)],check=True,capture_output=True)
        cls.public = subprocess.run(['openssl','pkey','-in',str(cls.key),'-pubout'],check=True,capture_output=True,text=True).stdout

    @classmethod
    def tearDownClass(cls):
        cls.keys.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'XDG_DATA_HOME':self.tmp.name})
        self.env.start()
        self.uid = patch.object(u.os,'getuid',return_value=os.getuid() or 1000)
        self.uid.start()
        self.root = Path(self.tmp.name)
        self.config = dict(app='sampleapp',feed='https://updates.example.invalid/latest.json',public_key=self.public,enabled=True)

    def tearDown(self):
        self.uid.stop();self.env.stop();self.tmp.cleanup()

    def archive(self, members=None):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w:gz') as a:
            for name,body in (members or [('sampleapp/__init__.py',b'__version__="2.0.0"'),('sampleapp/__main__.py',b'print("synthetic")')]):
                item=tarfile.TarInfo(name);item.size=len(body);a.addfile(item,io.BytesIO(body))
        return buffer.getvalue()

    def signed(self, blob, **changes):
        d=dict(schema=1,app='sampleapp',channel='stable',version='2.0.0',python_min=[3,10],url='https://updates.example.invalid/app.tar.gz',size=len(blob),sha256=hashlib.sha256(blob).hexdigest())
        d.update(changes);body=json.dumps(d).encode()
        file=self.root/'manifest';file.write_bytes(body)
        signature=subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(self.key),'-rawin','-in',str(file)],check=True,capture_output=True).stdout
        return body,base64.b64encode(signature)

    def fetch(self, blob, signed):
        def fetch(url, limit):
            return signed[1] if url.endswith('.sig') else signed[0] if url.endswith('.json') else blob
        return fetch

    def test_signed_update_preserves_user_files_and_waits_for_restart(self):
        # Simulate an ordinary user even in CI containers.
        with patch.object(u,'state_root',side_effect=lambda app:self.root):
            personal=self.root/'document.txt';personal.write_text('synthetic user document')
            blob=self.archive();signed=self.signed(blob)
            self.assertIn('próxima',u.stage(self.config,'1.0.0',self.fetch(blob,signed)))
            self.assertEqual(u.selected(self.config,'1.0.0')['version'],'2.0.0')
            self.assertEqual(personal.read_text(),'synthetic user document')
            self.assertIsNone(u.selected(self.config,'3.0.0'))
            self.assertIn('já usa',u.stage(self.config,'1.0.0',self.fetch(blob,signed)))

    def test_modified_signature_and_payload_rejected(self):
        blob=self.archive();body,sig=self.signed(blob)
        for bad,s in ((body+b' ',sig),(body,base64.b64encode(b'x'*64)),(body,b'invalid')):
            with self.assertRaises(ValueError):
                u.manifest(bad,s,self.config)

    def test_wrong_app_channel_url_size_version_or_python_rejected(self):
        blob=self.archive()
        for values in (dict(app='other'),dict(channel='preview'),dict(url='http://updates.example.invalid/x'),dict(url='https://other.invalid/x'),dict(size=-1),dict(version='2.0.0rc1'),dict(python_min=[4,0])):
            with self.subTest(values=values):
                body,sig=self.signed(blob,**values)
                with self.assertRaises(ValueError):u.manifest(body,sig,self.config)

    def test_download_failure_or_corruption_never_replaces_active(self):
        with patch.object(u,'state_root',side_effect=lambda app:self.root):
            blob=self.archive();signed=self.signed(blob);fetch=self.fetch(blob,signed)
            u.stage(self.config,'1.0.0',fetch);before=(self.root/'active.json').read_bytes()
            newer=self.signed(blob,version='3.0.0')
            with self.assertRaises(ValueError):u.stage(self.config,'1.0.0',self.fetch(blob+b'bad',newer))
            self.assertEqual((self.root/'active.json').read_bytes(),before)
            def offline(*_):raise OSError('offline')
            with self.assertRaises(OSError):u.stage(self.config,'1.0.0',offline)
            self.assertEqual((self.root/'active.json').read_bytes(),before)

    def test_archive_traversal_duplicate_foreign_and_symlink_rejected(self):
        for members in ([('../escape',b'x')],[('/escape',b'x')],[('other/__main__.py',b'x')],[('sampleapp/a',b'x'),('sampleapp/a',b'y')]):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises((ValueError,OSError)):u.unpack(self.archive(members),Path(tmp),'sampleapp')
        b=io.BytesIO()
        with tarfile.open(fileobj=b,mode='w:gz') as a:
            item=tarfile.TarInfo('sampleapp/link');item.type=tarfile.SYMTYPE;item.linkname='/tmp/out';a.addfile(item)
        with self.assertRaises(ValueError):u.unpack(b.getvalue(),self.root,'sampleapp')

    def test_incomplete_and_invalid_python_rejected(self):
        for members in ([('sampleapp/a',b'x')],[('sampleapp/__init__.py',b''),('sampleapp/__main__.py',b'not valid python!')]):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises((ValueError,SyntaxError)):u.unpack(self.archive(members),Path(tmp),'sampleapp')

    def test_root_and_disabled_channel(self):
        with patch.object(u.os,'getuid',return_value=0):
            with self.assertRaises(ValueError):u.stage(self.config,'1.0.0')
        self.assertIn('não ativado',u.stage(dict(self.config,enabled=False),'1.0.0'))

    def test_https_rejects_credentials_fragments_and_cross_origin_redirect(self):
        for url in ('http://example.invalid','https://user:pass@example.invalid','https://example.invalid/#token'):
            with self.assertRaises(ValueError):u.https_url(url)
        import urllib.request
        with self.assertRaises(ValueError):u.SameOriginRedirect().redirect_request(urllib.request.Request('https://example.invalid/a'),None,302,'',{},'https://other.invalid/b')

    def test_local_tampering_detected_and_downgrade_ignored(self):
        with patch.object(u,'state_root',side_effect=lambda app:self.root):
            blob=self.archive();signed=self.signed(blob);u.stage(self.config,'1.0.0',self.fetch(blob,signed))
            old=self.signed(blob,version='1.5.0')
            self.assertIn('já usa',u.stage(self.config,'1.0.0',self.fetch(blob,old)))
            archive=next(self.root.glob('*.tar.gz'));archive.write_bytes(blob+b'x')
            with self.assertRaises(ValueError):u.selected(self.config,'1.0.0')

    def test_real_child_launch_and_failed_update_falls_back(self):
        import sys
        with patch.object(u,'state_root',side_effect=lambda app:self.root):
            package=self.root/'bundled';package.mkdir()
            config=dict(self.config,bundled_version='1.0.0')
            (package/'update-channel.json').write_text(json.dumps(config))
            for body, expected in ((b'import sys;assert len(sys.argv)==1;print("UPDATED_CHILD")','UPDATED_CHILD'),(b'raise RuntimeError("synthetic failure")','BUNDLED_FALLBACK')):
                blob=self.archive([('sampleapp/__init__.py',b''),('sampleapp/__main__.py',body)])
                signed=self.signed(blob,version='2.0.0' if expected=='UPDATED_CHILD' else '3.0.0')
                u.stage(self.config,'1.0.0',self.fetch(blob,signed))
                script='import importlib.util,sys;from pathlib import Path;spec=importlib.util.spec_from_file_location("u",sys.argv[1]);u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u);root=Path(sys.argv[2]);package=Path(sys.argv[3]);u.os.getuid=lambda:1000;u.state_root=lambda app:root;sys.argv=["sampleapp"];u.bootstrap(package);print("BUNDLED_FALLBACK")'
                result=subprocess.run([sys.executable,'-c',script,str(MODULE),str(self.root),str(package)],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(expected,result.stdout)
            self.assertIn('falhou',u.stage(self.config,'1.0.0',self.fetch(blob,signed)))
