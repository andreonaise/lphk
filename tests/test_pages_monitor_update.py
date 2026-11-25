from copy import deepcopy
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import ast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_updater
import app_settings
from page_state import PageBook
from track_monitor import format_time
import command_guide


class PageTests(unittest.TestCase):
    def test_legacy_layout_loads_as_one_page(self):
        book = PageBook()
        layout = {'buttons': deepcopy(book.current['buttons'])}
        book.load(layout)
        self.assertEqual(len(book.pages), 1)
        self.assertEqual(book.current['name'], 'Page 1')

    def test_page_names_scripts_colours_and_active_page_roundtrip(self):
        book = PageBook()
        book.current['buttons'][0][1] = {'text': 'SOUND_PAUSE', 'color': [12, 34, 56]}
        second = book.add('Music')
        book.activate(second)
        book.current['buttons'][0][1] = {'text': 'SOUND_RESUME', 'color': [56, 34, 12]}
        saved = book.to_layout()
        restored = PageBook()
        restored.load(json.loads(json.dumps(saved)))
        self.assertEqual(restored.current['name'], 'Music')
        restored.activate('Page 1')
        self.assertEqual(restored.current['buttons'][0][1]['text'], 'SOUND_PAUSE')
        self.assertEqual(saved['buttons'][0][1]['text'], 'SOUND_RESUME')

    def test_bad_layout_does_not_replace_book(self):
        book = PageBook()
        previous = book.to_layout()
        with self.assertRaises(ValueError):
            book.load({'buttons': []})
        self.assertEqual(book.to_layout(), previous)

    def test_duplicate_names_ids_and_last_page_deletion(self):
        book = PageBook()
        with self.assertRaises(ValueError):
            book.add('page 1')
        with self.assertRaises(ValueError):
            book.remove()
        book.add('Music')
        saved = book.to_layout()
        saved['pages'][1]['id'] = saved['pages'][0]['id']
        with self.assertRaises(ValueError):
            book.load(saved)


