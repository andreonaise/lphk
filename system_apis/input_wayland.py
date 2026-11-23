"""MangoWM input: persistent uinput via ydotoold; text via wtype.

All subprocesses use argument vectors, never a shell. Importing this module
does not connect to a display, create a virtual device, or generate input.
"""
import atexit
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import bundled_tools
import mango_ipc


# Linux evdev codes (not X11 keycodes or Windows virtual-key values).
KEYS = {
    "esc": 1, "backspace": 14, "tab": 15, "enter": 28, "space": 57,
    "ctrl": 29, "ctrl_l": 29, "ctrl_r": 97,
    "shift": 42, "shift_l": 42, "shift_r": 54,
    "alt": 56, "alt_l": 56, "alt_r": 100, "alt_gr": 100,
    "menu": 56, "menu_r": 100, "apps": 127,
    "cmd": 125, "cmd_l": 125, "cmd_r": 126,
    "win": 125, "win_l": 125, "win_r": 126, "super": 125,
    "caps_lock": 58, "num_lock": 69, "scroll_lock": 70,
    "home": 102, "up": 103, "page_up": 104, "left": 105,
    "right": 106, "end": 107, "down": 108, "page_down": 109,
    "insert": 110, "delete": 111, "print_screen": 99, "pause": 119,
    "mute": 113, "vol_down": 114, "vol_up": 115,
    "next_track": 163, "play_pause": 164, "prev_track": 165,
    "num0": 82, "num1": 79, "num2": 80, "num3": 81, "num4": 75,
    "num5": 76, "num6": 77, "num7": 71, "num8": 72, "num9": 73,
    "-": 12, "=": 13, "[": 26, "]": 27, ";": 39, "'": 40,
    "`": 41, "\\": 43, ",": 51, ".": 52, "/": 53,
    "+": 78, "*": 55, "clear": 355,
}
KEYS.update(zip("1234567890", range(2, 12)))
KEYS.update(zip("qwertyuiop", range(16, 26)))
KEYS.update(zip("asdfghjkl", range(30, 39)))
KEYS.update(zip("zxcvbnm", range(44, 51)))
KEYS.update({f"f{i}": 58 + i for i in range(1, 11)})
KEYS.update({"f11": 87, "f12": 88})
KEYS.update({f"f{i}": 170 + i for i in range(13, 25)})
BUTTONS = {"left": 0, "right": 1, "middle": 2}


def sp(name):
    return KEYS.get(name)


