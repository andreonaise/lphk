"""Form-based action sequences; no script syntax is needed to create a binding."""
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import script_builder as model
import command_guide
import page_state
import soundtrack_ui
import ui_theme as theme


class Builder:
    def __init__(self, parent, editor, user_path):
        self.editor, self.user_path = editor, Path(user_path)
        self.lines = editor.get('1.0', 'end-1c').split('\n')
        if self.lines == ['']:
            self.lines = []
        self.window = tk.Toplevel(parent)
        self.window.title('Build actions')
        self.window.geometry('880x600')
        self.window.minsize(680, 480)
        self.window.transient(parent)
        self.previous_grab = parent.grab_current()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(2, weight=1)
        tk.Label(self.window, text='Build actions', font=(theme.FONT, 18, 'bold')).grid(row=0, column=0, sticky='w', padx=20, pady=(18, 6))
        tk.Label(self.window, text='Add actions, fill in their settings, then arrange them in the order they should run.',
                 fg=theme.MUTED, wraplength=780, justify='left').grid(row=1, column=0, sticky='w', padx=20, pady=(0, 12))
        frame = tk.Frame(self.window)
        frame.grid(row=2, column=0, sticky='nsew', padx=20)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.listing = tk.Listbox(frame, bg=theme.PANEL, fg=theme.TEXT, selectbackground=theme.ACCENT_BG,
                                  exportselection=False, activestyle='none', font=(theme.FONT, 11))
        self.listing.grid(row=0, column=0, sticky='nsew')
        scrollbar = tk.Scrollbar(frame, command=self.listing.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.listing.configure(yscrollcommand=scrollbar.set)
        buttons = tk.Frame(frame)
        buttons.grid(row=0, column=2, sticky='ns', padx=(12, 0))
        for title, action in [('Add action…', self.add), ('Keyboard shortcut…', self.add_shortcut), ('Edit settings…', self.edit),
                              ('Duplicate', self.duplicate), ('Move up', lambda: self.move(-1)),
                              ('Move down', lambda: self.move(1)), ('Remove', self.remove)]:
            theme.button(buttons, title, action).pack(fill='x', pady=(0, 8))
        self.listing.bind('<Double-Button-1>', lambda event: self.edit())
        self.listing.bind('<Delete>', lambda event: self.remove())
        self.note = tk.Label(self.window, text='Original lines stay unchanged until you edit or remove them.', fg=theme.MUTED, anchor='w')
        self.note.grid(row=3, column=0, sticky='ew', padx=20, pady=12)
        footer = tk.Frame(self.window)
        footer.grid(row=4, column=0, sticky='ew', padx=20, pady=(0, 18))
        theme.button(footer, 'Cancel', self.close).pack(side='right')
        theme.button(footer, 'Apply to pad editor', self.apply, primary=True).pack(side='right', padx=8)
        tk.Label(footer, text='Then use Bind Button to save the pad.', fg=theme.MUTED).pack(side='left')
        self.refresh()
        self.window.grab_set()

    def index(self):
        selected = self.listing.curselection()
        return selected[0] if selected else None

    def refresh(self, select=None):
        self.listing.delete(0, 'end')
        for i, line in enumerate(self.lines):
            self.listing.insert('end', f'{i + 1}.  {model.describe(line)}')
        if select is not None and self.lines:
            select = min(select, len(self.lines) - 1)
            self.listing.selection_set(select)
            self.listing.see(select)

    def insert(self, line):
        index = self.index()
        index = len(self.lines) if index is None else index + 1
        if line.startswith('@'):
            index = 0
        self.lines.insert(index, line)
        self.refresh(index)

    def add(self):
        return self.form(None)

    def edit(self):
        index = self.index()
        if index is None:
            return
        if model.parse(self.lines[index]) is None:
            messagebox.showinfo('Original line', 'This line is kept exactly as written. Edit it in the text editor, or remove it and add a new action.', parent=self.window)
            return
        return self.form(index)

    def duplicate(self):
        index = self.index()
        if index is not None:
            self.lines.insert(index + 1, self.lines[index])
            self.refresh(index + 1)

    def remove(self):
        index = self.index()
        if index is not None:
            self.lines.pop(index)
            self.refresh(index)

    def move(self, direction):
        index = self.index()
        if index is not None and 0 <= index + direction < len(self.lines):
            self.lines[index], self.lines[index + direction] = self.lines[index + direction], self.lines[index]
            self.refresh(index + direction)

    def close(self):
        self.window.destroy()
        if self.previous_grab is not None and self.previous_grab.winfo_exists():
            self.previous_grab.grab_set()

    def apply(self):
        try:
            model.validate_sequence(self.lines)
        except ValueError as error:
            messagebox.showerror('Check the action sequence', str(error), parent=self.window)
            return False
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', '\n'.join(self.lines))
        self.close()
        return True

    def choices(self, kind):
        if kind == 'key':
            return model.KEYS
        if kind == 'page':
            return [page['name'] for page in page_state.book.pages]
        if kind == 'label':
            return [line.strip().partition(' ')[2] for line in self.lines if line.strip().startswith('LABEL ')]
        if kind in ('sound', 'soundtrack', 'layout'):
            folder = self.user_path / ('user_layouts' if kind == 'layout' else 'user_sounds')
            return sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()) if folder.exists() else []
        return []

    def browse(self, field, variable, parent):
        kind = field['kind']
        path = filedialog.askopenfilename(parent=parent, title=field['label'],
                    initialdir=self.user_path / ('user_layouts' if kind == 'layout' else 'user_sounds'),
                    filetypes=[('Layout', '*.lpl')] if kind == 'layout' else [('All files', '*')])
        if not path:
            return
        try:
            if kind in ('sound', 'soundtrack'):
                relative = soundtrack_ui.import_file(path, self.user_path)
                if kind == 'sound' and any(c.isspace() for c in relative):
                    source = self.user_path / 'user_sounds' / relative
                    name = '_'.join(source.stem.split())
                    destination = self.user_path / 'user_sounds' / (name + source.suffix)
                    index = 2
                    while destination.exists():
                        destination = self.user_path / 'user_sounds' / f'{name}-{index}{source.suffix}'
                        index += 1
                    shutil.copy2(source, destination)
                    relative = destination.name
                variable.set(relative)
            elif kind == 'layout':
                folder = (self.user_path / 'user_layouts').resolve()
                source = Path(path).resolve()
                if not source.is_relative_to(folder):
                    raise ValueError('Choose a layout inside user_layouts. Copy it there before selecting it.')
                variable.set(source.relative_to(folder).as_posix())
            else:
                variable.set(path)
        except (OSError, ValueError) as error:
            messagebox.showerror('Could not select file', str(error), parent=parent)

    def form(self, index):
        parsed = model.parse(self.lines[index]) if index is not None else None
        dialog = tk.Toplevel(self.window)
        dialog.title('Action settings')
        dialog.transient(self.window)
        dialog.geometry('700x650')
        dialog.minsize(600, 550)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(3, weight=1)
        tk.Label(dialog, text='Choose an action', font=(theme.FONT, 16, 'bold')).grid(row=0, column=0, sticky='w', padx=20, pady=(18, 10))
        names = list(model.FORMS)
        labels = [(command_guide.COMMANDS[name][0] if name in command_guide.COMMANDS else 'Notes') + ' / ' + model.FORMS[name][0] for name in names]
        selector = ttk.Combobox(dialog, values=labels, state='readonly', width=72)
        selector.grid(row=1, column=0, sticky='ew', padx=20)
        description = tk.Label(dialog, text='', fg=theme.MUTED, wraplength=640, justify='left')
        description.grid(row=2, column=0, sticky='ew', padx=20, pady=12)
        controls = tk.Frame(dialog)
        controls.grid(row=3, column=0, sticky='new', padx=20)
        controls.columnconfigure(1, weight=1)
        variables = {}

        def render(values=None):
            for child in controls.winfo_children():
                child.destroy()
            variables.clear()
            name = names[selector.current()]
            description.configure(text=model.form_description(command_guide.COMMANDS[name][2]) if name in command_guide.COMMANDS else 'A note for yourself. This action does not run anything.')
            for row, f in enumerate(model.FORMS[name][1]):
                tk.Label(controls, text=f['label'], wraplength=260, justify='left').grid(row=row, column=0, sticky='w', pady=8, padx=(0, 12))
                value = tk.StringVar(value=(values or {}).get(f['name'], f['default']))
                initial_value = value.get()
                variables[f['name']] = value
                if f['kind'] in ('number', 'integer'):
                    entry = tk.Spinbox(controls, textvariable=value, from_=f['minimum'], to=f['maximum'],
                                       increment=1 if f['kind'] == 'integer' else .1, bg=theme.FIELD,
                                       buttonbackground=theme.BUTTON, insertbackground=theme.TEXT)
                elif f['kind'] in ('key', 'page', 'label', 'sound', 'soundtrack', 'layout'):
                    entry = ttk.Combobox(controls, textvariable=value, values=self.choices(f['kind']))
                else:
                    entry = tk.Entry(controls, textvariable=value, bg=theme.FIELD, insertbackground=theme.TEXT)
                entry.grid(row=row, column=1, sticky='ew', pady=8, ipady=5)
                # Tk Spinbox fills an empty variable with its minimum on creation.
                # Empty optional values must remain empty to retain engine defaults.
                value.set(initial_value)
                if f['kind'] in ('sound', 'soundtrack', 'file', 'program', 'layout'):
                    theme.button(controls, 'Browse…', lambda f=f, v=value: self.browse(f, v, dialog)).grid(row=row, column=2, padx=(8, 0))
                    if f['kind'] == 'file':
                        def folder(variable=value):
                            path = filedialog.askdirectory(parent=dialog, title='Choose a folder')
                            if path:
                                variable.set(path)
                        theme.button(controls, 'Folder…', folder).grid(row=row, column=3, padx=(4, 0))
            if not variables:
                tk.Label(controls, text='No settings needed for this action.', fg=theme.MUTED).grid(row=0, column=0, pady=12)

        def done():
            try:
                line = model.build(names[selector.current()], {k: v.get() for k, v in variables.items()})
                if index is None:
                    self.insert(line)
                else:
                    self.lines[index] = line
                    self.refresh(index)
                dialog.destroy()
                self.window.grab_set()
            except ValueError as error:
                messagebox.showerror('Check action settings', str(error), parent=dialog)

        def cancel():
            dialog.destroy()
            self.window.grab_set()
        dialog.protocol('WM_DELETE_WINDOW', cancel)
        footer = tk.Frame(dialog)
        footer.grid(row=4, column=0, sticky='ew', padx=20, pady=18)
        tk.Label(footer, text='Blank optional settings use the command’s defaults.', fg=theme.MUTED).pack(anchor='w', pady=(0, 10))
        theme.button(footer, 'Cancel', cancel).pack(side='right')
        theme.button(footer, 'Add action' if index is None else 'Save settings', done, primary=True).pack(side='right', padx=8)
        selector.bind('<<ComboboxSelected>>', lambda event: render())
        selector.current(names.index(parsed[0]) if parsed else names.index('TAP'))
        render(parsed[1] if parsed else None)
        # Expose actual form controls for functional GUI verification.
        dialog.selector, dialog.variables, dialog.render, dialog.submit = selector, variables, render, done
        dialog.grab_set()
        return dialog

    def add_shortcut(self):
        dialog = tk.Toplevel(self.window)
        dialog.title('Keyboard shortcut')
        dialog.transient(self.window)
        frame = tk.Frame(dialog)
        frame.pack(padx=22, pady=20)
        tk.Label(frame, text='Hold modifiers, tap a key, then release them.', fg=theme.MUTED).pack(anchor='w', pady=(0, 12))
        modifiers = {}
        for name in ('ctrl', 'alt', 'shift', 'cmd'):
            value = tk.BooleanVar(value=name == 'ctrl')
            modifiers[name] = value
            tk.Checkbutton(frame, text=name, variable=value, selectcolor=theme.FIELD).pack(anchor='w')
        chosen = tk.StringVar(value='c')
        ttk.Combobox(frame, values=model.KEYS, textvariable=chosen).pack(fill='x', pady=12)
        def done():
            try:
                lines = model.shortcut(chosen.get(), [name for name, value in modifiers.items() if value.get()])
                index = self.index()
                index = len(self.lines) if index is None else index + 1
                self.lines[index:index] = lines
                self.refresh(index)
                dialog.destroy()
                self.window.grab_set()
            except ValueError as error:
                messagebox.showerror('Check shortcut', str(error), parent=dialog)
        theme.button(frame, 'Add shortcut', done, primary=True).pack(side='right')
        dialog.protocol('WM_DELETE_WINDOW', lambda: (dialog.destroy(), self.window.grab_set()))
        dialog.grab_set()
        return dialog


def open_builder(parent, editor, user_path):
    return Builder(parent, editor, user_path)
