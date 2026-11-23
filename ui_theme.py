"""Shared dark palette for the existing Tk interface."""
import sys
import tkinter as tk
from tkinter import font, ttk

BG = '#17191c'
PANEL = '#1e2125'
FIELD = '#121417'
BORDER = '#353a41'
TEXT = '#e5e7eb'
MUTED = '#989fa9'
BUTTON = '#2b3036'
HOVER = '#393f47'
ACCENT = '#abc7b2'
ACCENT_BG = '#2b4133'
DANGER = '#d0a3a3'
FONT = 'Segoe UI' if sys.platform == 'win32' else 'DejaVu Sans'
MONO = 'Consolas' if sys.platform == 'win32' else 'DejaVu Sans Mono'


def apply(root):
    family = FONT
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont'):
        font.nametofont(name).configure(family=family, size=10)
    font.nametofont('TkFixedFont').configure(
        family='Consolas' if sys.platform == 'win32' else 'DejaVu Sans Mono', size=11)
    for option, value in {
        '*background': BG, '*foreground': TEXT,
        '*activeBackground': HOVER, '*activeForeground': TEXT,
        '*selectBackground': ACCENT_BG, '*selectForeground': TEXT,
        '*disabledForeground': '#666d76', '*highlightBackground': BORDER,
        '*highlightColor': ACCENT, '*insertBackground': TEXT,
        '*Button.background': BUTTON, '*Button.relief': 'flat',
        '*Button.borderWidth': 0, '*Button.padX': 14, '*Button.padY': 9,
        '*Button.cursor': 'hand2', '*Button.highlightThickness': 1,
        '*Text.background': FIELD, '*Text.relief': 'flat',
        '*Text.borderWidth': 0, '*Text.highlightThickness': 1,
        '*Entry.background': FIELD, '*Entry.relief': 'flat',
        '*Menu.background': PANEL, '*Menu.borderWidth': 0,
        '*Canvas.background': PANEL, '*Canvas.highlightThickness': 0,
        '*Scrollbar.background': BUTTON, '*Scrollbar.troughColor': FIELD,
        '*Scrollbar.relief': 'flat', '*Toplevel.background': BG,
    }.items():
        root.option_add(option, value)
    root.configure(background=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=BG, foreground=TEXT, bordercolor=BORDER,
                    fieldbackground=FIELD, troughcolor=FIELD, selectbackground=ACCENT_BG)
    style.configure('TButton', padding=(12, 8), background=BUTTON, foreground=TEXT)
    style.map('TButton', background=[('active', HOVER)], foreground=[('disabled', MUTED)])
    style.configure('TEntry', insertcolor=TEXT, fieldbackground=FIELD)
    style.configure('TCombobox', fieldbackground=FIELD, background=BUTTON, arrowcolor=TEXT)
    style.map('TCombobox', fieldbackground=[('readonly', FIELD)], foreground=[('readonly', TEXT)])
    style.configure('TNotebook.Tab', padding=(10, 6))
    style.layout('LPHK.Vertical.TScrollbar', [
        ('Vertical.Scrollbar.trough', {'sticky': 'ns', 'children': [
            ('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})]})])
    style.configure('LPHK.Vertical.TScrollbar', background=BUTTON, troughcolor=FIELD,
                    arrowcolor=MUTED, bordercolor=FIELD, lightcolor=BUTTON, darkcolor=BUTTON)
    style.map('LPHK.Vertical.TScrollbar', background=[('active', HOVER)])
    style.map('TNotebook.Tab', background=[('selected', BUTTON)])
    root.bind_class('Toplevel', '<Map>', lambda event: dark_titlebar(event.widget), add='+')
    root.after(0, lambda: dark_titlebar(root))


def dark_titlebar(window):
    if sys.platform != 'win32' or not isinstance(window, (tk.Tk, tk.Toplevel)):
        return
    try:
        import ctypes
        window.update_idletasks()
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        handle = user32.GetParent(window.winfo_id())
        enabled = ctypes.c_int(1)
        set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        set_attribute(handle, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
    except (OSError, AttributeError, tk.TclError):
        pass


def pad_color(color):
    # Off pads remain distinguishable from the chassis. Hardware RGB is untouched.
    return '#292e34' if color.lower() == '#000000' else color


def button(parent, text, command, primary=False, **kwargs):
    widget = tk.Button(parent, text=text, command=command, **kwargs)
    if primary:
        widget.configure(background=ACCENT_BG, foreground=ACCENT,
                         activebackground='#36513f', activeforeground=TEXT)
    return widget


def dark_scrollbar(text):
    text.vbar.pack_forget()
    scrollbar = ttk.Scrollbar(text.frame, orient='vertical', command=text.yview,
                              style='LPHK.Vertical.TScrollbar')
    scrollbar.pack(side='right', fill='y')
    text.configure(yscrollcommand=scrollbar.set)
    text.dark_scrollbar = scrollbar
