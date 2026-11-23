"""Read-only installation diagnostics; no keyboard/mouse events are emitted."""
import os
import sys
from input_backend import BACKEND


def main():
    print("LPHK input backend:", BACKEND)
    if BACKEND == "wayland":
        from system_apis.input_wayland import controller
        print(controller.check())
        if not os.environ.get("DISPLAY"):
            raise RuntimeError("Macro input is native Wayland, but the Tk interface needs XWayland ($DISPLAY). Install xorg-xwayland and enable it in MangoWM.")
    print("System check passed.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print("[LPHK]", error, file=sys.stderr)
        sys.exit(1)
