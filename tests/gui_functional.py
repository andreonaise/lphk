"""Exercise real GUI controls with a fake Launchpad; never generate OS input."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tkinter as tk
import window
import files
import scripts
import lp_colors
import ui_theme


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


errors = []
root = tk.Tk()
root.after(15000, root.destroy)
root.report_callback_exception = lambda *error: errors.append(error)
ui_theme.apply(root)
window.root = root
window.PATH = window.PROG_PATH = str(ROOT)
window.VERSION = (ROOT / 'VERSION').read_text().strip()
window.PLATFORM = 'windows' if sys.platform == 'win32' else 'linux'
window.MAIN_ICON = None
window.lp_mode = 'Mk2'
window.lp_connected = True
lp_colors.lp_object = MagicMock()

try:
    with tempfile.TemporaryDirectory() as directory:
        window.USER_PATH = directory
        for name in ('user_layouts', 'user_scripts', 'user_sounds'):
            (Path(directory) / name).mkdir()
        files.init(directory)
        app = window.Main_Window(root)
        window.app = app
        app.enable_menu('Layout')
        app.draw_canvas()
        root.update()
        assert app.c.cget('background') == ui_theme.PANEL
        assert app.grid_drawn
        assert len([item for row in app.grid_rects for item in row if item is not None]) == 81
        assert all(button.cget('state') == 'normal' for button in app.layout_buttons)

        def click(x, y):
            app.click(SimpleNamespace(x=(25 + x * 50) * app.canvas_scale[0], y=(25 + y * 50) * app.canvas_scale[1]))

        scripts.bind(0, 1, 'TAP a', [45, 95, 145])
        app.set_mode('copy')
        click(0, 1)
        click(1, 1)
        assert scripts.text[0][1] == scripts.text[1][1] == 'TAP a'
        app.set_mode('move')
        click(1, 1)
        click(2, 1)
        assert scripts.text[1][1] == '' and scripts.text[2][1] == 'TAP a'
        scripts.bind(2, 1, 'TAP b', [70, 80, 90])
        app.set_mode('swap')
        click(0, 1)
        click(2, 1)
        assert scripts.text[0][1] == 'TAP b' and scripts.text[2][1] == 'TAP a'
        assert lp_colors.curr_colors[0][1] == [70, 80, 90]
        app.set_mode('edit')
        click(8, 0)
        assert app.button_mode == 'move'  # Original corner mode control still works.
        app.mode_buttons['edit'].invoke()
        assert app.button_mode == 'edit'

        def edit_and_bind():
            editor = next(widget for widget in app.winfo_children() if isinstance(widget, tk.Toplevel))
            widgets = list(descendants(editor))
            text = next(widget for widget in widgets if isinstance(widget, tk.Text))
            text.delete('1.0', 'end')
            text.insert('1.0', 'PRESS ctrl\nTAP c\nRELEASE ctrl')
            path = str(Path(directory) / 'copy.lps')
            with patch('tkinter.filedialog.asksaveasfilename', return_value=path):
                app.export_script(text, editor)
            text.delete('1.0', 'end')
            with patch('tkinter.filedialog.askopenfilename', return_value=path):
                app.import_script(text, editor)
            assert text.get('1.0', 'end').strip().startswith('PRESS ctrl')
            colour = next(widget for widget in widgets if isinstance(widget, tk.Button) and widget.cget('text') == 'Select Color')
            with patch('tkcolorpicker.askcolor', return_value=((32, 64, 128), '#204080')):
                colour.invoke()
            save = next(widget for widget in widgets if isinstance(widget, tk.Button) and widget.cget('text').startswith('Bind Button'))
            save.invoke()

        root.after(150, edit_and_bind)
        app.script_entry_window(3, 2)
        assert scripts.text[3][2] == 'PRESS ctrl\nTAP c\nRELEASE ctrl'
        assert lp_colors.curr_colors[3][2] == [32, 64, 128]
        layout = str(Path(directory) / 'user_layouts/test.lpl')
        files.save_lp_to_layout(layout)
        scripts.unbind(3, 2)
        files.load_layout_to_lp(layout, popups=False)
        assert scripts.text[3][2].startswith('PRESS ctrl')
        assert app.layout_name.cget('text') == 'test.lpl'
        app.show_help('Help', 'README.md')
        for child in app.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
        assert not errors, errors
        files.layout_changed_since_load = False
        window.lp_connected = False
        app.disconnect_lp()
        assert not app.grid_drawn
        assert all(button.cget('state') == 'disabled' for button in app.layout_buttons)
        print('GUI checks passed: modes, original corner control, editor, colour, import/export, layout round-trip, help, disconnect')
finally:
    root.destroy()
