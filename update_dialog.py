"""Nonblocking public GitHub update check, download, and restart dialog."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox
import sys
from pathlib import Path
import app_settings
import app_updater
import ui_theme as theme


def open_dialog(app):
    dialog = tk.Toplevel(app)
    dialog.title('Update LPHK')
    dialog.resizable(False, False)
    frame = tk.Frame(dialog)
    frame.pack(padx=22, pady=20)
    tk.Label(frame, text='Update LPHK', font=(theme.FONT, 17, 'bold')).pack(anchor='w')
    tk.Label(frame, text=f'Installed version: {app.version}', fg=theme.MUTED).pack(anchor='w', pady=(6, 16))
    repository = tk.StringVar(value=app.settings['update_repository'])
    tk.Label(frame, text='GitHub repository').pack(anchor='w')
    tk.Entry(frame, textvariable=repository, width=52, bg=theme.FIELD).pack(fill='x', pady=(6, 12), ipady=6)
    status = tk.StringVar(value='Check the latest published release. Drafts and Actions artifacts are excluded.')
    tk.Label(frame, textvariable=status, wraplength=430, justify='left', fg=theme.MUTED).pack(anchor='w', pady=(0, 14))
    messages = queue.Queue()
    release = {'value': None}

    def work(operation):
        try:
            messages.put(('ok', operation()))
        except Exception as error:
            messages.put(('error', str(error)))

    def check():
        try:
            app.settings['update_repository'] = app_updater.repository_name(repository.get())
            app_settings.save(app.user_path, app.settings)
        except (ValueError, OSError) as error:
            status.set(str(error))
            return
        check_button.configure(state='disabled')
        status.set('Checking GitHub…')
        target_repository = repository.get()
        threading.Thread(target=work, args=(lambda: ('release', app_updater.latest(target_repository, app.version)),), daemon=True).start()

    def download():
        if not getattr(sys, 'frozen', False):
            status.set('Automatic installation is available in prebuilt app downloads. Update your source checkout using Git.')
            return
        install_button.configure(state='disabled')
        status.set('Downloading and verifying the update…')
        threading.Thread(target=work, args=(lambda: ('staged', app_updater.stage(release['value'], app.user_path)),), daemon=True).start()

    def poll():
        try:
            kind, result = messages.get_nowait()
            check_button.configure(state='normal')
            if kind == 'error':
                status.set(result)
            elif result[0] == 'release':
                release['value'] = result[1]
                if result[1] is None:
                    status.set('You are up to date.')
                else:
                    status.set(f"Version {result[1]['version']} is available. Your layouts, pages, scripts, sounds, and settings will be kept.")
                    install_button.configure(state='normal')
            else:
                if messagebox.askyesno('Install update', 'The download is verified. Close LPHK and install it now?', parent=dialog):
                    import files
                    if files.layout_changed_since_load:
                        answer = messagebox.askyesnocancel('Save layout', 'Save the current layout and its pages before updating?', parent=dialog)
                        if answer is None:
                            dialog.after(100, poll)
                            return
                        if answer:
                            app.save_layout()
                            if files.layout_changed_since_load:
                                dialog.after(100, poll)
                                return
                    app_updater.launch_install(result[1], Path(sys.executable).parent, app.user_path)
                    files.layout_changed_since_load = False
                    import window
                    window.close()
                    return
                status.set('Update downloaded. Check again when you are ready to install.')
        except queue.Empty:
            pass
        except (OSError, ValueError, RuntimeError) as error:
            status.set(f'Could not install the update: {error}')
        if dialog.winfo_exists():
            dialog.after(100, poll)

    check_button = theme.button(frame, 'Check for updates', check, primary=True)
    check_button.pack(side='left')
    install_button = theme.button(frame, 'Download and install', download, state='disabled')
    install_button.pack(side='left', padx=8)
    dialog.after(100, poll)
    return dialog
