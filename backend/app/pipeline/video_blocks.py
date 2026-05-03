from pathlib import Path

from moviepy import VideoFileClip


def video_to_audio(file_path: str, params: dict) -> str:
    fmt = str(params.get('format', 'mp3')).lower()
    if fmt not in ('mp3', 'wav', 'ogg'):
        fmt = 'mp3'

    src = Path(file_path)
    out_path = src.with_suffix(f'.{fmt}')

    clip = VideoFileClip(str(src))
    try:
        if clip.audio is None:
            raise ValueError(f'Video file {src.name!r} has no audio track')
        clip.audio.write_audiofile(str(out_path), logger=None)
    finally:
        clip.close()

    return str(out_path)
