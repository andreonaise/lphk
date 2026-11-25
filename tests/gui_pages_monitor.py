"""Real GUI checks for page audio isolation, seeking, monitor, and guide."""
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tkinter as tk
import window
import files
import sound
import scripts
import page_state
import ui_theme
from runtime_support import prepare_user_data


root = tk.Tk()
root.after(20000, root.destroy)
errors = []
root.report_callback_exception = lambda *error: errors.append(error)
ui_theme.apply(root)
window.root, window.root_destroyed = root, False
window.PATH, window.MAIN_ICON = str(ROOT), None
window.VERSION = (ROOT / 'VERSION').read_text().strip()
window.lp_connected = window.demo_mode = False


def wait_for(predicate):
    end = time.monotonic() + 3
    while time.monotonic() < end:
        root.update()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError('GUI condition did not complete')


try:
    with tempfile.TemporaryDirectory(dir=ROOT.parent) as folder:
        window.USER_PATH = folder
        prepare_user_data(folder, ROOT)
        files.init(folder)
        sound.init(folder)
        app = window.Main_Window(root)
        window.app = app
        app.connect_dummy()
        first = page_state.book.current['id']
        sound.toggle_track((0, 1), 'examples/demo_track.wav', 80, 0, 0)
        original = sound.pad_key((0, 1))
        app.open_monitor()
        root.update()
        monitor = app.monitor
        monitor.selected = original
        monitor.step.set('2.5')
        monitor.skip(1)
        assert sound.all_snapshot()[original]['position'] >= 2.5
        sound.player.pause(original, 0)
        monitor.skip(1)
        assert sound.all_snapshot()[original]['state'] == 'paused'
        assert sound.all_snapshot()[original]['position'] >= 5
        monitor.refresh()
        assert '/' in monitor.timer.cget('text')
        assert monitor.waveform.bars
        assert sound.all_snapshot()[original]['waveform']

        app.add_page('Music')
        second = page_state.book.current['id']
        assert second != first and scripts.text[0][1] == ''
        scripts.bind(0, 1, 'SOUND_TRACK examples/demo_track.wav 60 0 0', [20, 90, 130])
        sound.toggle_track((0, 1), 'examples/demo_track.wav', 60, 0, 0)
        other = sound.pad_key((0, 1))
        assert sound.player.tracks[original].channel_index != sound.player.tracks[other].channel_index
        assert sound.all_snapshot()[original]['state'] == 'paused'
        assert sound.all_snapshot()[other]['state'] == 'playing'
        app.switch_page(first)
        assert '70 1500' in scripts.text[0][1]
        assert sound.all_snapshot()[other]['state'] == 'playing'
        monitor.refresh()
        assert len(monitor.keys) == 2
        assert monitor.frame.winfo_toplevel() is root
        app.toggle_fullscreen()
        root.update()
        assert app.fullscreen
        app.exit_fullscreen()
        root.update()
        assert not app.fullscreen

        path = str(Path(folder) / 'user_layouts/pages.lpl')
        files.save_lp_to_layout(path)
        files.load_layout_to_lp(path, popups=False)
        assert len(page_state.book.pages) == 2
        app.switch_page('Music')
        assert scripts.text[0][1] == 'SOUND_TRACK examples/demo_track.wav 60 0 0'
        guide = app.open_guide()
        root.update()
        guide.destroy()

        # A page command uses the GUI queue, not Tk calls from worker threads.
        scripts.schedule_script('PAGE_PREV', 4, 4)
        wait_for(lambda: page_state.book.current['id'] == first)
        scripts.schedule_script('SOUND_SKIP 1 0 1', 4, 5)
        wait_for(lambda: scripts.threads[4][5] is not None and not scripts.threads[4][5].is_alive())
        assert scripts.validate_script('SOUND_SKIP -5 0 1') is True
        assert scripts.validate_script('SOUND_SEEK nan') is not True
        assert scripts.validate_script('PAGE_NEXT extra') is not True
        assert not errors, errors
        files.layout_changed_since_load = False
        app.disconnect_lp()
        print('Pages/monitor GUI passed: persistent pages, continuing audio, skip while paused, progress, command guide and pad page commands')
finally:
    sound.shutdown()
    root.destroy()
