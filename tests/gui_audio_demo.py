"""Exercise demo-pad interaction and the soundtrack editor with real dummy audio."""
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tkinter as tk
import window
import files
import scripts
import sound
import lp_colors
import lp_events
import ui_theme
from runtime_support import prepare_user_data


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


root = tk.Tk()
root.after(20000, root.destroy)
errors = []
root.report_callback_exception = lambda *error: errors.append(error)
ui_theme.apply(root)
window.root = root
window.root_destroyed = False
window.PATH = str(ROOT)
window.VERSION = (ROOT / 'VERSION').read_text().strip()
window.MAIN_ICON = None
window.lp_connected = False
window.demo_mode = False


def wait_for(predicate, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        root.update()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError('Timed out waiting for GUI/audio state')


try:
    with tempfile.TemporaryDirectory() as directory:
        window.USER_PATH = directory
        prepare_user_data(directory, ROOT)
        files.init(directory)
        sound.init(directory)
        app = window.Main_Window(root)
        window.app = app
        app.load_soundtrack_demo()
        assert window.demo_mode and window.lp_connected and app.run_mode
        assert lp_events.timer is None
        assert scripts.validate_script(scripts.text[0][1]) is True
        scripts.bind(0, 1, 'SOUND_TRACK examples/demo_track.wav 70 80 100', [70, 120, 90])

        def press():
            app.click(SimpleNamespace(x=25, y=75))
            app.release_play_pad()

        press()
        wait_for(lambda: sound.snapshot().get((0, 1), {}).get('state') == 'playing')
        wait_for(lambda: scripts.threads[0][1] is not None and not scripts.threads[0][1].is_alive())
        clip = sound.player.tracks[0, 1].sound
        press()
        wait_for(lambda: sound.snapshot()[0, 1]['state'] == 'paused')
        paused_at = sound.snapshot()[0, 1]['position']
        time.sleep(0.1)
        assert sound.snapshot()[0, 1]['position'] == paused_at
        app.audio_tick()
        assert app.c.itemcget(app.grid_rects[0][1], 'fill') == '#cd9b48'
        assert window.lp_object.leds[0, 1] == ('pulse', 9)
        press()
        wait_for(lambda: sound.snapshot()[0, 1]['state'] == 'playing')
        assert sound.snapshot()[0, 1]['position'] >= paused_at
        assert sound.player.tracks[0, 1].sound is clip
        sound.stop_faded()
        wait_for(lambda: sound.snapshot()[0, 1]['state'] == 'stopped')
        app.audio_tick()
        assert app.c.itemcget(app.grid_rects[0][1], 'fill') == '#46785a'
        app.transport_toggle.invoke()
        wait_for(lambda: sound.snapshot()[0, 1]['state'] in ('playing', 'fading_in'))
        app.transport_toggle.invoke()
        wait_for(lambda: all(state['state'] == 'paused' for state in sound.snapshot().values()))
        app.transport_toggle.invoke()
        wait_for(lambda: sound.snapshot()[0, 1]['state'] in ('playing', 'fading_in'))
        sound.stop()
        app.set_mode('edit')
        assert not app.run_mode

        # Exercise nested Soundtrack... dialog, file import, custom timings and Bind.
        source = Path(directory) / 'imported track.wav'
        with wave.open(str(source), 'wb') as stream:
            stream.setparams((1, 2, 22050, 0, 'NONE', ''))
            stream.writeframes(b'\x00\x00' * 22050)

        def configure_dialog():
            dialog = next(widget for widget in descendants(app) if isinstance(widget, tk.Toplevel) and widget.title() == 'Soundtrack')
            widgets = list(descendants(dialog))
            browse = next(widget for widget in widgets if isinstance(widget, tk.Button) and widget.cget('text') == 'Browse')
            with patch('tkinter.filedialog.askopenfilename', return_value=str(source)):
                browse.invoke()
            spinboxes = [widget for widget in widgets if isinstance(widget, tk.Spinbox)]
            for widget, value in zip(spinboxes, ('70', '0.125', '0.25', '0.9')):
                widget.delete(0, 'end')
                widget.insert(0, value)
            next(widget for widget in widgets if isinstance(widget, tk.Button) and widget.cget('text') == 'Apply to script').invoke()

        def configure_editor():
            editor = next(widget for widget in app.winfo_children() if isinstance(widget, tk.Toplevel))
            widgets = list(descendants(editor))
            root.after(80, configure_dialog)
            next(widget for widget in widgets if isinstance(widget, tk.Button) and widget.cget('text') == 'Soundtrack...').invoke()
            next(widget for widget in widgets if isinstance(widget, tk.Button) and widget.cget('text').startswith('Bind Button')).invoke()

        root.after(80, configure_editor)
        app.script_entry_window(4, 2)
        import track_commands
        assert track_commands.parse(scripts.text[4][2]) == ('imported track.wav', 70, 125, 900, 250)
        layout = str(Path(directory) / 'user_layouts/audio.lpl')
        files.save_lp_to_layout(layout)
        files.load_layout_to_lp(layout, popups=False)
        assert track_commands.parse(scripts.text[4][2])[2:] == (125, 900, 250)
        assert not errors, errors
        files.layout_changed_since_load = False
        app.disconnect_lp()
        assert not window.demo_mode
        print('Demo/audio GUI checks passed: play-pause-resume, fades, pad/LED state, import, soundtrack editor, saved settings')
finally:
    sound.shutdown()
    lp_events.stop()
    root.destroy()
