"""Create end-user archives containing the runtime, docs, and licenses."""
from importlib import metadata
from pathlib import Path
import hashlib
import platform
import shutil
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def copy_licenses(destination):
    licenses = destination / 'third-party-licenses'
    licenses.mkdir(exist_ok=True)
    for distribution in metadata.distributions():
        for file in distribution.files or []:
            if not any(word in file.name.lower() for word in ('license', 'copying', 'copyright')):
                continue
            source = Path(distribution.locate_file(file))
            if source.is_file() and '.dist-info' in str(file):
                target = licenses / distribution.metadata['Name'] / Path(str(file)).name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    for name in ('LICENSE.txt', 'LICENSE'):
        source = Path(sys.base_prefix) / name
        if source.is_file():
            shutil.copy2(source, licenses / 'Python-LICENSE.txt')
    if sys.platform.startswith('linux'):
        for package in ('libwayland-client0', 'libwayland-cursor0', 'libxkbcommon0',
                        'libffi8', 'libx11-6', 'libxext6', 'libxft2', 'libxrender1',
                        'libfontconfig1', 'libexpat1', 'libpng16-16', 'zlib1g'):
            source = Path('/usr/share/doc') / package / 'copyright'
            if source.is_file():
                shutil.copy2(source, licenses / (package + '-copyright.txt'))


def main():
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('This release configuration currently supports x86_64 only.')
    version = (ROOT / 'VERSION').read_text().strip()
    system = 'Windows' if sys.platform == 'win32' else 'Linux'
    name = f'LPHK-{version}-{system}-x86_64'
    release = ROOT / 'release'
    staging = release / name
    staging.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'dist/LPHK', staging, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('*.log'))
    for file in ('README.md', 'LICENSE', 'THIRD_PARTY.md', 'UPSTREAM.md'):
        shutil.copy2(ROOT / file, staging / file)
    if system == 'Linux':
        script = staging / 'install-linux-input.sh'
        shutil.copy2(ROOT / script.name, script)
        script.chmod(0o755)
        shutil.copytree(ROOT / '.build-tools/sources', staging / 'third-party-sources', dirs_exist_ok=True)
    copy_licenses(staging)
    if system == 'Windows':
        archive = release / (name + '.zip')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
            for file in sorted(staging.rglob('*')):
                if file.is_file():
                    package.write(file, Path(name) / file.relative_to(staging))
    else:
        archive = release / (name + '.tar.gz')
        with tarfile.open(archive, 'w:gz') as package:
            package.add(staging, arcname=name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (release / (archive.name + '.sha256')).write_text(f'{digest}  {archive.name}\n')
    print(archive)


if __name__ == '__main__':
    main()
