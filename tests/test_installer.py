import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='easycups test ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        env = patch.dict(os.environ, {'HOME':str(self.home), 'XDG_DATA_HOME':str(self.home/'dados')})
        env.start(); self.addCleanup(env.stop)
    def test_install_upgrade_and_uninstall(self):
        launcher = installer.install_files()
        self.assertTrue(launcher.is_file())
        desktop = installer.paths()[2].read_text()
        self.assertIn('Exec="', desktop)
        self.assertEqual(subprocess.check_output([str(launcher),'--version'],text=True).strip(), '1.2.1')
        installer.install_files()
        self.assertEqual(subprocess.check_output([str(launcher),'--version'],text=True).strip(), '1.2.1')
        uninstall = installer.paths()[0]/'uninstall.py'
        subprocess.run([sys.executable, str(uninstall), '--uninstall'], check=True, capture_output=True)
        self.assertFalse(launcher.exists())
        self.assertFalse(installer.paths()[0].exists())
    def test_copy_failure_preserves_previous_installation(self):
        launcher = installer.install_files(); previous = launcher.read_bytes()
        with patch.object(installer.shutil, 'copytree', side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError): installer.install_files()
        self.assertEqual(launcher.read_bytes(), previous)
    def test_failed_launcher_write_rolls_back(self):
        launcher = installer.install_files(); old = launcher.read_text()
        original = Path.write_text
        failed = False
        def fail_once(path, *args, **kwargs):
            nonlocal failed
            if path == launcher and not failed:
                failed = True; raise OSError('sem espaço')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'write_text', fail_once):
            with self.assertRaises(OSError): installer.install_files()
        self.assertEqual(launcher.read_text(), old)
        self.assertTrue((installer.paths()[0]/'easycups/__main__.py').exists())
    def test_relative_xdg_path_rejected(self):
        with patch.dict(os.environ, {'XDG_DATA_HOME':'relative'}):
            with self.assertRaises(ValueError): installer.paths()
    def test_symlink_target_rejected(self):
        target, *_ = installer.paths(); target.parent.mkdir(parents=True)
        elsewhere = self.home/'elsewhere'; elsewhere.mkdir(); target.symlink_to(elsewhere)
        with self.assertRaises(ValueError): installer.install_files()
        self.assertTrue(elsewhere.exists())
    def test_root_install_rejected(self):
        with patch.object(installer.os, 'geteuid', return_value=0):
            with self.assertRaises(ValueError): installer.install_files()
    def test_desktop_quote_percent_and_space(self):
        self.assertEqual(installer.desktop_quote('/home/A B/100%/x'), '"/home/A B/100%%/x"')
if __name__ == '__main__': unittest.main()
