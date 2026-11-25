"""GitHub release downloads and staged, rollback-capable app replacement."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile

REPOSITORY = 'andreonaise/lphk'
PRESERVE = {'user_layouts', 'user_scripts', 'user_sounds', 'settings.json', 'USERPATH', 'LPHK.log', 'updates', '_rollback'}


def repository_name(value):
    value = value.strip().removeprefix('https://github.com/').removesuffix('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('Enter a GitHub repository such as andreonaise/lphk.')
    return value


def version_tuple(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value.strip())
    if not match:
        raise ValueError('Release versions must use v0.6.0 style tags.')
    return tuple(map(int, match.groups()))


def request(url, binary=False):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'Accept': 'application/octet-stream' if binary else 'application/vnd.github+json',
        'User-Agent': 'LPHK-Updater', 'X-GitHub-Api-Version': '2022-11-28'}), timeout=30)


def latest(repository, current, platform=None):
    repository = repository_name(repository)
    try:
        with request(f'https://api.github.com/repos/{repository}/releases/latest') as response:
            release = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RuntimeError('No published release was found. Draft releases and Actions artifacts are not visible to the updater.') from None
        raise RuntimeError(f'GitHub returned HTTP {error.code}. Try again later.') from None
    version = release['tag_name'].removeprefix('v')
    if version_tuple(version) <= version_tuple(current):
        return None
    system = 'Windows' if (platform or sys.platform) == 'win32' else 'Linux'
    suffix = '.zip' if system == 'Windows' else '.tar.gz'
    filename = f'LPHK-{version}-{system}-x86_64{suffix}'
    assets = release.get('assets', [])
    asset = next((item for item in assets if item['name'] == filename), None)
    if asset is None:
        raise RuntimeError('The latest release does not contain ' + filename)
    checksum = next((item for item in assets if item['name'] == filename + '.sha256'), None)
    if not checksum and not str(asset.get('digest', '')).startswith('sha256:'):
        raise RuntimeError('This release has no SHA-256 checksum. Publish it using the supplied release workflow.')
    return {'version': version, 'repository': repository, 'asset': asset, 'checksum': checksum,
            'notes': release.get('body', '')[:12000]}


def download_asset(repository, asset, destination):
    url = f"https://api.github.com/repos/{repository_name(repository)}/releases/assets/{int(asset['id'])}"
    total = 0
    with request(url, binary=True) as response, Path(destination).open('wb') as output:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > 600 * 1024 * 1024:
                raise RuntimeError('Release asset exceeds the update size limit.')
            output.write(block)


def safe_path(root, name):
    name = name.replace('\\', '/')
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or ':' in name or '\x00' in name:
        raise ValueError('Unsafe path in update archive.')
    target = root.joinpath(*parts.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Update archive escapes its staging folder.')
    return target


def extract(archive, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    total = 0
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                target = safe_path(root, member.filename)
                total += member.file_size
                if total > 2 * 1024**3 or stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError('Unsafe or oversized ZIP update.')
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with package.open(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
    else:
        with tarfile.open(archive) as package:
            members = package.getmembers()
            for member in members:
                target = safe_path(root, member.name)
                total += member.size
                if total > 2 * 1024**3 or not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
                    raise ValueError('Unsafe or oversized TAR update.')
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with package.extractfile(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(member.mode & 0o777)
            for member in members:
                target = safe_path(root, member.name)
                if member.issym():
                    link = PurePosixPath(member.linkname)
                    resolved = (target.parent / member.linkname).resolve()
                    if link.is_absolute() or not resolved.is_relative_to(root.resolve()):
                        raise ValueError('Unsafe symlink in update archive.')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(member.linkname)
                elif member.islnk():
                    origin = safe_path(root, member.linkname)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(origin, target)


def stage(info, user_path, platform=None):
    folder = Path(user_path) / 'updates' / (info['version'] + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    archive = folder / info['asset']['name']
    download_asset(info['repository'], info['asset'], archive)
    expected = str(info['asset'].get('digest', '')).removeprefix('sha256:')
    if info['checksum']:
        checksum = folder / 'checksum.txt'
        download_asset(info['repository'], info['checksum'], checksum)
        expected = checksum.read_text().split()[0].lower()
    if not re.fullmatch('[a-fA-F0-9]{64}', expected) or hashlib.sha256(archive.read_bytes()).hexdigest() != expected.lower():
        raise RuntimeError('Update checksum did not match. Nothing was installed.')
    extract(archive, folder / 'payload')
    name = 'LPHK.exe' if (platform or sys.platform) == 'win32' else 'LPHK'
    candidates = [file.parent for file in (folder / 'payload').rglob(name)
                  if file.is_file() and (file.parent / '_internal/VERSION').is_file()]
    if len(candidates) != 1 or (candidates[0] / '_internal/VERSION').read_text().strip() != info['version']:
        raise RuntimeError('The update does not contain the expected application version.')
    return candidates[0]


def child_environment(user_path):
    environment = os.environ.copy()
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    environment['LPHK_USER_PATH'] = str(user_path)
    for name in list(environment):
        if name.startswith('_PYI_'):
            environment.pop(name)
    original = environment.pop('LD_LIBRARY_PATH_ORIG', None)
    if original is None:
        environment.pop('LD_LIBRARY_PATH', None)
    else:
        environment['LD_LIBRARY_PATH'] = original
    return environment


def launch_install(source, destination, user_path):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    name = 'LPHK.exe' if sys.platform == 'win32' else 'LPHK'
    plan = source.parent / 'update-plan.json'
    plan.write_text(json.dumps({'source': str(source), 'destination': str(destination),
                               'user_path': str(Path(user_path).resolve()), 'pid': os.getpid()}), encoding='utf-8')
    subprocess.Popen([str(source / name), '--apply-update', str(plan)], cwd=source,
                     env=child_environment(user_path))


def wait_for_parent(pid, timeout=60):
    if sys.platform == 'win32':
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, timeout * 1000) == 258:
                    raise RuntimeError('The old app is still running. Close it before updating.')
            finally:
                kernel.CloseHandle(handle)
    else:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
        raise RuntimeError('The old app is still running.')


def apply_update(plan_path, helper_root=None, wait=True, restart=True):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    source, destination = Path(plan['source']).resolve(), Path(plan['destination']).resolve()
    name = 'LPHK.exe' if sys.platform == 'win32' else 'LPHK'
    if helper_root is not None and source != Path(helper_root).resolve():
        raise ValueError('Update helper does not match the staged application.')
    if source == destination or destination == Path(destination.anchor) or destination == Path.home().resolve():
        raise ValueError('Invalid application destination.')
    if not (source / name).is_file() or not (destination / name).is_file() or not (destination / '_internal/VERSION').is_file():
        raise ValueError('The update destination is not an LPHK installation.')
    entries = [entry for entry in source.iterdir() if entry.name not in PRESERVE]
    if wait:
        wait_for_parent(int(plan['pid']))
    backup = destination / '_rollback' / uuid.uuid4().hex
    backup.mkdir(parents=True)
    installed, moved = [], []
    try:
        for entry in entries:
            target = destination / entry.name
            if target.parent.resolve() != destination:
                raise ValueError('Update target escapes the installation.')
            if target.exists() or target.is_symlink():
                target.replace(backup / entry.name)
                moved.append(entry.name)
            installed.append(entry.name)
            if entry.is_dir():
                shutil.copytree(entry, target, symlinks=True)
            else:
                shutil.copy2(entry, target)
    except Exception:
        for entry_name in reversed(installed):
            target = destination / entry_name
            if target.parent.resolve() != destination:
                continue
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
        for entry_name in moved:
            (backup / entry_name).replace(destination / entry_name)
        raise
    if restart:
        subprocess.Popen([str(destination / name), *plan.get('restart_args', [])], cwd=destination, env=child_environment(plan['user_path']))
    return backup
