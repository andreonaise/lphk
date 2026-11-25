"""Start the built app without hardware; verify it creates its log and exits."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
executable = ROOT / 'dist/LPHK' / ('LPHK.exe' if sys.platform == 'win32' else 'LPHK')
modules = CArchiveReader(str(executable)).open_embedded_archive('PYZ.pyz').toc
assert {'script_builder', 'script_builder_ui'} <= set(modules), 'Visual builder modules missing from the packaged app'
with tempfile.TemporaryDirectory() as directory:
    environment = os.environ.copy()
    environment.update(LPHK_USER_PATH=directory, SDL_AUDIODRIVER='dummy',
                       LPHK_INPUT_BACKEND='windows' if sys.platform == 'win32' else 'x11')
    for mode in ([], ['--demo']):
        subprocess.run([str(executable), '--smoke-test', *mode], env=environment, timeout=30, check=True)
        log = (Path(directory) / 'LPHK.log').read_text(encoding='utf-8')
        assert 'Input backend:' in log, log
        assert 'Traceback' not in log, log
        if mode:
            assert '[demo] mode enabled' in log, log
            assert 'soundtrack_demo.lpl' in log, log
print('Packaged GUI and demo startup/shutdown passed')
