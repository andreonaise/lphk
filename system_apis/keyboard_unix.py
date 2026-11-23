"""Linux/X11 keyboard backend using pynput and X keysyms."""
from pynput.keyboard import Controller, Key, KeyCode

controller = Controller()
ALIASES = {
    "win": "cmd", "win_r": "cmd_r", "apps": "menu",
    "menu": "alt_l", "menu_r": "alt_r",
    "vol_up": "media_volume_up", "vol_down": "media_volume_down",
    "mute": "media_volume_mute", "play_pause": "media_play_pause",
    "prev_track": "media_previous", "next_track": "media_next",
}


def sp(name):
    if name.startswith("num") and len(name) == 4 and name[3] in "0123456789":
        # X11 keysyms, not Windows virtual-key codes.
        return KeyCode.from_vk(0xFFB0 + int(name[3]))
    mapped = ALIASES.get(name, name)
    try:
        return Key[mapped]
    except KeyError:
        return KeyCode.from_char(name) if len(name) == 1 else None


def press(key):
    controller.press(key)


def release(key):
    controller.release(key)


def write(string):
    controller.type(string)
