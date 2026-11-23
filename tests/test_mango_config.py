from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from configure_mango import BEGIN, END, RULE, configure


class MangoConfigTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'config.conf'

    def test_preserves_config_with_backup_and_scoped_rule(self):
        original = 'xkb_rules_layout=de\nbind=SUPER,r,reload_config\n'
        self.path.write_text(original)
        backup = configure(self.path)
        self.assertEqual(backup.read_text(), original)
        result = self.path.read_text()
        self.assertTrue(result.startswith(BEGIN))
        self.assertIn(RULE, result)
        self.assertTrue(result.endswith(original))

    def test_rerun_does_not_duplicate_or_create_extra_backup(self):
        self.path.write_text('xkb_rules_layout=de\n')
        configure(self.path)
        self.assertIsNone(configure(self.path))
        self.assertEqual(self.path.read_text().count(BEGIN), 1)
        self.assertEqual(len(list(self.path.parent.glob('*.lphk-backup-*'))), 1)

    def test_existing_managed_rule_can_be_updated(self):
        self.path.write_text(f'{BEGIN}\nold rule\n{END}\nxkb_rules_layout=de\n')
        configure(self.path)
        self.assertNotIn('old rule', self.path.read_text())
        self.assertIn('xkb_rules_layout=de', self.path.read_text())

    def test_malformed_block_is_not_modified(self):
        for original in (BEGIN, END, END + '\n' + BEGIN):
            self.path.write_text(original)
            with self.assertRaises(ValueError):
                configure(self.path)
            self.assertEqual(self.path.read_text(), original)


if __name__ == '__main__':
    unittest.main()
