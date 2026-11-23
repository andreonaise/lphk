"""Select input without importing X11 libraries in a Wayland session."""
import os
import sys


def select_backend(platform=None, environ=None):
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    requested = environ.get("LPHK_INPUT_BACKEND", "auto").lower()
    if requested not in ("auto", "windows", "x11", "wayland"):
        raise RuntimeError("LPHK_INPUT_BACKEND must be auto, windows, x11, or wayland")
    if requested != "auto":
        if (requested == "windows") != (platform == "win32"):
            raise RuntimeError("The selected input backend does not match this operating system")
        return requested
    if platform == "win32":
        return "windows"
    if platform.startswith("linux") and (
        environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        or environ.get("WAYLAND_DISPLAY")
    ):
        return "wayland"
    return "x11"


BACKEND = select_backend()
