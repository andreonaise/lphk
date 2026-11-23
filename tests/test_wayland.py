import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from input_backend import select_backend
from system_apis.input_wayland import KEYS, WaylandInput, sp


class SelectionTests(unittest.TestCase):
    def test_windows_ignores_linux_environment(self):
        self.assertEqual(select_backend('win32', {'WAYLAND_DISPLAY': 'wayland-0'}), 'windows')

    def test_wayland_selected_even_with_xwayland_display(self):
        self.assertEqual(select_backend('linux', {'XDG_SESSION_TYPE': 'wayland', 'DISPLAY': ':0'}), 'wayland')
        self.assertEqual(select_backend('linux', {'WAYLAND_DISPLAY': 'wayland-1'}), 'wayland')
        self.assertEqual(select_backend('linux', {'DISPLAY': ':0'}), 'x11')

    def test_overrides_and_invalid_config(self):
        self.assertEqual(select_backend('linux', {'WAYLAND_DISPLAY': 'wayland-1', 'LPHK_INPUT_BACKEND': 'x11'}), 'x11')
        with self.assertRaises(RuntimeError):
            select_backend('linux', {'LPHK_INPUT_BACKEND': 'windows'})
        with self.assertRaises(RuntimeError):
            select_backend('win32', {'LPHK_INPUT_BACKEND': 'wayland'})
        with self.assertRaises(RuntimeError):
            select_backend('linux', {'LPHK_INPUT_BACKEND': 'bogus'})


