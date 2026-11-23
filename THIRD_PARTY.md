# Third-party components

Release archives contain Python and libraries collected by PyInstaller.
Their license files are copied into `third-party-licenses/`. The LPHK license
does not replace the licenses of those components.

| Component | Source / project | Notes |
| --- | --- | --- |
| Python | https://www.python.org/ | Python license included in the archive. |
| Tcl/Tk | https://www.tcl.tk/ | GUI runtime included by PyInstaller. |
| Pillow | https://github.com/python-pillow/Pillow | Image handling. |
| pygame / SDL | https://github.com/pygame/pygame | MIDI and audio. |
| pynput | https://github.com/moses-palmer/pynput | Windows/X11 mouse and X11 keyboard input. |
| PyAutoGUI and dependencies | https://github.com/asweigart/pyautogui | Windows text input. |
| tkcolorpicker | https://github.com/j4321/tkColorPicker | Existing colour picker. |
| launchpad.py | https://github.com/FMMT666/launchpad.py | Pinned in requirements.txt. |
| PyInstaller | https://github.com/pyinstaller/pyinstaller | Its bootloader distribution exception applies. |

Linux releases additionally bundle these separate helper programs:

- **ydotool / ydotoold**, AGPL-3.0-or-later, revision
  `57ba7d0af525e82da2de0e275d169477f293b197` (v1.0.4):
  https://github.com/ReimuNotMoe/ydotool
- **wtype**, MIT, revision `4b9cc29664f178cf380ccfe7f98405d38dffda3c`:
  https://github.com/atx/wtype

Their complete source archives, including their license files, are shipped in
the Linux archive's `third-party-sources/` directory. The build commands and
immutable source revisions are in `release_tools/build_linux_helpers.py`.
Associated Wayland and xkbcommon shared libraries are collected by PyInstaller.
System components such as the Linux kernel, display server, desktop compositor,
and device drivers are provided by the user's operating system.
