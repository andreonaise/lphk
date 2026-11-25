"""Searchable syntax/examples for every command accepted by the script engine."""
import tkinter as tk
from tkinter import ttk
import ui_theme as theme

# name: (category, syntax, explanation, insertable example)
COMMANDS = {
    '@ASYNC': ('Scheduling', '@ASYNC', 'First line: run this script in the background.', '@ASYNC\nSOUND_PAUSE'),
    '@SIMPLE': ('Keyboard', '@SIMPLE key', 'Hold a key while its Launchpad pad or demo mouse button is held.', '@SIMPLE a'),
    '@LOAD_LAYOUT': ('Layouts', '@LOAD_LAYOUT filename', 'First line: load a layout from user_layouts.', '@LOAD_LAYOUT examples/default.lpl'),
    'STRING': ('Keyboard', 'STRING text', 'Type the text following the command.', 'STRING hello'),
    'DELAY': ('Scheduling', 'DELAY seconds', 'Wait. The unit is seconds, including fractional values.', 'DELAY 0.5'),
    'TAP': ('Keyboard', 'TAP key [count] [hold_seconds]', 'Press and release a key, optionally repeating it.', 'TAP space'),
    'PRESS': ('Keyboard', 'PRESS key', 'Hold a key until RELEASE or RELEASE_ALL.', 'PRESS ctrl'),
    'RELEASE': ('Keyboard', 'RELEASE key', 'Release a held key.', 'RELEASE ctrl'),
    'RELEASE_ALL': ('Keyboard', 'RELEASE_ALL', 'Release all keys held by scripts.', 'RELEASE_ALL'),
    'WEB': ('Files', 'WEB URL', 'Open a website in your browser.', 'WEB https://example.com'),
    'WEB_NEW': ('Files', 'WEB_NEW URL', 'Ask the browser to open a new window.', 'WEB_NEW https://example.com'),
    'CODE': ('Files', 'CODE program', 'Run an external program. Use an executable path; OS-specific commands need adapting.', 'CODE /usr/bin/true'),
    'OPEN': ('Files', 'OPEN path', 'Open a file or folder with its default application.', 'OPEN user_sounds'),
    'SOUND': ('Audio', 'SOUND filename [volume]', 'Play a one-shot effect from user_sounds. Volume is 0–100.', 'SOUND examples/airhorn.wav 80'),
    'SOUND_TRACK': ('Audio', 'SOUND_TRACK "filename" [volume] [play_fade_ms] [stop_fade_ms] [pause_fade_ms]', 'One pad toggles play/pause/resume. Fades are milliseconds. Pause preserves the playhead. Track files are relative to user_sounds.', 'SOUND_TRACK examples/demo_track.wav 80 1500 2000 500'),
    'SOUND_PAUSE': ('Audio', 'SOUND_PAUSE [fade_ms]', 'Pause all soundtrack pads, on every page. Omit fade_ms to use each track’s pause fade.', 'SOUND_PAUSE'),
    'SOUND_RESUME': ('Audio', 'SOUND_RESUME [fade_ms]', 'Continue paused soundtracks at their saved positions. Uses each play fade unless overridden.', 'SOUND_RESUME'),
    'SOUND_STOP': ('Audio', 'SOUND_STOP [fade_ms]', 'Stop all audio. A later play starts from the beginning. Optional fade is milliseconds.', 'SOUND_STOP 1000'),
    'SOUND_SKIP': ('Audio', 'SOUND_SKIP seconds [pad_x pad_y]', 'Skip forward or backward. Without coordinates, affects all active tracks. With coordinates, targets that pad on this page. Paused tracks stay paused.', 'SOUND_SKIP 10 0 1'),
    'SOUND_SEEK': ('Audio', 'SOUND_SEEK seconds [pad_x pad_y]', 'Jump to an absolute time, in seconds. Optional pad coordinates target this page; otherwise affects all active tracks.', 'SOUND_SEEK 30 0 1'),
    'WAIT_UNPRESSED': ('Scheduling', 'WAIT_UNPRESSED', 'Wait until this pad is released.', 'WAIT_UNPRESSED'),
    'M_MOVE': ('Mouse', 'M_MOVE dx dy', 'Move the pointer relative to its current position.', 'M_MOVE 20 0'),
    'M_SET': ('Mouse', 'M_SET x y', 'Move the pointer to screen coordinates.', 'M_SET 400 300'),
    'M_SCROLL': ('Mouse', 'M_SCROLL vertical [horizontal]', 'Scroll the wheel; negative values reverse direction.', 'M_SCROLL -3'),
    'M_LINE': ('Mouse', 'M_LINE x1 y1 x2 y2 [delay_ms] [step_pixels]', 'Move along a line between two screen points.', 'M_LINE 100 100 300 100 5 2'),
    'M_LINE_MOVE': ('Mouse', 'M_LINE_MOVE dx dy [delay_ms] [step_pixels]', 'Move along a line relative to the current pointer.', 'M_LINE_MOVE 100 0 5 2'),
    'M_LINE_SET': ('Mouse', 'M_LINE_SET x y [delay_ms] [step_pixels]', 'Move in a line to an absolute point.', 'M_LINE_SET 400 300 5 2'),
    'M_STORE': ('Mouse', 'M_STORE', 'Remember the current pointer location in this script.', 'M_STORE'),
    'M_RECALL': ('Mouse', 'M_RECALL', 'Return to the location saved by M_STORE.', 'M_RECALL'),
    'M_RECALL_LINE': ('Mouse', 'M_RECALL_LINE [delay_ms] [step_pixels]', 'Return to the stored pointer location along a line.', 'M_RECALL_LINE 5 2'),
    'LABEL': ('Flow', 'LABEL name', 'Define a jump/repeat label.', 'LABEL start\nDELAY 1'),
    'GOTO_LABEL': ('Flow', 'GOTO_LABEL name', 'Jump to a label in this script.', 'LABEL start\nDELAY 1\nGOTO_LABEL start'),
    'IF_PRESSED_GOTO_LABEL': ('Flow', 'IF_PRESSED_GOTO_LABEL name', 'Jump if this pad is still held.', 'LABEL start\nDELAY 0.1\nIF_PRESSED_GOTO_LABEL start'),
    'IF_UNPRESSED_GOTO_LABEL': ('Flow', 'IF_UNPRESSED_GOTO_LABEL name', 'Jump if this pad is released.', 'LABEL start\nDELAY 0.1\nIF_UNPRESSED_GOTO_LABEL start'),
    'REPEAT_LABEL': ('Flow', 'REPEAT_LABEL name count', 'Repeat a label a limited number of times.', 'LABEL start\nDELAY 0.2\nREPEAT_LABEL start 3'),
    'IF_PRESSED_REPEAT_LABEL': ('Flow', 'IF_PRESSED_REPEAT_LABEL name count', 'Repeat while the pad is held, up to count times.', 'LABEL start\nDELAY 0.1\nIF_PRESSED_REPEAT_LABEL start 3'),
    'IF_UNPRESSED_REPEAT_LABEL': ('Flow', 'IF_UNPRESSED_REPEAT_LABEL name count', 'Repeat while released, up to count times.', 'LABEL start\nDELAY 0.1\nIF_UNPRESSED_REPEAT_LABEL start 3'),
    'RESET_REPEATS': ('Flow', 'RESET_REPEATS', 'Reset this script’s repeat counters.', 'RESET_REPEATS'),
    'PAGE': ('Pages', 'PAGE name_or_number', 'Switch to a page by name or 1-based number. Background tracks keep playing.', 'PAGE 2'),
    'PAGE_NEXT': ('Pages', 'PAGE_NEXT', 'Switch to the next page, wrapping at the end.', 'PAGE_NEXT'),
    'PAGE_PREV': ('Pages', 'PAGE_PREV', 'Switch to the previous page.', 'PAGE_PREV'),
}


