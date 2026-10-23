import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class BootstrapTests(unittest.TestCase):
    def run_bootstrap(self, ready, answer='', sudo_status=0, check=False, manager='apt-get'):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); tools = base/'bin'; tools.mkdir(); log = base/'calls'
            def script(name, body):
                file = tools/name; file.write_text('#!/bin/sh\n'+body+'\n'); file.chmod(0o755)
            script('id', 'echo 1000')
            (tools/'dirname').symlink_to('/usr/bin/dirname')
            script(manager, 'exit 0')
            script('python3', 'if [ "$1" = -c ]; then exit "$READY_STATUS"; fi\nprintf "GUI:%s:%s\\n" "$PWD" "$*" >> "$CALL_LOG"')
            script('sudo', 'printf "PRIV:%s\\n" "$*" >> "$CALL_LOG"; exit "$SUDO_STATUS"')
            for cmd in ['lpstat', 'lpadmin', 'lpinfo', 'lp', 'cancel', 'pkexec']: script(cmd, 'exit 0')
            env = {**os.environ, 'PATH':str(tools), 'READY_STATUS':'0' if ready else '1', 'SUDO_STATUS':str(sudo_status), 'CALL_LOG':str(log), 'EASYCUPS_CHECK_ONLY':'1' if check else '0'}
            result = subprocess.run(['/bin/sh',str(ROOT/'packaging/bootstrap.sh')], input=answer,text=True,capture_output=True,env=env)
            return result, log.read_text() if log.exists() else ''
    def test_ready_goes_directly_to_wizard_in_project_directory(self):
        result, log = self.run_bootstrap(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('GUI:'+str(ROOT)+':install.py --gui', log)
        self.assertNotIn('PRIV:', log)
    def test_cancel_never_calls_privileged_command(self):
        result, log = self.run_bootstrap(False, 'n\n')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(log, '')
    def test_package_install_failure_stops(self):
        result, log = self.run_bootstrap(False, 's\n', sudo_status=23)
        self.assertEqual(result.returncode, 23)
        self.assertIn('apt-get install', log)
        self.assertNotIn('GUI:', log)
    def test_insufficient_library_versions_stop_before_gui(self):
        result, log = self.run_bootstrap(False, 's\n')
        self.assertEqual(result.returncode, 2)
        self.assertIn('GTK 4.10+', result.stderr)
        self.assertNotIn('GUI:', log)
    def test_check_mode_has_no_side_effect(self):
        result, log = self.run_bootstrap(False,check=True)
        self.assertEqual(result.returncode,3)
        self.assertEqual(log,'')
    def test_six_package_managers_detected(self):
        for manager in ['apt-get','dnf','zypper','pacman','apk','xbps-install']:
            with self.subTest(manager=manager):
                result, log = self.run_bootstrap(False, 's\n', sudo_status=23,manager=manager)
                self.assertEqual(result.returncode,23)
                self.assertIn('PRIV:-- '+manager,log)
                self.assertNotIn('GUI:',log)
if __name__ == '__main__': unittest.main()
