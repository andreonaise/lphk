"""Exercise staged replacement, preserved data, backup, and app restart."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_updater

source = ROOT / 'dist/LPHK'
name = 'LPHK.exe' if sys.platform == 'win32' else 'LPHK'
with tempfile.TemporaryDirectory(dir=ROOT.parent) as folder:
    folder = Path(folder)
    destination = folder / 'installed'
    shutil.copytree(source, destination, symlinks=True)
    user = destination / 'user_layouts'
    user.mkdir(exist_ok=True)
    (user / 'keep.lpl').write_text('user layout fixture')
    (destination / 'settings.json').write_text('{"skip_seconds": 7}')
    (destination / '_internal/README.md').write_text('previous runtime fixture')
    parent = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(1)'])
    plan = folder / 'plan.json'
    plan.write_text(json.dumps(dict(source=str(source), destination=str(destination),
                                   user_path=str(destination), pid=parent.pid,
                                   restart_args=['--smoke-test', '--demo'])))
    environment = app_updater.child_environment(destination)
    environment['SDL_AUDIODRIVER'] = 'dummy'
    environment['LPHK_INPUT_BACKEND'] = 'windows' if sys.platform == 'win32' else 'x11'
    result = subprocess.run([str(source / name), '--apply-update', str(plan)],
                            env=environment, timeout=45)
    parent.wait(timeout=5)
    assert result.returncode == 0
    assert not (folder / 'update-error.log').exists()
    assert (user / 'keep.lpl').read_text() == 'user layout fixture'
    assert json.loads((destination / 'settings.json').read_text())['skip_seconds'] == 7
    backups = list((destination / '_rollback').iterdir())
    assert len(backups) == 1
    assert (backups[0] / '_internal/README.md').read_text() == 'previous runtime fixture'
    assert (destination / '_internal/README.md').read_text() != 'previous runtime fixture'
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        log = destination / 'LPHK.log'
        text = log.read_text(encoding='utf-8') if log.exists() else ''
        if '[demo] mode enabled' in text and 'soundtrack_demo.lpl' in text:
            break
        time.sleep(0.2)
    else:
        raise AssertionError('Updated app did not complete demo startup/shutdown: ' + text)
    assert 'Traceback' not in text, text
    time.sleep(2)
print('Frozen updater passed: parent exit, runtime backup/replacement, preserved user files, restart')
