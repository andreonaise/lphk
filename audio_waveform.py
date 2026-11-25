"""A waveform timeline derived from decoded PCM, with played/unplayed colouring."""
import struct
import tkinter as tk
import ui_theme as theme


def overview(buffer, channels=2, bits=-16, bins=256):
    if bits != -16 or channels < 1:
        return []
    data = memoryview(buffer).cast('B')
    frame_bytes = channels * 2
    frames = len(data) // frame_bytes
    if not frames:
        return []
    count = min(bins, frames)
    peaks = []
    for index in range(count):
        start, end = index * frames // count, (index + 1) * frames // count
        step = max(1, (end - start) // 32)
        maximum = 0
        for frame in range(start, end, step):
            for channel in range(channels):
                value = abs(struct.unpack_from('<h', data, frame * frame_bytes + channel * 2)[0])
                maximum = max(maximum, value)
        peaks.append(maximum / 32768)
    return peaks


class Waveform(tk.Canvas):
    def __init__(self, parent, seek):
        super().__init__(parent, height=38, bg=theme.FIELD, highlightthickness=0, cursor='hand2')
        self.seek = seek
        self.shape = None
        self.bars = []
        self.cursor_line = None
        self.bind('<Button-1>', lambda event: self.seek(max(0, min(1, event.x / max(1, self.winfo_width())))))

    def render(self, peaks, position, duration, state):
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        shape = (id(peaks), width, height)
        if shape != self.shape:
            self.delete('all')
            self.bars = []
            maximum = max(peaks, default=0) or 1
            for index, peak in enumerate(peaks):
                x = (index + 0.5) * width / max(1, len(peaks))
                amplitude = max(1, peak / maximum * (height / 2 - 3))
                self.bars.append(self.create_line(x, height / 2 - amplitude, x, height / 2 + amplitude,
                                                 fill=theme.BORDER, width=max(1, width / max(1, len(peaks)) - 1)))
            if not peaks:
                self.create_line(0, height / 2, width, height / 2, fill=theme.BORDER)
            self.cursor_line = self.create_line(0, 0, 0, height, fill=theme.TEXT, width=1)
            self.shape = shape
        fraction = max(0, min(1, position / duration)) if duration else 0
        colour = '#cd9b48' if state == 'paused' else theme.ACCENT
        for index, item in enumerate(self.bars):
            self.itemconfigure(item, fill=colour if (index + 0.5) / len(self.bars) <= fraction else theme.BORDER)
        self.coords(self.cursor_line, width * fraction, 0, width * fraction, height)
