"""Compact playback monitor embedded below the Launchpad grid."""
import math
import tkinter as tk
from tkinter import ttk, messagebox
import app_settings
import page_state
import sound
import ui_theme as theme
from audio_waveform import Waveform


def format_time(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'


class TrackMonitor:
    def __init__(self, app):
        self.app = app
        self.frame = tk.Frame(app)
        self.frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=24, pady=(0, 12))
        self.frame.columnconfigure(0, weight=1)
        self.selected = None
        self.keys = []
        self.chooser = ttk.Combobox(self.frame, state='readonly', width=45)
        self.chooser.grid(row=0, column=0, sticky='ew', padx=(0, 12))
        self.chooser.bind('<<ComboboxSelected>>', self.select)
        self.timer = tk.Label(self.frame, text='00:00 / 00:00', font=(theme.MONO, 12))
        self.timer.grid(row=0, column=1, sticky='e')
        self.waveform = Waveform(self.frame, self.scrub_fraction)
        self.waveform.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(6, 4))
        controls = tk.Frame(self.frame)
        controls.grid(row=2, column=0, columnspan=2, sticky='ew')
        theme.button(controls, 'Play / pause track', self.toggle).pack(side='left')
        self.backward = theme.button(controls, '−5s', lambda: self.skip(-1))
        self.backward.pack(side='left', padx=(8, 4))
        self.forward = theme.button(controls, '+5s', lambda: self.skip(1))
        self.forward.pack(side='left', padx=(0, 10))
        tk.Label(controls, text='Skip (s)', fg=theme.MUTED).pack(side='left')
        self.step = tk.StringVar(value=f"{app.settings['skip_seconds']:g}")
        tk.Spinbox(controls, from_=0.1, to=3600, increment=1, textvariable=self.step, width=5,
                   bg=theme.FIELD, buttonbackground=theme.BUTTON, insertbackground=theme.TEXT).pack(side='left', padx=6, ipady=5)
        self.state_label = tk.Label(controls, text='no track selected', fg=theme.MUTED)
        self.state_label.pack(side='right')
        self.step.trace_add('write', self.change_step)
        self.change_step()
        self.refresh()

    def alive(self):
        return bool(self.frame.winfo_exists())

    def select(self, event=None):
        index = self.chooser.current()
        self.selected = self.keys[index] if 0 <= index < len(self.keys) else None

    def refresh(self):
        states = sound.all_snapshot()
        keys = list(states)
        labels = []
        for key in keys:
            state = states[key]
            page_id = key[0] if len(key) == 3 else 'main'
            page = next((page['name'] for page in page_state.book.pages if page['id'] == page_id), 'Other layout')
            labels.append(f"{page} · {key[-2]},{key[-1]} · {state['filename']}")
        self.keys = keys
        if self.selected not in states:
            self.selected = next((key for key, state in states.items() if state['state'] != 'stopped'), next(iter(states), None))
        self.chooser.configure(values=labels)
        if self.selected is not None:
            self.chooser.current(keys.index(self.selected))
        else:
            self.chooser.set('No soundtracks playing')
        state = states.get(self.selected)
        if state:
            self.timer.configure(text=f"{format_time(state['position'])} / {format_time(state['length'])}")
            self.state_label.configure(text=state['state'].replace('_', ' '))
            self.waveform.render(state.get('waveform', []), state['position'], state['length'], state['state'])
        else:
            self.timer.configure(text='00:00 / 00:00')
            self.state_label.configure(text='no track selected')
            self.waveform.render([], 0, 0, 'stopped')

    def change_step(self, *args):
        try:
            value = float(self.step.get())
            if not math.isfinite(value) or not 0 < value <= 3600:
                return
            self.app.settings['skip_seconds'] = value
            app_settings.save(self.app.user_path, self.app.settings)
            self.backward.configure(text=f'−{value:g}s')
            self.forward.configure(text=f'+{value:g}s')
        except (ValueError, OSError):
            pass

    def skip(self, direction):
        try:
            seconds = float(self.step.get())
            if not math.isfinite(seconds) or not 0 < seconds <= 3600:
                raise ValueError('Skip time must be between 0 and 3600 seconds.')
            if self.selected is not None and sound.player:
                sound.player.seek(self.selected, direction * seconds, relative=True)
        except (ValueError, RuntimeError) as error:
            messagebox.showerror('Could not skip', str(error), parent=self.app)

    def scrub_fraction(self, fraction):
        state = sound.all_snapshot().get(self.selected)
        if state and sound.player:
            sound.player.seek(self.selected, state['length'] * fraction)

    def toggle(self):
        if sound.player and self.selected in sound.player.tracks:
            track = sound.player.tracks[self.selected]
            sound.player.toggle(self.selected, track.filename, track.volume * 100, track.fade_in, track.fade_out, track.pause_fade)
