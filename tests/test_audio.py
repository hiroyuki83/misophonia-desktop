"""Basic checks for the offline spectrum filter (stdlib unittest)."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from misophonia.audio import process_file, suppress
from misophonia.store import TargetStore


RATE = 16000


def tone(hz: float, seconds: float = 2.0) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    return np.sin(2 * np.pi * hz * t).astype(np.float32) * 0.4


def amplitude(signal: np.ndarray, hz: float) -> float:
    t = np.arange(len(signal)) / RATE
    return float(np.abs(np.dot(signal, np.exp(-2j * np.pi * hz * t))) * 2 / len(signal))


class AudioTests(unittest.TestCase):
    def test_target_tone_attenuated_but_other_tone_retained(self):
        trigger = tone(440)
        other = tone(1300)
        mixed = (trigger + other)[:, None]
        result = suppress(mixed, RATE, [(trigger[:, None], RATE)], strength=0.9, threshold=0.38)
        self.assertEqual(result.shape, mixed.shape)
        self.assertLess(amplitude(result[:, 0], 440), amplitude(mixed[:, 0], 440) * 0.65)
        self.assertGreater(amplitude(result[:, 0], 1300), amplitude(mixed[:, 0], 1300) * 0.75)

    def test_zero_strength_preserves_exact_input(self):
        signal = tone(440)[:, None]
        output = suppress(signal, RATE, [(signal, RATE)], strength=0.0)
        np.testing.assert_array_equal(signal, output)

    def test_silent_reference_rejected(self):
        reference = np.zeros((RATE, 1), dtype=np.float32)
        with self.assertRaises(ValueError):
            suppress(tone(440)[:, None], RATE, [(reference, RATE)])

    def test_stereo_and_resampled_reference(self):
        mono = tone(440)
        mixed = np.column_stack([mono, mono])
        reference_rate = 8000
        ref = np.sin(2 * np.pi * 440 * (np.arange(reference_rate) / reference_rate))
        result = suppress(mixed, RATE, [(ref[:, None], reference_rate)], strength=0.5)
        self.assertEqual(result.shape, mixed.shape)
        self.assertTrue(np.isfinite(result).all())

    def test_file_output_and_local_store(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            original = base / "original.wav"
            reference = base / "reference.wav"
            output = base / "output.wav"
            sf.write(original, tone(440)[:, None], RATE)
            sf.write(reference, tone(440)[:, None], RATE)
            store = TargetStore(base / "user")
            added = store.add_file(reference)
            self.assertEqual(len(store.list()), 1)
            process_file(original, [store.path(added)], output)
            self.assertTrue(output.exists())
            audio, rate = sf.read(output)
            self.assertEqual(len(audio), RATE * 2)
            self.assertEqual(rate, RATE)
            store.delete({added["id"]})
            self.assertEqual(store.list(), [])


if __name__ == "__main__":
    unittest.main()
