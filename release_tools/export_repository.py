"""Export the exact source tree to upload to a fresh GitHub repository."""
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    'audio_waveform.py',
    'app_settings.py', 'page_state.py', 'command_guide.py', 'track_monitor.py',
    'app_updater.py', 'update_dialog.py',
    'audio_tracks.py', 'track_commands.py', 'demo_launchpad.py', 'soundtrack_ui.py',
    'LPHK.py', 'bresenham.py', 'files.py', 'kb.py', 'logger.py', 'lp_colors.py',
    'lp_events.py', 'ms.py', 'scripts.py', 'sound.py', 'window.py', 'ui_theme.py',
    'runtime_support.py', 'input_backend.py', 'bundled_tools.py', 'mango_ipc.py',
    'configure_mango.py', 'check_system.py', 'build.py', 'requirements.txt',
    'README.md', 'LICENSE', 'VERSION', 'UPSTREAM.md', 'THIRD_PARTY.md',
    'RELEASE_NOTES.md', '.gitattributes', '.gitignore', 'SETUP.bat', 'RUN.bat',
    'RUN_with_local_venv.bat', 'SETUP.sh', 'RUN.bash', 'SETUP_CACHYOS.sh',
    'install-linux-input.sh', 'START_HERE.txt', 'CACHYOS_MANGOWM.txt',
}
DIRECTORIES = ('.github', 'android', 'system_apis', 'resources', 'docs', 'release_tools',
               'tests', 'user_layouts/examples', 'user_scripts/examples', 'user_sounds/examples')


def export(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ROOT_FILES:
        shutil.copy2(ROOT / name, destination / name)
    for name in DIRECTORIES:
        shutil.copytree(ROOT / name, destination / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'build', '.keys', '*.keystore', '*.apk', '*.idsig'))
    (destination / 'utils').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'utils/launchpad_connector.py', destination / 'utils/launchpad_connector.py')
    # Source archives created on Windows must still contain POSIX shell lines.
    for file in destination.rglob('*'):
        if file.is_file() and file.suffix in {'.py', '.sh', '.bash', '.md', '.yml', '.txt'}:
            text = file.read_text(encoding='utf-8')
            file.write_text(text, encoding='utf-8', newline='\n')
    return destination


def archive(source, path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as package:
        for file in sorted(Path(source).rglob('*')):
            if file.is_file():
                package.write(file, Path('LPHK') / file.relative_to(source))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--zip', type=Path)
    arguments = parser.parse_args()
    folder = export(arguments.destination)
    if arguments.zip:
        archive(folder, arguments.zip)
    print(folder)
