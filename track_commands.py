"""Portable soundtrack bindings stored as ordinary LPHKscript text."""
import math
import shlex

COMMAND = 'SOUND_TRACK'


def parse(line):
    parts = shlex.split(line)
    if not parts or parts[0] != COMMAND or not 2 <= len(parts) <= 6:
        raise ValueError('Use SOUND_TRACK "filename" [volume] [play_fade_ms] [stop_fade_ms] [pause_fade_ms].')
    filename = parts[1].replace('\\', '/')
    if not filename or filename.startswith('/') or ':' in filename or '..' in filename.split('/'):
        raise ValueError('Choose a file inside user_sounds, using a relative path.')
    numbers = [float(value) for value in parts[2:]]
    if any(not math.isfinite(value) for value in numbers):
        raise ValueError('Soundtrack settings must be finite numbers.')
    volume, fade_in, fade_out = (numbers[:3] + [100, 0, 0][min(len(numbers), 3):])
    pause_fade = numbers[3] if len(numbers) > 3 else None
    if not 0 <= volume <= 100:
        raise ValueError('Volume must be between 0 and 100.')
    fades = (fade_in, fade_out) if pause_fade is None else (fade_in, fade_out, pause_fade)
    if any(value < 0 or value > 3600000 or int(value) != value for value in fades):
        raise ValueError('Fade times must be whole milliseconds between 0 and 3600000.')
    settings = (filename, volume, int(fade_in), int(fade_out))
    return settings if pause_fade is None else (*settings, int(pause_fade))


def build(filename, volume=100, fade_in=0, fade_out=0, pause_fade=None):
    line = f'{COMMAND} {shlex.quote(filename.replace(chr(92), "/"))} {volume:g} {fade_in:g} {fade_out:g}'
    if pause_fade is not None:
        line += f' {pause_fade:g}'
    parse(line)
    return line


def control_fade(line):
    parts = line.split()
    if len(parts) > 2:
        raise ValueError('Use SOUND_PAUSE [fade_ms] or SOUND_RESUME [fade_ms].')
    if len(parts) == 1:
        return None
    value = float(parts[1])
    if not math.isfinite(value) or not 0 <= value <= 3600000 or value != int(value):
        raise ValueError('Fade time must be whole milliseconds between 0 and 3600000.')
    return int(value)
