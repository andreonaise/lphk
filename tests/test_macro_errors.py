import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


class MacroErrorTests(unittest.TestCase):
    def load_scripts(self):
        dependencies = {name: types.ModuleType(name) for name in
                        ('lp_events', 'lp_colors', 'kb', 'sound', 'ms', 'files')}
        dependencies['kb'].release_all = MagicMock()
        with patch.dict(sys.modules, dependencies):
            spec = importlib.util.spec_from_file_location('scripts_error_test', ROOT / 'scripts.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module, dependencies['kb']

    def test_input_failure_cleans_up_and_unblocks_serial_queue(self):
        scripts, keyboard = self.load_scripts()
        scripts.running = True
        with patch.object(scripts, '_run_script', side_effect=RuntimeError('daemon unavailable')):
            scripts.run_script('PRESS ctrl\nTAP c\nRELEASE ctrl', 0, 0)
        keyboard.release_all.assert_called_once()
        self.assertFalse(scripts.running)

    def test_async_failure_keeps_existing_serial_job_running(self):
        scripts, keyboard = self.load_scripts()
        scripts.running = True
        with patch.object(scripts, '_run_script', side_effect=RuntimeError('daemon unavailable')):
            scripts.run_script('- comment\n@ASYNC\nSTRING Hello', 0, 0)
        keyboard.release_all.assert_called_once()
        self.assertTrue(scripts.running)


if __name__ == '__main__':
    unittest.main()
