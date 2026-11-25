import ast
from pathlib import Path
import unittest
import script_builder as builder


class ScriptBuilderTests(unittest.TestCase):
    def test_every_command_has_a_form(self):
        module = ast.parse((Path(__file__).resolve().parents[1] / 'command_guide.py').read_text(encoding='utf-8'))
        catalog = ast.literal_eval(next(n.value for n in module.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'COMMANDS' for t in n.targets)))
        self.assertEqual(set(builder.FORMS), set(catalog) | {'-'})

    def test_soundtrack_values_use_seconds_in_forms_and_milliseconds_in_script(self):
        command, values = builder.parse('SOUND_TRACK "my song.wav" 70 1500 2000 500')
        self.assertEqual(values['play'], '1.5')
        self.assertEqual(values['pause'], '0.5')
        self.assertEqual(builder.build(command, values), 'SOUND_TRACK "my song.wav" 70 1500 2000 500')

    def test_legacy_soundtrack_pause_default_is_preserved(self):
        command, values = builder.parse('SOUND_TRACK music.ogg 80 1500 2500')
        self.assertEqual(values['pause'], '2.5')
        self.assertTrue(builder.build(command, values).endswith('2500 2500'))

    def test_later_optional_argument_fills_earlier_defaults(self):
        self.assertEqual(builder.build('TAP', dict(key='space', count='', hold='0.2')), 'TAP space 1 0.2')
        self.assertEqual(builder.build('M_LINE_SET', dict(x='120', y='240', delay='', step='5')), 'M_LINE_SET 120 240 0 5')

    def test_optional_fades_keep_individual_defaults(self):
        self.assertEqual(builder.build('SOUND_PAUSE', dict(fade='')), 'SOUND_PAUSE')
        self.assertEqual(builder.build('SOUND_PAUSE', dict(fade='0.125')), 'SOUND_PAUSE 125')
        self.assertEqual(builder.build('SOUND_STOP', dict(fade='0')), 'SOUND_STOP 0')

    def test_target_coordinates_must_be_paired(self):
        with self.assertRaises(ValueError):
            builder.build('SOUND_SKIP', dict(seconds='5', x='0', y=''))
        self.assertEqual(builder.build('SOUND_SKIP', dict(seconds='-5', x='0', y='1')), 'SOUND_SKIP -5 0 1')

    def test_remainder_text_preserves_spaces_and_windows_paths(self):
        for line in ('STRING hello world', 'OPEN C:\\my files\\example.txt', 'CODE C:\\my app\\program.exe', '@LOAD_LAYOUT my layouts/test.lpl'):
            command, values = builder.parse(line)
            self.assertEqual(builder.build(command, values), line)

    def test_page_names_and_comments(self):
        self.assertEqual(builder.build('PAGE', dict(page='Sound tracks')), 'PAGE "Sound tracks"')
        self.assertEqual(builder.build('-', dict(text='a note')), '- a note')
        self.assertEqual(builder.parse('-a note')[1]['text'], 'a note')

    def test_rejects_injection_nonfinite_fractional_counts_and_invalid_fades(self):
        for command, values in [('STRING', dict(text='hello\nTAP a')), ('DELAY', dict(seconds='nan')), ('TAP', dict(key='space', count='1.5', hold='')), ('SOUND_PAUSE', dict(fade='0.0001')), ('SOUND', dict(path='my song.wav', volume='80'))]:
            with self.subTest(command=command), self.assertRaises(ValueError):
                builder.build(command, values)

    def test_unrecognized_lines_are_not_rewritten(self):
        for line in ('CUSTOM_COMMAND something', 'TAP space extra invalid arguments', '', 'SOUND_TRACK "unterminated'):
            self.assertIsNone(builder.parse(line))

    def test_shortcut_releases_modifiers_in_reverse_order(self):
        self.assertEqual(builder.shortcut('s', ['ctrl', 'shift']), ['PRESS ctrl', 'PRESS shift', 'TAP s', 'RELEASE shift', 'RELEASE ctrl'])

    def test_sequence_checks_headers_and_labels(self):
        builder.validate_sequence(['- note', '@ASYNC', 'LABEL again', 'DELAY 1', 'REPEAT_LABEL again 3'])
        for lines in (['TAP a', '@ASYNC'], ['@SIMPLE a', 'TAP b'], ['LABEL start', 'LABEL start'], ['GOTO_LABEL missing']):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                builder.validate_sequence(lines)

    def test_all_guide_examples_open_in_forms(self):
        module = ast.parse((Path(__file__).resolve().parents[1] / 'command_guide.py').read_text(encoding='utf-8'))
        catalog = ast.literal_eval(next(n.value for n in module.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'COMMANDS' for t in n.targets)))
        for command, entry in catalog.items():
            line = next(line for line in entry[3].splitlines() if line.split()[0] == command)
            with self.subTest(command=command):
                self.assertIsNotNone(builder.parse(line))

    def test_form_description_explains_gui_time_units(self):
        self.assertIn('seconds', builder.form_description('Fades are milliseconds.'))
        self.assertNotIn('fade_ms', builder.form_description('Omit fade_ms to use each track setting.'))


if __name__ == '__main__':
    unittest.main()
