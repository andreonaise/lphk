import pygame, os
from time import sleep
from runtime_support import sound_path

PATH = None
SOUND_PATH = "/user_sounds/"

import pygame

m = pygame.mixer

def init(path_in):
    global PATH
    PATH = path_in

    m.pre_init(44100, -16, 2, 2048)
    try:
        m.init()
    except pygame.error as error:
        print("[sound] Audio unavailable; continuing without sound:", error)

def full_name(filename):
    return sound_path(PATH, filename)

def is_valid(filename):
    final_name = full_name(filename)
    try:
        sound = m.Sound(final_name)
        return True
    except:
        return False

def play(filename, volume=100.0):
    final_name = full_name(filename)
    try:
        sound = m.Sound(final_name)
        vol = float(volume / 100.0)
        sound.set_volume(vol)
        sound.play()
    except:
        print("[sound] Could not play sound " + final_name)


def stop():
    try:
        m.stop()
    except:
        print("Could not stop sounds")


def fadeout(delay):
    try:
        m.fadeout(delay)
    except:
        print("Could not fade out sound")