class GuideTests(unittest.TestCase):
    def test_guide_covers_every_parser_command(self):
        tree = ast.parse((ROOT / 'scripts.py').read_text())
        commands = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VALID_COMMANDS' for target in node.targets):
                commands.update(ast.literal_eval(node.value))
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                function = node.value.func
                if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name) and function.value.id == 'VALID_COMMANDS':
                    commands.update(ast.literal_eval(node.value.args[0]))
        self.assertEqual(commands, set(command_guide.COMMANDS))
        self.assertIn('SOUND_PAUSE', command_guide.search('pause'))
        self.assertIn('PAGE_NEXT', command_guide.search('page'))

    def test_monitor_time_format(self):
        self.assertEqual(format_time(141.9), '02:21')
        self.assertEqual(format_time(225), '03:45')
        self.assertEqual(format_time(3661), '01:01:01')

    def test_settings_only_store_non_secret_values(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as folder:
            app_settings.save(folder, {'skip_seconds': 12.5, 'update_repository': 'andreonaise/lphk', 'token': 'never-save'})
            data = (Path(folder) / 'settings.json').read_text()
            self.assertNotIn('never-save', data)
            self.assertEqual(app_settings.load(folder)['skip_seconds'], 12.5)


class UpdateTests(unittest.TestCase):
    def release(self):
        return {'tag_name': 'v0.6.0', 'assets': [
            {'id': 1, 'name': 'LPHK-0.6.0-Windows-x86_64.zip', 'digest': 'sha256:' + '0' * 64},
            {'id': 2, 'name': 'LPHK-0.6.0-Linux-x86_64.tar.gz', 'digest': 'sha256:' + '0' * 64}], 'body': 'Release'}

    def test_latest_selects_os_binary_and_rejects_downgrade(self):
        data = json.dumps(self.release()).encode()
        with patch('app_updater.request', side_effect=lambda *a, **k: BytesIO(data)):
            result = app_updater.latest('https://github.com/andreonaise/lphk', '0.5.1', 'win32')
            self.assertEqual(result['asset']['id'], 1)
            self.assertIsNone(app_updater.latest('andreonaise/lphk', '0.6.0', 'linux'))
            self.assertEqual(app_updater.latest('andreonaise/lphk', '0.5.1', 'linux')['asset']['id'], 2)

    def test_release_without_checksum_is_not_installed(self):
        data = self.release()
        data['assets'][0].pop('digest')
        with patch('app_updater.request', return_value=BytesIO(json.dumps(data).encode())):
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                app_updater.latest('andreonaise/lphk', '0.5.1', 'win32')

    def test_zip_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('../outside.txt', 'bad')
            with self.assertRaises(ValueError):
                app_updater.extract(archive, Path(folder) / 'payload')
            self.assertFalse((Path(folder) / 'outside.txt').exists())

    def test_tar_external_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.tar.gz'
            with tarfile.open(archive, 'w:gz') as package:
                link = tarfile.TarInfo('outside')
                link.type, link.linkname = tarfile.SYMTYPE, '/outside'
                package.addfile(link)
            with self.assertRaises(ValueError):
                app_updater.extract(archive, Path(folder) / 'payload')

    def test_staged_download_verifies_checksum_and_version(self):
        with tempfile.TemporaryDirectory() as folder:
            content = BytesIO()
            with zipfile.ZipFile(content, 'w') as package:
                package.writestr('app/LPHK.exe', 'new')
                package.writestr('app/_internal/VERSION', '0.6.0')
            data = content.getvalue()
            info = {'version': '0.6.0', 'repository': 'andreonaise/lphk', 'checksum': None,
                    'asset': {'name': 'update.zip', 'id': 1, 'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}}
            def download(repository, asset, destination):
                Path(destination).write_bytes(data)
            with patch('app_updater.download_asset', side_effect=download):
                root = app_updater.stage(info, folder, 'win32')
                self.assertEqual((root / 'LPHK.exe').read_text(), 'new')
                info['asset']['digest'] = 'sha256:' + '0' * 64
                with self.assertRaisesRegex(RuntimeError, 'checksum'):
                    app_updater.stage(info, folder, 'win32')

    def create_plan(self, folder):
        base = Path(folder)
        source, destination = base / 'staged', base / 'installed'
        executable = 'LPHK.exe' if sys.platform == 'win32' else 'LPHK'
        for path, version, text in ((source, '0.6.0', 'new'), (destination, '0.5.1', 'old')):
            (path / '_internal').mkdir(parents=True)
            (path / '_internal/VERSION').write_text(version)
            (path / executable).write_text(text)
            (path / 'user_sounds').mkdir()
        (destination / 'user_sounds/custom.wav').write_text('user audio')
        (destination / 'settings.json').write_text('settings')
        (source / 'settings.json').write_text('replacement')
        plan = base / 'plan.json'
        plan.write_text(json.dumps({'source': str(source), 'destination': str(destination), 'user_path': str(destination), 'pid': 0}))
        return source, destination, plan, executable

    def test_install_preserves_user_data_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            source, destination, plan, executable = self.create_plan(folder)
            backup = app_updater.apply_update(plan, helper_root=source, wait=False, restart=False)
            self.assertEqual((destination / executable).read_text(), 'new')
            self.assertEqual((backup / executable).read_text(), 'old')
            self.assertEqual((destination / 'settings.json').read_text(), 'settings')
            self.assertEqual((destination / 'user_sounds/custom.wav').read_text(), 'user audio')

    def test_failed_install_rolls_back_old_application(self):
        with tempfile.TemporaryDirectory() as folder:
            source, destination, plan, executable = self.create_plan(folder)
            original = app_updater.shutil.copy2
            def fail(src, dst, *args, **kwargs):
                if Path(src).resolve() == (source / executable).resolve():
                    raise OSError('simulated copy failure')
                return original(src, dst, *args, **kwargs)
            with patch('app_updater.shutil.copy2', side_effect=fail), self.assertRaises(OSError):
                app_updater.apply_update(plan, helper_root=source, wait=False, restart=False)
            self.assertEqual((destination / executable).read_text(), 'old')
            self.assertEqual((destination / '_internal/VERSION').read_text(), '0.5.1')
            self.assertEqual((destination / 'user_sounds/custom.wav').read_text(), 'user audio')


if __name__ == '__main__':
    unittest.main()
