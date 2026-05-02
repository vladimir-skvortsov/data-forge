from pathlib import Path

import noisereduce as nr
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent


def _fmt(file_path: str) -> str:
    return Path(file_path).suffix.lstrip('.').lower() or 'mp3'


def remove_silence(file_path: str, params: dict) -> str:
    audio = AudioSegment.from_file(file_path)
    min_silence_len = int(params.get('min_silence_len', 1000))
    silence_thresh = int(params.get('silence_thresh', -40))

    chunks = detect_nonsilent(
        audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh
    )
    if not chunks:
        return file_path

    result = sum((audio[start:end] for start, end in chunks), AudioSegment.empty())
    result.export(file_path, format=_fmt(file_path))
    return file_path


def normalize(file_path: str, params: dict) -> str:
    audio = AudioSegment.from_file(file_path)
    target_dbfs = float(params.get('target_dbfs', -20.0))
    delta = target_dbfs - audio.dBFS
    audio.apply_gain(delta).export(file_path, format=_fmt(file_path))
    return file_path


def boost_volume(file_path: str, params: dict) -> str:
    audio = AudioSegment.from_file(file_path)
    db = float(params.get('db', 6.0))
    (audio + db).export(file_path, format=_fmt(file_path))
    return file_path


def denoise(file_path: str, params: dict) -> str:  # noqa: ARG001
    audio = AudioSegment.from_file(file_path)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    max_int = float(2 ** (audio.sample_width * 8 - 1))

    # Normalise to [-1, 1] for noisereduce
    normalised = samples / max_int

    if audio.channels == 2:
        stereo = normalised.reshape((-1, 2)).T
        reduced = np.array(
            [nr.reduce_noise(y=ch, sr=audio.frame_rate) for ch in stereo]
        ).T.flatten()
    else:
        reduced = nr.reduce_noise(y=normalised, sr=audio.frame_rate)

    # Back to integer samples
    result_int = (reduced * max_int).clip(-max_int, max_int - 1).astype(np.int16)
    denoised = AudioSegment(
        result_int.tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels,
    )
    denoised.export(file_path, format=_fmt(file_path))
    return file_path