class WaylandTests(unittest.TestCase):
    def setUp(self):
        self.backend = WaylandInput()

    def test_common_keys_use_evdev_not_x_or_windows_codes(self):
        self.assertEqual(sp('ctrl'), 29)
        self.assertEqual(sp('win'), 125)
        self.assertEqual(sp('vol_up'), 115)
        self.assertEqual(sp('num1'), 79)
        self.assertEqual(sp('f24'), 194)
        self.assertEqual(sp('z'), 44)
        self.assertIsNone(sp('invalid'))

    def test_held_keys_survive_between_cli_calls(self):
        with patch.object(self.backend, 'run') as run:
            self.backend.press(sp('ctrl'))
            self.backend.press(sp('c'))
            self.assertEqual(self.backend.held_keys, {29, 46})
            self.backend.release(sp('c'))
            self.assertEqual(self.backend.held_keys, {29})
            self.backend.release_all()
            self.assertEqual(self.backend.held_keys, set())
            self.assertEqual(run.call_args_list[0].args, ('ydotool', 'key', '--key-delay', '0', '29:1'))
            self.assertEqual(run.call_args_list[-1].args[-1], '29:0')

    def test_unicode_and_shell_metacharacters_sent_literally_on_stdin(self):
        text = '-M ctrl; $(touch /tmp/oops) "Grüße"\nこんにちは'
        with patch('system_apis.input_wayland.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            self.backend.write(text)
            args, kwargs = run.call_args
            self.assertEqual(args[0], ['wtype', '-'])
            self.assertEqual(kwargs['input'], text)
            self.assertEqual(kwargs['encoding'], 'utf-8')
            self.assertNotIn('shell', kwargs)
            self.assertGreaterEqual(kwargs['timeout'], 10)

    def test_command_failure_has_actionable_error(self):
        with patch('system_apis.input_wayland.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'socket unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'socket unavailable'):
                self.backend.press(29)
        self.assertIn(29, self.backend.held_keys)

    def test_missing_command_and_timeout(self):
        for failure in (FileNotFoundError(), subprocess.TimeoutExpired('ydotool', 5)):
            with self.subTest(failure=type(failure).__name__):
                with patch('system_apis.input_wayland.subprocess.run', side_effect=failure):
                    with self.assertRaises(RuntimeError):
                        self.backend.run('ydotool', 'debug')

    def test_release_all_attempts_every_key_and_mouse_after_failure(self):
        self.backend.held_keys = {29, 46}
        self.backend.held_buttons = {'right'}
        with patch.object(self.backend, 'run', side_effect=[RuntimeError('gone'), '', '']) as run:
            with self.assertRaisesRegex(RuntimeError, 'gone'):
                self.backend.release_all()
            self.assertEqual(run.call_count, 3)
            self.assertEqual(len(self.backend.held_keys), 1)
            self.assertEqual(self.backend.held_buttons, set())

    def test_mouse_button_masks(self):
        with patch.object(self.backend, 'run') as run:
            self.backend.button('right', True)
            self.assertEqual(run.call_args.args[-1], '0x41')
            self.assertEqual(self.backend.held_buttons, {'right'})
            self.backend.button('right', False)
            self.assertEqual(run.call_args.args[-1], '0x81')
            self.backend.click('middle', 2)
            self.assertEqual(run.call_count, 6)
            self.assertEqual(self.backend.held_buttons, set())

    def test_scroll_preserves_fractional_steps_and_direction(self):
        with patch.object(self.backend, 'run') as run:
            self.backend.scroll(0.5, -0.5)
            run.assert_not_called()
            self.backend.scroll(0.5, -0.5)
            run.assert_called_once_with('ydotool', 'mousemove', '--wheel', '--', 1, -1)

    def test_cursor_uses_mango_global_position(self):
        with patch.object(self.backend, 'run', return_value=json.dumps({'x': -850.2, 'y': 30.8, 'monitor': 'DP-1'})) as run:
            self.assertEqual(self.backend.get_pos(), (-850, 31))
            run.assert_called_once_with('mmsg', 'get', 'cursorpos')

    def test_unsupported_or_malformed_mango_response(self):
        for text in ('{"error":"unknown command"}', 'not json', '[]', '{"x":NaN,"y":1}'):
            with self.subTest(text=text), patch.object(self.backend, 'run', return_value=text):
                with self.assertRaisesRegex(RuntimeError, 'MangoWM'):
                    self.backend.get_pos()

    def test_set_position_uses_feedback_and_handles_scaled_movement(self):
        position = [20, 30]

        def move(x, y):
            position[0] += x * 2
            position[1] += y

        with patch.object(self.backend, 'get_pos', side_effect=lambda: tuple(position)), \
             patch.object(self.backend, 'move', side_effect=move) as movement, \
             patch('system_apis.input_wayland.time.sleep'):
            self.backend.set_pos(-100, 200)
            self.assertEqual(position, [-100, 200])
            self.assertLessEqual(movement.call_count, 3)

    def test_set_position_reports_confinement(self):
        with patch.object(self.backend, 'get_pos', return_value=(0, 0)), \
             patch.object(self.backend, 'move'), patch('system_apis.input_wayland.time.sleep'):
            with self.assertRaisesRegex(RuntimeError, 'confinement'):
                self.backend.set_pos(100, 100)

    def test_health_check_does_not_inject_input(self):
        def run(program, *arguments, **kwargs):
            if program == 'mmsg':
                return '{"x":1,"y":2}'
            self.assertEqual((program, *arguments), ('ydotool', 'debug'))
            return ''

        with patch('system_apis.input_wayland.shutil.which', side_effect=lambda name: '/usr/bin/' + name), \
             patch.object(self.backend, 'run', side_effect=run):
            self.assertIn('ready', self.backend.check())

    def test_health_check_lists_missing_dependencies(self):
        with patch('system_apis.input_wayland.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'ydotool, wtype'):
                self.backend.check()

    def test_existing_daemon_socket_is_preserved(self):
        with patch.dict('os.environ', {'YDOTOOL_SOCKET': '/my/socket'}):
            self.assertEqual(self.backend.environment()['YDOTOOL_SOCKET'], '/my/socket')

    def test_wayland_import_path_does_not_load_x11_input_libraries(self):
        backend_module = types.ModuleType('input_backend')
        backend_module.BACKEND = 'wayland'
        with patch.dict(sys.modules, {'input_backend': backend_module, 'pynput': None, 'pyautogui': None}):
            spec = importlib.util.spec_from_file_location('wayland_mouse_test', ROOT / 'ms.py')
            mouse = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mouse)
            with patch.dict(sys.modules, {'ms': mouse}):
                spec = importlib.util.spec_from_file_location('wayland_keyboard_test', ROOT / 'kb.py')
                keyboard = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(keyboard)
            self.assertEqual(keyboard.sp('win'), 125)
            with patch.object(mouse.controller, 'run') as run:
                keyboard.press(keyboard.sp('a'))
                keyboard.release_all()
                mouse.scroll(0, 1)
                self.assertEqual(run.call_args.args[:3], ('ydotool', 'mousemove', '--wheel'))


if __name__ == '__main__':
    unittest.main()
