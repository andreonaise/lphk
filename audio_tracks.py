"""Independent mixer channels with nonblocking fades and real pause/unpause."""
from dataclasses import dataclass, field
import threading
import time
import math
from audio_waveform import overview


@dataclass
class Track:
    filename: str
    sound: object
    channel: object
    volume: float
    fade_in: int
    fade_out: int
    length: float
    pause_fade: object = None
    channel_index: int = 0
    base_sound: object = None
    pcm: object = None
    waveform: list = field(default_factory=list)
    state: str = 'stopped'
    gain: float = 0
    elapsed: float = 0
    active_since: float = 0
    envelope: object = None


class TrackPlayer:
    def __init__(self, mixer, resolve, clock=time.monotonic):
        self.mixer = mixer
        self.resolve = resolve
        self.clock = clock
        self.lock = threading.RLock()
        self.tracks = {}
        self.channel_owners = {}

    def _position(self, track, now):
        if track.state in ('stopped', 'paused'):
            return track.elapsed
        return min(track.length, track.elapsed + max(0, now - track.active_since))

    def _fade(self, track, target, milliseconds, action, now):
        track.envelope = (now, milliseconds / 1000, track.gain, target, action)
        track.state = 'fading_in' if target > track.gain else 'fading_out'
        if not milliseconds:
            self._finish(track, target, action, now)

    def _finish(self, track, gain, action, now):
        track.gain = gain
        track.channel.set_volume(gain)
        track.envelope = None
        if action == 'pause':
            track.elapsed = self._position(track, now)
            track.channel.pause()
            track.state = 'paused'
        elif action in ('stop', 'end'):
            track.channel.stop()
            track.sound = None
            track.base_sound = track.pcm = None
            if self.channel_owners.get(track.channel_index) is track:
                self.channel_owners.pop(track.channel_index)
            track.elapsed = track.length if action == 'end' else 0
            track.state = 'stopped'
        else:
            track.state = 'playing'

    def toggle(self, pad, filename, volume=100, fade_in=0, fade_out=0, pause_fade=None):
        with self.lock:
            self.update()
            track = self.tracks.get(pad)
            if track and track.filename == filename and track.state != 'stopped':
                track.volume, track.fade_in, track.fade_out = volume / 100, fade_in, fade_out
                track.pause_fade = fade_out if pause_fade is None else pause_fade
                if track.state == 'paused' or (track.envelope and track.envelope[-1] == 'pause'):
                    self.resume(pad)
                else:
                    self.pause(pad)
                return
            # Load first: a bad replacement must not interrupt an existing track.
            clip = self.mixer.Sound(self.resolve(filename))
            if track and track.state != 'stopped':
                track.channel.stop()
                self.channel_owners.pop(track.channel_index, None)
            coordinates = pad[-2:]
            preferred = coordinates[0] * 9 + coordinates[1]
            index = preferred if preferred not in self.channel_owners else next((i for i in range(81) if i not in self.channel_owners), None)
            if index is None:
                raise RuntimeError('All 81 soundtrack channels are in use. Stop a track before starting another.')
            channel = self.mixer.Channel(index)
            now = self.clock()
            track = Track(filename, clip, channel, volume / 100, fade_in, fade_out,
                          clip.get_length(), pause_fade=fade_out if pause_fade is None else pause_fade,
                          channel_index=index, base_sound=clip,
                          state='playing', active_since=now)
            try:
                _, sample_format, channels = self.mixer.get_init()
                track.waveform = overview(clip, channels, sample_format)
            except (TypeError, ValueError, AttributeError):
                track.waveform = []
            self.tracks[pad] = track
            self.channel_owners[index] = track
            # Set initial gain before play to avoid a full-volume first buffer.
            track.gain = 0 if fade_in else track.volume
            channel.set_volume(track.gain)
            channel.play(clip)
            if fade_in:
                self._fade(track, track.volume, fade_in, 'play', now)

    def pause(self, pad, fade_ms=None):
        with self.lock:
            self.update()
            track = self.tracks.get(pad)
            if not track or track.state in ('paused', 'stopped'):
                return
            self._fade(track, 0, track.pause_fade if fade_ms is None else fade_ms, 'pause', self.clock())

    def resume(self, pad, fade_ms=None):
        with self.lock:
            self.update()
            track = self.tracks.get(pad)
            if not track or track.state == 'stopped':
                return
            now = self.clock()
            if track.state == 'paused':
                track.active_since = now
                track.channel.unpause()
            elif not (track.envelope and track.envelope[-1] == 'pause'):
                return
            self._fade(track, track.volume, track.fade_in if fade_ms is None else fade_ms, 'play', now)

    def stop(self, pad, fade_ms=0):
        with self.lock:
            self.update()
            track = self.tracks.get(pad)
            if not track or track.state == 'stopped':
                return
            if track.state == 'paused' or not fade_ms:
                self._finish(track, 0, 'stop', self.clock())
            else:
                self._fade(track, 0, fade_ms, 'stop', self.clock())

    def all(self, action, fade_ms=None):
        with self.lock:
            for pad in list(self.tracks):
                if action == 'stop':
                    self.stop(pad, 0 if fade_ms is None else fade_ms)
                else:
                    getattr(self, action)(pad, fade_ms)

    def toggle_all(self, bindings):
        """One transport button: start, pause, or resume the soundtrack pads."""
        with self.lock:
            self.update()
            active = [track for track in self.tracks.values() if track.state != 'stopped']
            playing = any(track.state != 'paused' and not (track.envelope and track.envelope[-1] == 'pause') for track in active)
            if playing:
                self.all('pause')
                return 'pause'
            if active:
                self.all('resume')
                return 'resume'
            for pad, settings in bindings.items():
                self.toggle(pad, *settings)
            return 'play'

    def seek(self, pad, seconds, relative=False):
        if not math.isfinite(float(seconds)):
            raise ValueError('Seek time must be a finite number.')
        with self.lock:
            self.update()
            track = self.tracks.get(pad)
            if not track or track.state == 'stopped':
                return
            now = self.clock()
            target = float(seconds) + (self._position(track, now) if relative else 0)
            target = max(0, min(track.length, target))
            if target >= track.length:
                self._finish(track, 0, 'end', now)
                return
            rate, size, channels = self.mixer.get_init()
            frame_bytes = abs(size) // 8 * channels
            if track.pcm is None:
                track.pcm = track.base_sound.get_raw()
            frame = int(target * rate)
            clip = self.mixer.Sound(buffer=track.pcm[frame * frame_bytes:])
            paused = track.state == 'paused'
            if track.envelope and track.envelope[-1] == 'end':
                track.envelope = None
                track.gain = track.volume
                track.state = 'playing'
            track.channel.stop()
            track.channel.set_volume(0 if paused else track.gain)
            track.channel.play(clip)
            if paused:
                track.channel.pause()
            track.sound = clip
            track.base_sound = None
            track.elapsed, track.active_since = frame / rate, now

    def seek_all(self, seconds, relative=False):
        with self.lock:
            for pad in list(self.tracks):
                self.seek(pad, seconds, relative)

    def update(self):
        with self.lock:
            now = self.clock()
            for track in self.tracks.values():
                if track.state in ('stopped', 'paused'):
                    continue
                if not track.channel.get_busy():
                    self._finish(track, 0, 'end', now)
                    continue
                if track.envelope:
                    start, duration, initial, target, action = track.envelope
                    fraction = min(1, max(0, (now - start) / duration)) if duration else 1
                    track.gain = initial + (target - initial) * fraction
                    track.channel.set_volume(track.gain)
                    if fraction == 1:
                        self._finish(track, target, action, now)
                remaining = track.length - self._position(track, now)
                ending = track.envelope and track.envelope[-1] in ('pause', 'stop', 'end')
                if track.state not in ('stopped', 'paused') and not ending and track.fade_out and remaining <= track.fade_out / 1000:
                    self._fade(track, 0, max(0, round(remaining * 1000)), 'end', now)

    def snapshot(self):
        with self.lock:
            now = self.clock()
            return {pad: {'filename': track.filename, 'state': track.state,
                          'gain': track.gain, 'position': self._position(track, now),
                          'length': track.length, 'waveform': track.waveform}
                    for pad, track in self.tracks.items()}