class WaylandInput:
    def __init__(self):
        self.lock = threading.RLock()
        self.held_keys = set()
        self.held_buttons = set()
        self.wheel_remainder = [0.0, 0.0]

    def environment(self):
        environment = os.environ.copy()
        # Respect users who already run their own ydotoold instance.
        if not environment.get("YDOTOOL_SOCKET") and hasattr(os, "getuid"):
            socket = Path(f"/run/lphk-ydotool-{os.getuid()}/socket")
            if socket.exists():
                environment["YDOTOOL_SOCKET"] = str(socket)
        return environment

    def run(self, program, *arguments, text=None, timeout=5):
        if program == "mmsg":
            return mango_ipc.request(" ".join(map(str, arguments)), timeout=timeout)
        executable = bundled_tools.command(program)
        command = [executable, *map(str, arguments)]
        try:
            result = subprocess.run(command, input=text, text=True, encoding="utf-8",
                                    capture_output=True, timeout=timeout,
                                    env=bundled_tools.external_environment(self.environment(), executable), check=False)
        except FileNotFoundError as error:
            raise RuntimeError(f"Missing {program}. Run bash SETUP_CACHYOS.sh; see CACHYOS_MANGOWM.txt.") from error
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError(f"{program} failed or timed out: {error}") from error
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            raise RuntimeError(f"{program}: {detail}. See CACHYOS_MANGOWM.txt.")
        return result.stdout

    def check(self):
        missing = [name for name in ("ydotool", "wtype") if bundled_tools.locate(name) is None]
        if missing:
            raise RuntimeError("Missing commands: " + ", ".join(missing) + ". Run bash SETUP_CACHYOS.sh.")
        # debug connects to the daemon without emitting input events.
        self.run("ydotool", "debug")
        position = self.get_pos()
        return f"Wayland input ready; MangoWM cursor at {position}. Text protocol is checked when typing."

    def press(self, key):
        if key not in KEYS.values():
            raise ValueError(f"Unsupported Linux key code: {key}")
        with self.lock:
            self.held_keys.add(key)
            self.run("ydotool", "key", "--key-delay", "0", f"{key}:1")

    def release(self, key):
        with self.lock:
            self.run("ydotool", "key", "--key-delay", "0", f"{key}:0")
            self.held_keys.discard(key)

    def write(self, text):
        # stdin keeps text (including '-' prefixes, quotes and Unicode) literal.
        # wtype's own keymap avoids dependence on the user's physical layout.
        with self.lock:
            self.run("wtype", "-", text=text, timeout=max(10, len(text) * 0.1))

    def get_pos(self):
        try:
            response = json.loads(self.run("mmsg", "get", "cursorpos"))
            x, y = float(response["x"]), float(response["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError("non-finite cursor position")
            return round(x), round(y)
        except (ValueError, KeyError, TypeError) as error:
            raise RuntimeError("MangoWM did not return a cursor position. Update MangoWM and start LPHK from a MangoWM terminal.") from error

    def move(self, x, y):
        x, y = round(x), round(y)
        if x or y:
            with self.lock:
                self.run("ydotool", "mousemove", "--", x, y)

    def set_pos(self, x, y):
        target = round(x), round(y)
        with self.lock:
            # Use compositor coordinates, including negative monitor offsets.
            # Never use ydotool's origin-reset approximation of absolute motion.
            gain = [1.0, 1.0]
            previous = None
            command = None
            for _ in range(12):
                current = self.get_pos()
                if current == target:
                    return
                if previous is not None:
                    for axis in (0, 1):
                        if command[axis]:
                            measured = (current[axis] - previous[axis]) / command[axis]
                            if measured > 0:
                                gain[axis] = max(0.05, min(20.0, measured))
                steps = []
                for axis in (0, 1):
                    offset = target[axis] - current[axis]
                    step = round(offset / gain[axis])
                    # An integer cursor offset needs at least one input unit.
                    if offset and not step:
                        step = 1 if offset > 0 else -1
                    steps.append(step)
                command = tuple(steps)
                self.move(*command)
                previous = current
                time.sleep(0.01)
            if self.get_pos() != target:
                raise RuntimeError("Pointer could not reach the requested position. Check the ydotoold device rule, monitor bounds, and pointer confinement; see CACHYOS_MANGOWM.txt.")

    def button(self, button, down):
        if button not in BUTTONS:
            raise ValueError(f"Unsupported mouse button: {button}")
        with self.lock:
            mask = (0x40 if down else 0x80) | BUTTONS[button]
            if down:
                self.held_buttons.add(button)
            self.run("ydotool", "click", "--next-delay", "0", hex(mask))
            if not down:
                self.held_buttons.discard(button)

    def click(self, button="left", clicks=1):
        with self.lock:
            for _ in range(clicks):
                self.button(button, True)
                self.button(button, False)

    def scroll(self, x, y):
        with self.lock:
            totals = [self.wheel_remainder[0] + x, self.wheel_remainder[1] + y]
            steps = [math.trunc(value) for value in totals]
            if any(steps):
                self.run("ydotool", "mousemove", "--wheel", "--", *steps)
            self.wheel_remainder = [value - step for value, step in zip(totals, steps)]

    def release_all(self):
        errors = []
        with self.lock:
            # Attempt every release even when the daemon disconnects partway.
            for key in self.held_keys.copy():
                try:
                    self.release(key)
                except RuntimeError as error:
                    errors.append(str(error))
            for button in self.held_buttons.copy():
                try:
                    self.button(button, False)
                except RuntimeError as error:
                    errors.append(str(error))
        if errors:
            raise RuntimeError("; ".join(errors))


controller = WaylandInput()
press = controller.press
release = controller.release
write = controller.write


def cleanup():
    try:
        controller.release_all()
    except RuntimeError as error:
        print("[input] Could not release virtual input:", error)


atexit.register(cleanup)
