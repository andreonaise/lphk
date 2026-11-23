"""Build the helper executables shipped in Linux releases (build machine only)."""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.build-tools'
SOURCES = {
    'ydotool': ('ReimuNotMoe/ydotool', '57ba7d0af525e82da2de0e275d169477f293b197'),
    'wtype': ('atx/wtype', '4b9cc29664f178cf380ccfe7f98405d38dffda3c'),
}


def run(*arguments, cwd=None):
    subprocess.run(list(map(str, arguments)), cwd=cwd, check=True)


def main():
    if not sys.platform.startswith('linux'):
        raise SystemExit('Linux helpers must be built on Linux.')
    (DEST / 'bin').mkdir(parents=True, exist_ok=True)
    (DEST / 'sources').mkdir(exist_ok=True)
    for name, (repository, revision) in SOURCES.items():
        archive = DEST / 'sources' / f'{name}-{revision}.tar.gz'
        if not archive.exists():
            urllib.request.urlretrieve(f'https://codeload.github.com/{repository}/tar.gz/{revision}', archive)
        with tarfile.open(archive) as package:
            package.extractall(DEST, filter='data')
        source = DEST / f'{name}-{revision}'
        if name == 'ydotool':
            run('cmake', '-S', source, '-B', source / 'build', '-DCMAKE_BUILD_TYPE=Release')
            run('cmake', '--build', source / 'build', '--target', 'ydotool', 'ydotoold', '-j2')
            for binary in ('ydotool', 'ydotoold'):
                shutil.copy2(source / 'build' / binary, DEST / 'bin' / binary)
        else:
            run('meson', 'setup', source / 'build', source, '--buildtype=release')
            run('meson', 'compile', '-C', source / 'build')
            shutil.copy2(source / 'build/wtype', DEST / 'bin/wtype')
    print('Linux helpers built. Their corresponding source archives are retained for distribution.')


if __name__ == '__main__':
    main()
