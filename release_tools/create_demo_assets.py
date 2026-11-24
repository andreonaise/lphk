"""Generate an original short demo tone and its example Launchpad layout."""
from array import array
import json
import math
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / 'user_sounds/examples/demo_track.wav'
    target.parent.mkdir(parents=True, exist_ok=True)
    rate, duration = 22050, 16
    samples = array('h')
    notes = [146.83, 174.61, 220, 196]
    for index in range(rate * duration):
        seconds = index / rate
        frequency = notes[int(seconds / 2) % len(notes)]
        edge = min(1, seconds / 0.03, (duration - seconds) / 0.03)
        gain = 0.12 * edge * (0.75 + 0.25 * math.sin(seconds * math.tau * 0.5))
        value = math.sin(math.tau * frequency * seconds) + 0.25 * math.sin(math.tau * frequency * 2 * seconds)
        samples.append(round(32767 * gain * value))
    if sys.byteorder != 'little':
        samples.byteswap()
    with wave.open(str(target), 'wb') as output:
        output.setparams((1, 2, rate, 0, 'NONE', ''))
        output.writeframes(samples.tobytes())
    buttons = [[{'color': [0, 0, 0], 'text': ''} for y in range(9)] for x in range(9)]
    for x, y, text, colour in (
        (0, 1, 'SOUND_TRACK examples/demo_track.wav 70 1500 1200 800', [70, 120, 90]),
        (0, 2, 'SOUND_TRACK examples/demo_track.wav 40 2500 2000 600', [70, 100, 150]),
        (3, 1, 'SOUND_STOP 1000', [160, 80, 80]),
    ):
        buttons[x][y] = {'color': colour, 'text': text}
    layout = ROOT / 'user_layouts/examples/soundtrack_demo.lpl'
    layout.parent.mkdir(parents=True, exist_ok=True)
    layout.write_text(json.dumps({'version': '0.1.1', 'buttons': buttons}, indent=2), encoding='utf-8')
    print('Generated demo audio and layout; the audio is synthesized for this project.')


if __name__ == '__main__':
    main()
