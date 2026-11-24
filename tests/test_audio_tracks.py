from pathlib import Path
import os
import sys
import tempfile
import time
import unittest
import wave
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio_tracks import TrackPlayer
import track_commands


class TrackTests(unittest.TestCase):
    def test_one_global_button_starts_pauses_and_resumes(self):
        bindings = {self.pad: ('song.wav', 80, 1000, 4000, 500)}
        self.assertEqual(self.player.toggle_all(bindings), 'play')
        self.advance(2)
        self.assertEqual(self.player.toggle_all(bindings), 'pause')
        self.advance(0.5)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'paused')
        self.assertEqual(self.player.toggle_all(bindings), 'resume')
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'playing')
        self.channels[1].play.assert_called_once()

    def test_same_pad_toggles_with_independent_pause_and_play_fades(self):
        settings = ('song.wav', 80, 2000, 5000, 1000)
        self.player.toggle(self.pad, *settings)
        self.advance(3)
        clip = self.player.tracks[self.pad].sound
        self.player.toggle(self.pad, *settings)
        self.advance(0.5)
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.4)
        self.advance(0.5)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'paused')
        position = self.player.snapshot()[self.pad]['position']
        self.advance(4)
        self.player.toggle(self.pad, *settings)
        self.advance(1)
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.4)
        self.assertGreater(self.player.snapshot()[self.pad]['position'], position)
        self.assertIs(self.player.tracks[self.pad].sound, clip)
        self.channels[1].play.assert_called_once()
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'playing')
        self.assertEqual(self.player.tracks[self.pad].fade_out, 5000)

    def test_instant_pause_keeps_a_separate_natural_end_fade(self):
        self.player.toggle(self.pad, 'song.wav', 100, 0, 5000, 0)
        self.player.pause(self.pad)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'paused')
        self.player.resume(self.pad)
        self.advance(15)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'fading_out')
        self.advance(2.5)
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.5)

    def setUp(self):
        self.time = 0.0
        self.mixer = MagicMock()
        self.channels = {}
        self.mixer.Channel.side_effect = lambda index: self.channels.setdefault(index, MagicMock())
        self.mixer.Sound.return_value.get_length.return_value = 20
        self.player = TrackPlayer(self.mixer, lambda name: '/sounds/' + name, lambda: self.time)
        self.pad = (0, 1)

    def advance(self, seconds):
        self.time += seconds
        self.player.update()

    def test_fade_in_is_per_track_and_nonblocking(self):
        self.player.toggle(self.pad, 'song.wav', 80, 2000, 1000)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'fading_in')
        self.advance(1)
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.4)
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'playing')
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.8)

    def test_fade_pause_then_resume_keeps_channel_and_position(self):
        self.player.toggle(self.pad, 'song.wav', 80, 1000, 1000)
        self.advance(3)
        self.player.toggle(self.pad, 'song.wav', 80, 1000, 1000)
        self.advance(0.5)
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.4)
        self.advance(0.5)
        paused = self.player.snapshot()[self.pad]['position']
        self.assertEqual(paused, 4)
        self.advance(5)
        self.assertEqual(self.player.snapshot()[self.pad]['position'], paused)
        channel = self.channels[1]
        channel.pause.assert_called_once()
        channel.play.assert_called_once()
        self.player.toggle(self.pad, 'song.wav', 80, 1000, 1000)
        channel.unpause.assert_called_once()
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['position'], 5)
        channel.play.assert_called_once()

    def test_zero_fades_pause_and_resume_immediately(self):
        self.player.toggle(self.pad, 'song.wav')
        self.advance(2)
        self.player.pause(self.pad)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'paused')
        self.player.resume(self.pad)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'playing')

    def test_natural_end_uses_fade_out(self):
        self.player.toggle(self.pad, 'song.wav', 100, 0, 2000)
        self.advance(18)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'fading_out')
        self.advance(1)
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 0.5)
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'stopped')

    def test_resume_can_cancel_an_in_progress_pause_fade(self):
        self.player.toggle(self.pad, 'song.wav', 100, 1000, 1000)
        self.advance(2)
        self.player.pause(self.pad)
        self.advance(0.5)
        self.player.resume(self.pad)
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'playing')
        self.assertAlmostEqual(self.player.snapshot()[self.pad]['gain'], 1)
        self.channels[1].play.assert_called_once()

    def test_multiple_tracks_do_not_pause_one_another(self):
        other = (2, 3)
        self.player.toggle(self.pad, 'song.wav')
        self.player.toggle(other, 'song.wav')
        self.player.pause(self.pad)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'paused')
        self.assertEqual(self.player.snapshot()[other]['state'], 'playing')
        self.assertIsNot(self.channels[1], self.channels[21])

    def test_missing_replacement_does_not_stop_current_track(self):
        self.player.toggle(self.pad, 'song.wav')
        self.mixer.Sound.side_effect = OSError('missing')
        with self.assertRaises(OSError):
            self.player.toggle(self.pad, 'missing.wav')
        self.channels[1].stop.assert_not_called()
        self.assertEqual(self.player.snapshot()[self.pad]['filename'], 'song.wav')

    def test_finished_clip_resets_visual_state(self):
        self.player.toggle(self.pad, 'song.wav')
        self.channels[1].get_busy.return_value = False
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'stopped')
        self.player.toggle(self.pad, 'song.wav')
        self.assertEqual(self.channels[1].play.call_count, 2)

    def test_stop_while_paused_does_not_unpause_audio(self):
        self.player.toggle(self.pad, 'song.wav')
        self.player.pause(self.pad)
        self.player.stop(self.pad, 1000)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'stopped')
        self.channels[1].unpause.assert_not_called()

    def test_global_controls_and_override_fade(self):
        self.player.toggle(self.pad, 'song.wav', 100, 0, 5000)
        self.player.all('pause', 0)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'paused')
        self.player.all('resume', 0)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'playing')
        self.player.all('stop', 1000)
        self.advance(1)
        self.assertEqual(self.player.snapshot()[self.pad]['state'], 'stopped')


