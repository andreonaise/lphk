"""Shared visual-command forms and lossless editing of existing script lines."""
import math
import shlex


def field(name, label, kind='text', default='', optional=False, minimum=None, maximum=None, scale=1):
    return dict(name=name, label=label, kind=kind, default=str(default), optional=optional,
                minimum=minimum, maximum=maximum, scale=scale)


KEYS = list('abcdefghijklmnopqrstuvwxyz0123456789') + [
    'alt', 'alt_gr', 'backspace', 'caps_lock', 'cmd', 'ctrl', 'delete', 'down', 'end',
    'enter', 'esc', 'home', 'insert', 'left', 'menu', 'mouse_left', 'mouse_middle',
    'mouse_right', 'mute', 'next_track', 'num_lock', 'page_down', 'page_up', 'pause',
    'play_pause', 'prev_track', 'print_screen', 'right', 'scroll_lock', 'shift',
    'shift_r', 'space', 'tab', 'up', 'vol_down', 'vol_up'] + [f'f{i}' for i in range(1, 25)]


def key():
    return field('key', 'Key or mouse button', 'key', 'space')


def number(name, label, default, optional=False, minimum=0, maximum=86400, kind='number', scale=1):
    return field(name, label, kind, default, optional, minimum, maximum, scale)


def fade(name, label, optional=True, default=''):
    return number(name, label + ' (seconds)', default, optional, 0, 3600, scale=1000)


def xy():
    return [number('x', 'X position / movement (pixels)', 0, minimum=-1000000, maximum=1000000, kind='integer'),
            number('y', 'Y position / movement (pixels)', 0, minimum=-1000000, maximum=1000000, kind='integer')]


def line_options():
    return [number('delay', 'Delay between steps (milliseconds)', '', True, 0, 3600000),
            number('step', 'Pixels per step', '', True, 1, 1000000, 'integer')]


def target():
    return [number('x', 'Target pad column (blank = all tracks)', '', True, 0, 8, 'integer'),
            number('y', 'Target pad row (blank = all tracks)', '', True, 0, 8, 'integer')]


