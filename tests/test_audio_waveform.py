import struct
import unittest
from audio_waveform import overview


class WaveformTests(unittest.TestCase):
    def test_stereo_peaks_include_both_channels(self):
        pcm = struct.pack('<8h', 0, 16384, -32768, 0, 0, 8192, 0, 0)
        self.assertEqual(overview(pcm, channels=2, bins=2), [1.0, 0.25])

    def test_silence_and_short_audio(self):
        self.assertEqual(overview(bytes(8), channels=2), [0.0, 0.0])
        self.assertEqual(overview(b''), [])

    def test_unsupported_sample_format(self):
        self.assertEqual(overview(bytes(8), bits=8), [])


if __name__ == '__main__':
    unittest.main()
