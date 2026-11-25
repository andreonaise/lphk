import os
import pygame
import threading
from runtime_support import sound_path
from audio_tracks import TrackPlayer

PATH = None
m = pygame.mixer
player = None
TRACK_CHANNELS = 81
_worker = None
_worker_stop = None
current_page = None


def set_page(page_id):
    global current_page
    current_page = page_id


def pad_key(pad, page_id=None):
    if len(pad) == 3:
        return pad
    page = current_page if page_id is None else page_id
    return tuple(pad) if page is None else (page, *pad)


def _end_worker():
    global _worker, _worker_stop
    if _worker_stop is not None:
        _worker_stop.set()
    if _worker is not None and _worker is not threading.current_thread():
        _worker.join(timeout=1)
    _worker = _worker_stop = None


def _update_loop(current, stop_event):
    while not stop_event.wait(0.01):
        try:
            current.update()
        except (pygame.error, RuntimeError) as error:
            print('[sound] Audio update stopped:', error)
            return


def full_name(filename):
    return sound_path(PATH, filename)


def init(path_in):
    global PATH, player, _worker, _worker_stop
    _end_worker()
    if player is not None:
        player.all('stop')
    PATH = path_in
    player = None
    try:
        m.pre_init(44100, -16, 2, 1024)
        m.init()
        m.set_num_channels(TRACK_CHANNELS + 16)
        m.set_reserved(TRACK_CHANNELS)
        player = TrackPlayer(m, full_name)
        _worker_stop = threading.Event()
        _worker = threading.Thread(target=_update_loop, args=(player, _worker_stop), daemon=True)
        _worker.start()
    except pygame.error as error:
        print('[sound] Audio unavailable; continuing without sound:', error)


def is_valid(filename):
    if not m.get_init():
        return os.path.isfile(full_name(filename))
    try:
        m.Sound(full_name(filename))
        return True
    except (pygame.error, OSError):
        return False


def play(filename, volume=100.0):
    try:
        clip = m.Sound(full_name(filename))
        clip.set_volume(volume / 100)
        if clip.play() is None:
            print('[sound] No free effect channel')
    except (pygame.error, OSError) as error:
        print('[sound] Could not play sound:', error)


def toggle_track(pad, filename, volume=100, fade_in=0, fade_out=0, pause_fade=None, page_id=None):
    if player is None:
        raise RuntimeError('Audio is unavailable. Check your audio output and restart LPHK.')
    player.toggle(pad_key(pad, page_id), filename, volume, fade_in, fade_out, pause_fade)


def toggle_all(bindings):
    if player is None:
        raise RuntimeError('Audio is unavailable. Check your audio output and restart LPHK.')
    return player.toggle_all({pad_key(pad): settings for pad, settings in bindings.items()})


def pause(fade_ms=None):
    if player:
        player.all('pause', fade_ms)


def resume(fade_ms=None):
    if player:
        player.all('resume', fade_ms)


def stop():
    if player:
        player.all('stop')
    if m.get_init():
        m.stop()


def stop_track(pad):
    if player:
        player.stop(pad_key(pad))


def stop_tracks():
    if player:
        with player.lock:
            player.all('stop')
            player.tracks.clear()


def stop_page(page_id):
    if player:
        with player.lock:
            for key in list(player.snapshot()):
                if len(key) == 3 and key[0] == page_id:
                    player.stop(key)
                    player.tracks.pop(key, None)


def seek(seconds, pad=None, relative=False, page_id=None):
    if player:
        if pad is None:
            player.seek_all(seconds, relative)
        else:
            player.seek(pad_key(pad, page_id), seconds, relative)


def stop_faded():
    if player:
        with player.lock:
            for pad, track in list(player.tracks.items()):
                player.stop(pad, track.fade_out)
    if m.get_init():
        for index in range(TRACK_CHANNELS, m.get_num_channels()):
            m.Channel(index).stop()


def fadeout(delay):
    if player:
        player.all('stop', delay)
    if m.get_init():
        for index in range(TRACK_CHANNELS, m.get_num_channels()):
            m.Channel(index).fadeout(delay)


def tick():
    if player:
        player.update()


def snapshot():
    states = all_snapshot()
    return {key[-2:]: state for key, state in states.items()
            if len(key) == 2 or key[0] == current_page}


def all_snapshot():
    return player.snapshot() if player else {}


def visual(pad):
    state = snapshot().get(pad)
    if not state or state['state'] == 'stopped':
        return None
    if state['state'] == 'paused':
        return [205, 155, 72]
    intensity = 0.3 + 0.7 * state['gain']
    return [round(value * intensity) for value in (62, 178, 112)]


def shutdown():
    global player
    _end_worker()
    stop()
    player = None
    if m.get_init():
        m.quit()