# The order is the actual argument order used by the existing script engine.
FORMS = {
    '@ASYNC': ('Run in background', []),
    '@SIMPLE': ('Hold a key while the pad is held', [key()]),
    '@LOAD_LAYOUT': ('Load another layout', [field('path', 'Layout file', 'layout')]),
    'STRING': ('Type text', [field('text', 'Text to type', 'remainder')]),
    'DELAY': ('Wait', [number('seconds', 'Wait time (seconds)', .5)]),
    'TAP': ('Tap a key or mouse button', [key(), number('count', 'Repetitions (blank = 1)', '', True, 1, 1000000, 'integer'), number('hold', 'Hold each tap (seconds)', '', True)]),
    'PRESS': ('Hold down a key or mouse button', [key()]),
    'RELEASE': ('Release a key or mouse button', [key()]),
    'RELEASE_ALL': ('Release all held keys', []),
    'WEB': ('Open a website', [field('url', 'Website address', default='https://')]),
    'WEB_NEW': ('Open a website in a new window', [field('url', 'Website address', default='https://')]),
    'CODE': ('Run a program', [field('program', 'Program path / command', 'program')]),
    'OPEN': ('Open a file or folder', [field('path', 'File or folder', 'file')]),
    'SOUND': ('Play a sound effect', [field('path', 'Audio file (no spaces for this legacy command)', 'sound'), number('volume', 'Volume (%)', '', True, 0, 100)]),
    'SOUND_TRACK': ('Play / pause a soundtrack', [field('path', 'Audio file', 'soundtrack', 'examples/demo_track.wav'), number('volume', 'Volume (%)', 80, False, 0, 100), fade('play', 'Play / resume fade-in', False, 1.5), fade('stop', 'Stop / end fade-out', False, 2), fade('pause', 'Pause fade-out', False, .5)]),
    'SOUND_PAUSE': ('Pause all soundtracks', [fade('fade', 'Pause fade-out (blank = each track’s setting)')]),
    'SOUND_RESUME': ('Resume all paused soundtracks', [fade('fade', 'Resume fade-in (blank = each track’s setting)')]),
    'SOUND_STOP': ('Stop all audio', [fade('fade', 'Stop fade-out (blank = stop immediately)')]),
    'SOUND_SKIP': ('Skip forward / backward', [number('seconds', 'Seconds to skip (negative = backward)', 5, minimum=-864000, maximum=864000), *target()]),
    'SOUND_SEEK': ('Jump to a track position', [number('seconds', 'Position (seconds from start)', 30, maximum=864000), *target()]),
    'WAIT_UNPRESSED': ('Wait until this pad is released', []),
    'M_MOVE': ('Move the pointer by an offset', xy()),
    'M_SET': ('Move the pointer to a position', xy()),
    'M_SCROLL': ('Scroll', [number('vertical', 'Vertical scroll (negative = down)', -3, minimum=-1000000, maximum=1000000), number('horizontal', 'Horizontal scroll', '', True, -1000000, 1000000)]),
    'M_LINE': ('Move the pointer along a line', [number('x1', 'Start X (pixels)', 100, minimum=-1000000, maximum=1000000, kind='integer'), number('y1', 'Start Y (pixels)', 100, minimum=-1000000, maximum=1000000, kind='integer'), number('x2', 'End X (pixels)', 300, minimum=-1000000, maximum=1000000, kind='integer'), number('y2', 'End Y (pixels)', 100, minimum=-1000000, maximum=1000000, kind='integer'), *line_options()]),
    'M_LINE_MOVE': ('Move the pointer along a relative line', [*xy(), *line_options()]),
    'M_LINE_SET': ('Move in a line to a position', [*xy(), *line_options()]),
    'M_STORE': ('Remember the pointer position', []),
    'M_RECALL': ('Return to the remembered pointer position', []),
    'M_RECALL_LINE': ('Move in a line to the remembered position', line_options()),
    'LABEL': ('Name a point in this sequence', [field('label', 'Label name', 'label', 'start')]),
    'GOTO_LABEL': ('Jump to a named point', [field('label', 'Jump to label', 'label', 'start')]),
    'IF_PRESSED_GOTO_LABEL': ('Jump while this pad is held', [field('label', 'Jump to label', 'label', 'start')]),
    'IF_UNPRESSED_GOTO_LABEL': ('Jump when this pad is released', [field('label', 'Jump to label', 'label', 'start')]),
    'REPEAT_LABEL': ('Repeat from a named point', [field('label', 'Repeat from label', 'label', 'start'), number('count', 'Repeat count', 3, minimum=0, maximum=1000000, kind='integer')]),
    'IF_PRESSED_REPEAT_LABEL': ('Repeat while this pad is held', [field('label', 'Repeat from label', 'label', 'start'), number('count', 'Repeat count', 3, minimum=0, maximum=1000000, kind='integer')]),
    'IF_UNPRESSED_REPEAT_LABEL': ('Repeat when this pad is released', [field('label', 'Repeat from label', 'label', 'start'), number('count', 'Repeat count', 3, minimum=0, maximum=1000000, kind='integer')]),
    'RESET_REPEATS': ('Reset repeat counters', []),
    'PAGE': ('Switch to a page', [field('page', 'Page name or number', 'page', '1')]),
    'PAGE_NEXT': ('Go to the next page', []),
    'PAGE_PREV': ('Go to the previous page', []),
    '-': ('Comment / note', [field('text', 'Note', 'remainder')]),
}

REMAINDER = {'STRING', 'CODE', 'OPEN', '@LOAD_LAYOUT', '-'}


def form_description(description):
    return description.replace('Fades are milliseconds.', 'Enter fade times in seconds here.').replace('Omit fade_ms', 'Leave the fade time blank').replace('fade_ms', 'fade time')


FILL_DEFAULTS = {'TAP': ['space', '1', '0'], 'SOUND_TRACK': ['', '100', '0', '0', '0'],
                 'M_LINE': ['0', '0', '0', '0', '0', '1'],
                 'M_LINE_MOVE': ['0', '0', '0', '1'], 'M_LINE_SET': ['0', '0', '0', '1'],
                 'M_RECALL_LINE': ['0', '1']}


