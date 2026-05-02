from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.pipeline.audio_blocks import boost_volume, denoise, normalize, remove_silence


@pytest.fixture
def audio_file(tmp_path: Path) -> str:
    p = tmp_path / 'test.mp3'
    p.write_bytes(b'fake')
    return str(p)


def _mock_audio(dbfs: float = -20.0, channels: int = 1) -> MagicMock:
    audio = MagicMock()
    audio.dBFS = dbfs
    audio.channels = channels
    audio.frame_rate = 44100
    audio.sample_width = 2
    audio.apply_gain.return_value = audio
    audio.get_array_of_samples.return_value = list(range(100))
    return audio


def test_remove_silence_trims_and_exports(audio_file: str) -> None:
    audio = _mock_audio()
    with (
        patch('app.pipeline.audio_blocks.AudioSegment.from_file', return_value=audio),
        patch(
            'app.pipeline.audio_blocks.detect_nonsilent',
            return_value=[(0, 500), (1000, 2000)],
        ),
        patch('app.pipeline.audio_blocks.AudioSegment.empty') as mock_empty,
    ):
        mock_concat = MagicMock()
        mock_empty.return_value = mock_concat
        # simulate sum() with AudioSegment.empty() as start
        mock_concat.__add__ = MagicMock(return_value=mock_concat)
        result = remove_silence(audio_file, {})

    assert result == audio_file


def test_remove_silence_no_speech_noop(audio_file: str) -> None:
    audio = _mock_audio()
    with (
        patch('app.pipeline.audio_blocks.AudioSegment.from_file', return_value=audio),
        patch('app.pipeline.audio_blocks.detect_nonsilent', return_value=[]),
    ):
        result = remove_silence(audio_file, {})
    audio.export.assert_not_called()
    assert result == audio_file


def test_normalize_applies_gain(audio_file: str) -> None:
    audio = _mock_audio(dbfs=-30.0)
    with patch('app.pipeline.audio_blocks.AudioSegment.from_file', return_value=audio):
        result = normalize(audio_file, {'target_dbfs': '-20'})
    audio.apply_gain.assert_called_once_with(10.0)
    assert result == audio_file


def test_boost_volume_adds_db(audio_file: str) -> None:
    audio = _mock_audio()
    boosted = MagicMock()
    audio.__add__ = MagicMock(return_value=boosted)
    with patch('app.pipeline.audio_blocks.AudioSegment.from_file', return_value=audio):
        result = boost_volume(audio_file, {'db': '3'})
    audio.__add__.assert_called_once_with(3.0)
    boosted.export.assert_called_once()
    assert result == audio_file


def test_denoise_mono(audio_file: str) -> None:
    audio = _mock_audio(channels=1)
    samples = np.zeros(100, dtype=np.int16)
    audio.get_array_of_samples.return_value = samples.tolist()
    reduced = np.zeros(100, dtype=np.float32)

    with (
        patch('app.pipeline.audio_blocks.AudioSegment.from_file', return_value=audio),
        patch(
            'app.pipeline.audio_blocks.np.array',
            return_value=samples.astype(np.float32),
        ),
        patch('app.pipeline.audio_blocks.nr.reduce_noise', return_value=reduced),
        patch('app.pipeline.audio_blocks.AudioSegment') as mock_seg_class,
    ):
        mock_seg_class.from_file.return_value = audio
        mock_seg_instance = MagicMock()
        mock_seg_class.return_value = mock_seg_instance
        result = denoise(audio_file, {})

    assert result == audio_file