class CommandTests(unittest.TestCase):
    def test_optional_pause_fade_roundtrip_and_legacy_default(self):
        line = track_commands.build('my track.wav', 80, 1500, 2000, pause_fade=250)
        self.assertEqual(track_commands.parse(line), ('my track.wav', 80, 1500, 2000, 250))
        self.assertEqual(track_commands.parse('SOUND_TRACK a.wav 80 1500 2000'), ('a.wav', 80, 1500, 2000))
        for value in ('nan', '-1', '1.5', '3600001'):
            with self.assertRaises(ValueError):
                track_commands.parse('SOUND_TRACK a.wav 80 1500 2000 ' + value)

    def test_defaults_and_quoted_filename_roundtrip(self):
        self.assertEqual(track_commands.parse('SOUND_TRACK song.wav'), ('song.wav', 100, 0, 0))
        self.assertEqual(track_commands.parse('SOUND_TRACK song.wav 70'), ('song.wav', 70, 0, 0))
        line = track_commands.build("music/it's a song.wav", 70, 125, 2400)
        self.assertEqual(track_commands.parse(line), ("music/it's a song.wav", 70, 125, 2400))

    def test_invalid_settings_rejected(self):
        for line in ('SOUND_TRACK', 'SOUND_TRACK a.wav 101', 'SOUND_TRACK a.wav nan',
                     'SOUND_TRACK a.wav 80 -1', 'SOUND_TRACK a.wav 80 1.5',
                     'SOUND_TRACK a.wav 80 0 inf', 'SOUND_TRACK ../a.wav',
                     'SOUND_TRACK /a.wav', 'SOUND_TRACK a.wav 80 0 0 extra'):
            with self.subTest(line=line), self.assertRaises(ValueError):
                track_commands.parse(line)

    def test_global_control_validation(self):
        self.assertIsNone(track_commands.control_fade('SOUND_PAUSE'))
        self.assertEqual(track_commands.control_fade('SOUND_RESUME 1500'), 1500)
        for line in ('SOUND_PAUSE -1', 'SOUND_RESUME nan', 'SOUND_RESUME 1 2'):
            with self.assertRaises(ValueError):
                track_commands.control_fade(line)


class ActualMixerTests(unittest.TestCase):
    def make_clip(self, directory):
        path = Path(directory) / 'user_sounds/tone.wav'
        path.parent.mkdir()
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((1, 2, 44100, 0, 'NONE', ''))
            stream.writeframes(b'\x00\x00' * 44100 * 3)
        return path

    def test_background_fades_finish_without_gui_ticks(self):
        import sound
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SDL_AUDIODRIVER': 'dummy'}):
            self.make_clip(directory)
            sound.init(directory)
            try:
                sound.toggle_track((0, 1), 'tone.wav', 80, 50, 50)
                time.sleep(0.15)
                self.assertEqual(sound.snapshot()[0, 1]['state'], 'playing')
                self.assertAlmostEqual(sound.snapshot()[0, 1]['gain'], 0.8)
                self.assertAlmostEqual(sound.player.tracks[0, 1].channel.get_volume(), 0.8, delta=0.02)
                sound.pause()
                time.sleep(0.15)
                self.assertEqual(sound.snapshot()[0, 1]['state'], 'paused')
            finally:
                sound.shutdown()

    def test_legacy_effect_does_not_reuse_a_soundtrack_channel(self):
        import sound
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SDL_AUDIODRIVER': 'dummy'}):
            self.make_clip(directory)
            sound.init(directory)
            try:
                sound.toggle_track((0, 1), 'tone.wav', 70)
                self.assertAlmostEqual(sound.player.tracks[0, 1].channel.get_volume(), 0.7, delta=0.02)
                sound.play('tone.wav', 50)
                self.assertTrue(any(sound.m.Channel(index).get_busy() for index in range(81, 97)))
                self.assertEqual(sound.snapshot()[0, 1]['state'], 'playing')
                sound.pause(0)
                self.assertTrue(any(sound.m.Channel(index).get_busy() for index in range(81, 97)))
                sound.stop()
                self.assertFalse(sound.m.get_busy())
            finally:
                sound.shutdown()

    def test_pause_resume_with_real_sdl_dummy_audio(self):
        import pygame
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SDL_AUDIODRIVER': 'dummy'}):
            path = Path(directory) / 'tone.wav'
            with wave.open(str(path), 'wb') as stream:
                stream.setparams((1, 2, 44100, 0, 'NONE', ''))
                stream.writeframes(b'\x00\x00' * 44100 * 3)
            pygame.mixer.init()
            try:
                pygame.mixer.set_num_channels(97)
                pygame.mixer.set_reserved(81)
                player = TrackPlayer(pygame.mixer, lambda _: str(path))
                player.toggle((0, 1), 'tone.wav', 70, 0, 0)
                time.sleep(0.08)
                player.pause((0, 1))
                position = player.snapshot()[0, 1]['position']
                clip = player.tracks[0, 1].sound
                time.sleep(0.08)
                player.update()
                self.assertEqual(player.snapshot()[0, 1]['position'], position)
                player.resume((0, 1))
                time.sleep(0.08)
                self.assertGreater(player.snapshot()[0, 1]['position'], position)
                self.assertIs(player.tracks[0, 1].sound, clip)
                self.assertIsNotNone(player.tracks[0, 1].channel.get_sound())
                player.all('stop')
            finally:
                pygame.mixer.quit()


if __name__ == '__main__':
    unittest.main()
