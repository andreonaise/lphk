import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime_support import prepare_user_data, restart_command, sound_path


class PortabilityTests(unittest.TestCase):
    def test_restart_keeps_spaces_and_arguments(self):
        executable = '/folder with spaces/python'
        argv = ['/app folder/LPHK.py', '--debug']
        self.assertEqual(restart_command(executable, argv), [executable, *argv])
        self.assertEqual(restart_command(executable, argv, True), [executable, '--debug'])

    def test_data_initialization_preserves_user_examples(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = base / 'resources/user_layouts/examples'
            source.mkdir(parents=True)
            (source / 'demo.lpl').write_text('original')
            target = base / 'user data'
            prepare_user_data(target, base / 'resources')
            example = target / 'user_layouts/examples/demo.lpl'
            self.assertEqual(example.read_text(), 'original')
            example.write_text('edited')
            prepare_user_data(target, base / 'resources')
            self.assertEqual(example.read_text(), 'edited')
            self.assertTrue((target / 'user_sounds').is_dir())
            self.assertTrue((target / 'user_scripts').is_dir())

    def test_sound_layouts_accept_both_path_separators(self):
        expected = str(Path('data folder') / 'user_sounds/examples/demo.wav')
        self.assertEqual(sound_path('data folder', 'examples/demo.wav'), expected)
        self.assertEqual(sound_path('data folder', 'examples\\demo.wav'), expected)

    def test_linux_key_names_and_backend_dispatch(self):
        # Exercise Linux mappings on either host without generating real input.
        fake = types.ModuleType('pynput.keyboard')
        names = ['cmd', 'cmd_r', 'menu', 'alt_l', 'alt_r', 'ctrl_l', 'shift_r',
                 'media_volume_up', 'media_volume_down', 'media_volume_mute',
                 'media_play_pause', 'media_previous', 'media_next']
        fake.Key = {name: object() for name in names}
        fake.KeyCode = MagicMock()
        fake.Controller = MagicMock()
        with patch.dict(sys.modules, {'pynput.keyboard': fake}):
            spec = importlib.util.spec_from_file_location('linux_keys_test', ROOT / 'system_apis/keyboard_unix.py')
            backend = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(backend)
        for alias, name in backend.ALIASES.items():
            self.assertIs(backend.sp(alias), fake.Key[name])
        for number in range(10):
            backend.sp('num' + str(number))
            fake.KeyCode.from_vk.assert_called_with(0xFFB0 + number)
        self.assertIsNone(backend.sp('unknown_key'))
        backend.sp('a')
        fake.KeyCode.from_char.assert_called_with('a')
        backend.press('key')
        backend.release('key')
        backend.write('Grüße')
        fake.Controller.return_value.press.assert_called_once_with('key')
        fake.Controller.return_value.release.assert_called_once_with('key')
        fake.Controller.return_value.type.assert_called_once_with('Grüße')


if __name__ == '__main__':
    unittest.main()
