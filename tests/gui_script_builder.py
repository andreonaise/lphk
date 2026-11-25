"""Exercise visual command forms and sequence editing without generating input."""
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import script_builder
import script_builder_ui
import ui_theme
import scripts
from command_guide import COMMANDS

root = tk.Tk()
ui_theme.apply(root)
errors = []
root.report_callback_exception = lambda *e: errors.append(e)
root.after(15000, root.destroy)
editor = tk.Text(root)
editor.pack()
original = '- keep this comment\n\nCUSTOM_LEGACY_LINE argument\nTAP a\n'
editor.insert('1.0', original)
try:
    # Keep engine imports in the GUI check: Linux runs this under Xvfb.
    # The headless unit suite uses the pure form model instead.
    with patch('scripts.os.path.isfile', return_value=True), patch('scripts.sound.is_valid', return_value=True), patch('scripts.files.load_layout', return_value={}), patch('scripts.files.LAYOUT_PATH', '/layouts'), patch('scripts.sound.full_name', return_value='/audio/example.wav'):
        for command, entry in COMMANDS.items():
            line = next(line for line in entry[3].splitlines() if line.split()[0] == command)
            _, values = script_builder.parse(line)
            result = script_builder.build(command, values)
            if command.endswith(('GOTO_LABEL', 'REPEAT_LABEL')):
                result = 'LABEL start\n' + result
            assert scripts.validate_script(result) is True, command
    with tempfile.TemporaryDirectory() as folder:
        builder = script_builder_ui.open_builder(root, editor, folder)
        root.update()
        assert builder.lines == original.split('\n')
        # Cancel leaves the original text byte for byte unchanged.
        builder.insert('DELAY 2')
        builder.close()
        assert editor.get('1.0', 'end-1c') == original
        builder = script_builder_ui.open_builder(root, editor, folder)
        builder.insert('TAP space')
        form = builder.edit()
        root.update()
        form.variables['key'].set('enter')
        form.variables['count'].set('2')
        form.submit()
        assert builder.lines[-1] == 'TAP enter 2'
        builder.duplicate()
        builder.move(-1)
        builder.remove()
        form = builder.add()
        form.selector.current(list(script_builder.FORMS).index('SOUND_PAUSE'))
        form.render()
        form.variables['fade'].set('1.25')
        form.submit()
        assert builder.lines[-1] == 'SOUND_PAUSE 1250'
        assert builder.apply()
        assert editor.get('1.0', 'end-1c').startswith(original)
        assert 'TAP enter 2' in editor.get('1.0', 'end-1c')
        assert not errors, errors
        print('Visual builder GUI passed: lossless import/cancel, edit forms, reorder, duplicate, remove, fade conversion, apply')
finally:
    root.destroy()
