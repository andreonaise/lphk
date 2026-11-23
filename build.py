"""Build a portable native app on Windows or Linux: python build.py."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onedir", "--name", "LPHK", "--hidden-import", "PIL._tkinter_finder"]
for name in ("VERSION", "README.md", "resources", "docs", "user_layouts", "user_scripts", "user_sounds"):
    destination = name if (root / name).is_dir() else "."
    args += ["--add-data", f"{name}{os.pathsep}{destination}"]
if sys.platform == "win32":
    args += ["--windowed", "--icon", "resources/LPHK.ico"]
elif sys.platform.startswith("linux"):
    # pynput imports these by name at runtime. Its discovery hook can return
    # nothing on a headless build machine, so list the X11 backends explicitly.
    for module in ("pynput.keyboard._xorg", "pynput.mouse._xorg", "pynput._util.xorg"):
        args += ["--hidden-import", module]
    # python-xlib also loads extension and keysym modules dynamically.
    args += ["--collect-submodules", "Xlib"]
    for name in ("ydotool", "ydotoold", "wtype"):
        helper = root / ".build-tools/bin" / name
        if not helper.is_file():
            raise SystemExit("Build the bundled input tools first: python release_tools/build_linux_helpers.py")
        args += ["--add-binary", f"{helper}{os.pathsep}tools"]
subprocess.run([*args, "LPHK.py"], cwd=root, check=True)
