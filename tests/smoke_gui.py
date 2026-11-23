"""Open and close the actual GUI without a Launchpad or generated input."""
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import window

original_make = window.make


def make_for_test():
    # Hardware detection normally opens a modal 'no Launchpad' dialog.
    window.Main_Window.connect_lp = lambda self: None
    original_init = window.Main_Window.init_window

    def init_for_test(self):
        original_init(self)
        self.after(500, window.close)

    window.Main_Window.init_window = init_for_test
    original_make()


window.make = make_for_test
with tempfile.TemporaryDirectory() as data:
    os.environ['LPHK_USER_PATH'] = data
    try:
        runpy.run_path(str(ROOT / 'LPHK.py'), run_name='__main__')
    except SystemExit as result:
        if result.code not in (None, 0):
            raise
    assert window.root_destroyed, 'GUI did not close cleanly'
    assert not window.restart, 'Disconnect unexpectedly requested a restart'
print('GUI startup and shutdown passed')
