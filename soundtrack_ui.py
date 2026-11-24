"""Small soundtrack binding editor; settings stay in the pad's script."""
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import ui_theme as theme
import track_commands
import sound


def import_file(source, user_path):
    source = Path(source).resolve()
    destination = (Path(user_path) / 'user_sounds').resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if source.is_relative_to(destination):
        return source.relative_to(destination).as_posix()
    target = destination / source.name
    count = 2
    while target.exists():
        target = destination / f'{source.stem}-{count}{source.suffix}'
        count += 1
    shutil.copy2(source, target)
    return target.name


def open_settings(parent, text_widget, user_path):
    dialog = tk.Toplevel(parent)
    dialog.title('Soundtrack')
    dialog.transient(parent)
    dialog.resizable(False, False)
    values = ('examples/demo_track.wav', 80, 1000, 1000)
    for line in text_widget.get('1.0', 'end').splitlines():
        if line.strip().startswith('SOUND_TRACK '):
            try:
                values = track_commands.parse(line.strip())
            except ValueError:
                pass
            break
    filename = tk.StringVar(value=values[0])
    volume = tk.StringVar(value=f'{values[1]:g}')
    fade_in = tk.StringVar(value=f'{values[2] / 1000:g}')
    fade_out = tk.StringVar(value=f'{values[3] / 1000:g}')
    pause_fade = tk.StringVar(value=f'{(values[4] if len(values) > 4 else values[3]) / 1000:g}')
    frame = tk.Frame(dialog)
    frame.pack(padx=22, pady=20)
    tk.Label(frame, text='Soundtrack', font=(theme.FONT, 16, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w')
    tk.Label(frame, text='One pad: play → pause → resume. Press it again to toggle.', fg=theme.MUTED).grid(row=1, column=0, columnspan=3, sticky='w', pady=(6, 18))
    tk.Label(frame, text='Audio file').grid(row=2, column=0, sticky='w')
    tk.Entry(frame, textvariable=filename, width=38, bg=theme.FIELD).grid(row=3, column=0, columnspan=2, sticky='ew', pady=(6, 18), ipady=6)

    def browse():
        path = filedialog.askopenfilename(parent=dialog, title='Choose a soundtrack',
                                         filetypes=[('Audio', '*.wav *.ogg *.mp3 *.flac'), ('All files', '*')])
        if path:
            try:
                filename.set(import_file(path, user_path))
            except OSError as error:
                messagebox.showerror('Could not import audio', str(error), parent=dialog)

    theme.button(frame, 'Browse', browse).grid(row=3, column=2, padx=(10, 0), pady=(6, 18))
    for row, label, variable, maximum, step in (
        (4, 'Volume (%)', volume, 100, 1),
        (5, 'Play / resume fade-in (s)', fade_in, 3600, 0.1),
        (6, 'Pause fade-out (s)', pause_fade, 3600, 0.1),
        (7, 'Stop / end fade-out (s)', fade_out, 3600, 0.1),
    ):
        tk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=6)
        tk.Spinbox(frame, textvariable=variable, from_=0, to=maximum, increment=step,
                   width=10, bg=theme.FIELD, buttonbackground=theme.BUTTON,
                   insertbackground=theme.TEXT).grid(row=row, column=1, sticky='e', pady=6, ipady=5)
    tk.Label(frame, text='Pausing keeps the track at the position reached after its fade.',
             fg=theme.MUTED, justify='left').grid(row=8, column=0, columnspan=3, sticky='w', pady=(14, 4))
    tk.Label(frame, text='Applying replaces the script in this editor. Bind the pad to save it.',
             fg=theme.MUTED, justify='left').grid(row=9, column=0, columnspan=3, sticky='w', pady=(0, 18))

    def apply():
        try:
            line = track_commands.build(filename.get().strip(), float(volume.get()),
                                        round(float(fade_in.get()) * 1000), round(float(fade_out.get()) * 1000),
                                        round(float(pause_fade.get()) * 1000))
            path, *_ = track_commands.parse(line)
            if not Path(sound.full_name(path)).is_file() or not sound.is_valid(path):
                raise ValueError('Choose an audio file that can be opened. Browse copies it into user_sounds.')
            text_widget.delete('1.0', 'end')
            text_widget.insert('1.0', line)
            dialog.destroy()
        except (ValueError, OverflowError, OSError) as error:
            messagebox.showerror('Check soundtrack settings', str(error), parent=dialog)

    theme.button(frame, 'Apply to script', apply, primary=True).grid(row=10, column=1, columnspan=2, sticky='e')
    theme.button(frame, 'Cancel', dialog.destroy).grid(row=10, column=0, sticky='w')
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.wait_window()
    if parent.winfo_exists():
        parent.grab_set()