def build(command, values):
    fields = FORMS[command][1]
    args = []
    for f in fields:
        raw = str(values.get(f['name'], '')).strip() if f['kind'] != 'remainder' else str(values.get(f['name'], ''))
        if '\n' in raw or '\r' in raw:
            raise ValueError(f"{f['label']}: use one line per action.")
        if raw == '':
            if not f['optional']:
                raise ValueError(f"{f['label']} is required.")
            args.append('')
            continue
        if f['kind'] in ('number', 'integer'):
            value = float(raw)
            if not math.isfinite(value) or not f['minimum'] <= value <= f['maximum']:
                raise ValueError(f"{f['label']}: enter a number from {f['minimum']} to {f['maximum']}.")
            if f['kind'] == 'integer' and value != int(value):
                raise ValueError(f"{f['label']}: enter a whole number.")
            scaled = value * f['scale']
            if f['scale'] == 1000:
                if abs(scaled - round(scaled)) > 1e-6:
                    raise ValueError('Fade times support millisecond precision (three decimal places).')
                scaled = round(scaled)
            raw = f'{scaled:g}'
        elif command not in REMAINDER and command not in ('PAGE', 'SOUND_TRACK') and any(c.isspace() for c in raw):
            raise ValueError(f"{f['label']} cannot contain spaces for this command.")
        if command in ('PAGE', 'SOUND_TRACK') and f['name'] in ('path', 'page'):
            if '"' in raw:
                raise ValueError('Names cannot contain a double quote.')
            if command == 'SOUND_TRACK':
                raw = raw.replace('\\', '/')
                if raw.startswith('/') or ':' in raw or '..' in raw.split('/'):
                    raise ValueError('Choose audio inside user_sounds, using a relative path.')
                if "'" in raw:
                    raise ValueError('Use an audio filename without quote characters.')
                raw = '"' + raw + '"'
            elif any(c.isspace() for c in raw):
                raw = '"' + raw + '"'
        args.append(raw)
    if command in ('SOUND_SKIP', 'SOUND_SEEK') and bool(args[1]) != bool(args[2]):
        raise ValueError('Choose both target pad coordinates, or leave both blank for all tracks.')
    while args and not args[-1]:
        args.pop()
    for index, value in enumerate(args):
        if value == '':
            args[index] = FILL_DEFAULTS.get(command, [])[index]
    return command + (' ' + ' '.join(args) if args else '')


def parse(line):
    """Return editable form values, or None if a line needs preserving verbatim."""
    stripped = line.strip()
    if not stripped:
        return None
    command, _, tail = stripped.partition(' ')
    if stripped.startswith('-'):
        command, tail = '-', stripped[1:].lstrip()
    if command not in FORMS:
        return None
    fields = FORMS[command][1]
    try:
        args = [tail] if command in REMAINDER else (shlex.split(tail) if command == 'SOUND_TRACK' else ([tail.strip('"')] if command == 'PAGE' else tail.split()))
        if len(args) > len(fields):
            return None
        values = {f['name']: '' for f in fields}
        for f, arg in zip(fields, args):
            values[f['name']] = f'{float(arg) / f["scale"]:g}' if f['scale'] != 1 else arg
        # Preserve legacy defaults when opening old short soundtrack bindings.
        if command == 'SOUND_TRACK':
            for name, default in [('volume', '100'), ('play', '0'), ('stop', '0')]:
                values[name] = values[name] or default
            values['pause'] = values['pause'] or values['stop']
        build(command, values)
        return command, values
    except (ValueError, IndexError, TypeError):
        return None


def describe(line):
    parsed = parse(line)
    if not parsed:
        return 'Blank line' if not line.strip() else 'Original line (kept as written): ' + line.strip()
    command, values = parsed
    return FORMS[command][0] + (' · ' + ', '.join(v for v in values.values() if v) if values else '')


def validate_sequence(lines):
    active = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith('-')]
    for index, line in enumerate(active):
        if line.startswith('@') and index != 0:
            raise ValueError('Run in background, Hold a key, and Load layout must be the first action.')
    if active and active[0].split()[0] in ('@SIMPLE', '@LOAD_LAYOUT') and len(active) > 1:
        raise ValueError('Hold a key and Load layout each use a pad on their own. Use another pad for additional actions.')
    labels = [line.split()[1] for line in active if line.startswith('LABEL ') and len(line.split()) == 2]
    if len(labels) != len(set(labels)):
        raise ValueError('Each label needs a unique name.')
    for line in active:
        words = line.split()
        if words[0].endswith(('GOTO_LABEL', 'REPEAT_LABEL')) and len(words) > 1 and words[1] not in labels:
            raise ValueError('Add a named point (label) called ' + words[1] + ' before using it as a jump/repeat target.')


def shortcut(key_name, modifiers):
    if not key_name or any(c.isspace() for c in key_name):
        raise ValueError('Choose a key. Use space for the spacebar.')
    return [*('PRESS ' + key for key in modifiers), 'TAP ' + key_name,
            *('RELEASE ' + key for key in reversed(modifiers))]
