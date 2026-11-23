from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bundled_tools
import mango_ipc
import logger


class PackagingTests(unittest.TestCase):
    def test_windowed_logging_has_no_console_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'LPHK.log'
            with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
                logger.start(path)
                print('Grüße / 日本語')
                logger.stop()
                self.assertIsNone(sys.stdout)
            self.assertIn('Grüße / 日本語', path.read_text(encoding='utf-8'))

    def test_bundled_tools_are_found_without_path(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'tools/wtype'
            target.parent.mkdir()
            target.write_text('fixture')
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', directory, create=True), patch('shutil.which', return_value=None):
                self.assertEqual(bundled_tools.locate('wtype'), str(target))
                self.assertIsNone(bundled_tools.locate('missing'))

    def test_external_tools_do_not_inherit_bundled_library_path(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', '/app/_internal', create=True):
            environment = {'LD_LIBRARY_PATH': '/app/_internal', 'LD_LIBRARY_PATH_ORIG': '/original'}
            result = bundled_tools.external_environment(environment, '/usr/bin/xdg-open')
            self.assertEqual(result['LD_LIBRARY_PATH'], '/original')
            result = bundled_tools.external_environment(environment, '/app/_internal/tools/wtype')
            self.assertEqual(result['LD_LIBRARY_PATH'], '/app/_internal')

    def test_mango_ipc_reads_fragmented_json_without_mmsg(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.recv.side_effect = [b'{"x":-10,', b'"y":20}\n']
        with patch.dict('os.environ', {'MANGO_INSTANCE_SIGNATURE': '/example/socket'}), patch('mango_ipc.socket.socket', return_value=connection), patch('mango_ipc.socket.AF_UNIX', 1, create=True):
            self.assertEqual(mango_ipc.request('get cursorpos'), '{"x":-10,"y":20}')
            connection.sendall.assert_called_once_with(b'get cursorpos\n')

    def test_mango_ipc_rejects_server_errors(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.recv.return_value = b'{"error":"unknown command"}\n'
        with patch.dict('os.environ', {'MANGO_INSTANCE_SIGNATURE': '/example/socket'}), patch('mango_ipc.socket.socket', return_value=connection), patch('mango_ipc.socket.AF_UNIX', 1, create=True):
            with self.assertRaisesRegex(RuntimeError, 'unknown command'):
                mango_ipc.request('get cursorpos')


if __name__ == '__main__':
    unittest.main()
