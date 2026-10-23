import subprocess, unittest
from unittest.mock import patch
from easycups.core import valid_uri, uniq, run, service_command

class CoreTests(unittest.TestCase):
    def test_valid_addresses(self):
        for uri in ['ipp://192.0.2.1/ipp/print', 'ipps://printer.local/ipp/print', 'usb://Vendor/Model', 'socket://192.0.2.1:9100']:
            self.assertTrue(valid_uri(uri))
    def test_reject_injected_or_invalid_addresses(self):
        for uri in ['-x printer', 'ipp://', 'ipp://a\n', 'ipp://a b', 'file:///etc/passwd', 'ipp://a\x00b', 'ipp://a"b']:
            self.assertFalse(valid_uri(uri), repr(uri))
    def test_name_collision(self):
        self.assertEqual(uniq('Printer', {'Printer','Printer_2'}), 'Printer_3')
    @patch('easycups.core.subprocess.run', side_effect=FileNotFoundError(2, 'absent', 'lpstat'))
    def test_missing_command(self, mock):
        self.assertFalse(run(['lpstat'])[0])
    @patch('easycups.core.subprocess.run', side_effect=subprocess.TimeoutExpired('lpstat', 1))
    def test_timeout(self, mock):
        self.assertFalse(run(['lpstat'])[0])
    @patch('easycups.core.subprocess.run')
    def test_locale_and_argument_boundaries(self, mock):
        mock.return_value = subprocess.CompletedProcess([], 0, 'ok', '')
        self.assertTrue(run(['lpadmin','-p','a;touch /tmp/unsafe'])[0])
        self.assertEqual(mock.call_args.args[0], ['env','LC_ALL=C','lpadmin','-p','a;touch /tmp/unsafe'])
    def test_service_rejects_shell(self):
        with self.assertRaises(ValueError): service_command('start;echo bad')
    @patch('easycups.core.os.path.isdir', return_value=True)
    @patch('easycups.core.shutil.which', return_value='/usr/bin/systemctl')
    def test_systemd_enable(self, *_):
        self.assertEqual(service_command('enable'), ['systemctl','enable','--now','cups'])
    @patch('easycups.core.os.path.isdir', return_value=False)
    @patch('easycups.core.shutil.which', side_effect=lambda k: '/sbin/'+k if k == 'rc-service' else None)
    def test_openrc(self, *_):
        self.assertEqual(service_command('start'), ['rc-service','cups','start'])
if __name__ == '__main__': unittest.main()
