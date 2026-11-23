import ms
import sys
from input_backend import BACKEND

if BACKEND == 'windows':
    import system_apis.keyboard_win as keyboard_api
elif BACKEND == 'wayland':
    import system_apis.input_wayland as keyboard_api
else:
    import system_apis.keyboard_unix as keyboard_api

pressed = set()


def sp(name):
    if "mouse_" in name:
        return name

    return keyboard_api.sp(name)


def press(key):
    if type(key) == str:
        if "mouse_" in key:
            ms.press(key[6:])
            pressed.add(key)
            return
    keyboard_api.press(key)
    pressed.add(key)


def release(key):
    if type(key) == str:
        if "mouse_" in key:
            ms.release(key[6:])
            pressed.discard(key)
            return
    keyboard_api.release(key)
    pressed.discard(key)


def release_all():
    errors = []
    for key in pressed.copy():
        try:
            release(key)
        except Exception as error:
            errors.append(str(error))
    if BACKEND == 'wayland':
        try:
            keyboard_api.controller.release_all()
        except RuntimeError as error:
            errors.append(str(error))
    if errors:
        raise RuntimeError("Could not release all input: " + "; ".join(errors))


def tap(key):
    if type(key) == str:
        if "mouse_" in key:
            ms.click(key[6:])
            return
    press(key)
    release(key)


def write(string):
    keyboard_api.write(string)