def search(query):
    query = query.casefold().strip()
    return [name for name, entry in COMMANDS.items() if query in ' '.join((name, *entry)).casefold()]


def open_guide(parent, editor=None):
    dialog = tk.Toplevel(parent)
    dialog.title('Command guide')
    dialog.geometry('820x590')
    query = tk.StringVar()
    tk.Label(dialog, text='Command guide', font=(theme.FONT, 17, 'bold')).pack(anchor='w', padx=20, pady=(18, 8))
    tk.Label(dialog, text='Search a command or action, such as pause, skip, mouse, or page.', fg=theme.MUTED).pack(anchor='w', padx=20)
    entry = tk.Entry(dialog, textvariable=query, bg=theme.FIELD, insertbackground=theme.TEXT)
    entry.pack(fill='x', padx=20, pady=12, ipady=7)
    body = tk.Frame(dialog)
    body.pack(fill='both', expand=True, padx=20)
    listing = tk.Listbox(body, width=27, bg=theme.PANEL, bd=0, exportselection=False, selectbackground=theme.ACCENT_BG)
    listing.pack(side='left', fill='y', padx=(0, 14))
    details = tk.scrolledtext.ScrolledText(body, width=52, height=18, wrap='word', font='TkFixedFont', padx=12, pady=12)
    theme.dark_scrollbar(details)
    details.pack(side='left', fill='both', expand=True)

    def chosen():
        return listing.get(listing.curselection()[0]) if listing.curselection() else None

    def select(event=None):
        name = chosen()
        details.configure(state='normal')
        details.delete('1.0', 'end')
        if name:
            category, syntax, explanation, example = COMMANDS[name]
            details.insert('1.0', f'{category}\n\n{syntax}\n\n{explanation}\n\nExample\n\n{example}')
        details.configure(state='disabled')

    def filter_items(*args):
        listing.delete(0, 'end')
        for name in search(query.get()):
            listing.insert('end', name)
        if listing.size():
            listing.selection_set(0)
        select()

    def copy():
        if chosen():
            dialog.clipboard_clear()
            dialog.clipboard_append(COMMANDS[chosen()][3])

    def insert():
        if chosen() and editor is not None and editor.winfo_exists():
            editor.insert('insert', COMMANDS[chosen()][3] + '\n')
            dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.pack(fill='x', padx=20, pady=16)
    theme.button(buttons, 'Copy example', copy).pack(side='left')
    if editor is not None:
        theme.button(buttons, 'Insert example', insert, primary=True).pack(side='left', padx=8)
    theme.button(buttons, 'Close', dialog.destroy).pack(side='right')
    listing.bind('<<ListboxSelect>>', select)
    query.trace_add('write', filter_items)
    filter_items()
    entry.focus_set()
    return dialog
