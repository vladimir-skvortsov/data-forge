from decimal import Decimal
from unittest.mock import MagicMock

from app.core.cost_estimator import (
    BLOCK_PER_FILE_COSTS,
    BLOCK_PER_JOB_COSTS,
    estimate_cost,
    estimate_file_base_cost,
)
from app.db.enums import FileType
from app.db.models.job_file import JobFile


def _file(
    file_type: FileType, size_bytes: int = 2000, duration: float | None = None
) -> JobFile:
    f = MagicMock(spec=JobFile)
    f.file_type = file_type
    f.file_size_bytes = size_bytes
    f.duration_seconds = duration
    return f


def test_text_file_one_page() -> None:
    f = _file(FileType.TEXT, size_bytes=2000)
    assert estimate_file_base_cost(f) == Decimal('1')


def test_text_file_two_pages() -> None:
    f = _file(FileType.TEXT, size_bytes=4001)
    assert estimate_file_base_cost(f) == Decimal('3')


def test_text_file_minimum_one_credit() -> None:
    f = _file(FileType.TEXT, size_bytes=10)
    assert estimate_file_base_cost(f) == Decimal('1')


def test_image_file_three_credits() -> None:
    f = _file(FileType.IMAGE, size_bytes=500_000)
    assert estimate_file_base_cost(f) == Decimal('3')


def test_audio_with_duration() -> None:
    f = _file(FileType.AUDIO, duration=90.0)  # 1.5 min → ceil=2
    assert estimate_file_base_cost(f) == Decimal('4')


def test_audio_exactly_one_minute() -> None:
    f = _file(FileType.AUDIO, duration=60.0)
    assert estimate_file_base_cost(f) == Decimal('2')


def test_audio_without_duration_uses_size() -> None:
    f = _file(FileType.AUDIO, size_bytes=1, duration=None)
    cost = estimate_file_base_cost(f)
    assert cost >= Decimal('2')


def test_empty_file_list_returns_zero() -> None:
    assert estimate_cost([], []) == Decimal('0')


def test_no_pipeline_blocks_only_base_cost() -> None:
    files = [_file(FileType.IMAGE)]
    assert estimate_cost(files, []) == Decimal('3')


def test_per_file_block_added_per_file() -> None:
    files = [_file(FileType.IMAGE), _file(FileType.IMAGE)]
    pipeline = [{'type': 'image_resize'}]
    expected = (Decimal('3') + BLOCK_PER_FILE_COSTS['image_resize']) * 2
    assert estimate_cost(files, pipeline) == expected


def test_per_job_block_added_once_regardless_of_file_count() -> None:
    files = [_file(FileType.IMAGE), _file(FileType.IMAGE), _file(FileType.IMAGE)]
    pipeline = [{'type': 'deduplicate'}]
    base = Decimal('3') * 3
    expected = base + BLOCK_PER_JOB_COSTS['deduplicate']
    assert estimate_cost(files, pipeline) == expected


def test_unknown_block_type_ignored() -> None:
    files = [_file(FileType.IMAGE)]
    pipeline = [{'type': 'nonexistent_block'}]
    assert estimate_cost(files, pipeline) == Decimal('3')


def test_multiple_per_file_blocks_cumulative() -> None:
    files = [_file(FileType.AUDIO, duration=60.0)]
    pipeline = [{'type': 'audio_normalize'}, {'type': 'audio_denoise'}]
    expected = (
        Decimal('2')
        + BLOCK_PER_FILE_COSTS['audio_normalize']
        + BLOCK_PER_FILE_COSTS['audio_denoise']
    )
    assert estimate_cost(files, pipeline) == expected


def test_mixed_per_file_and_per_job_blocks() -> None:
    files = [
        _file(FileType.TEXT, size_bytes=2000),
        _file(FileType.TEXT, size_bytes=2000),
    ]
    pipeline = [{'type': 'translate'}, {'type': 'deduplicate'}]
    per_file = Decimal('1') + BLOCK_PER_FILE_COSTS['translate']
    expected = per_file * 2 + BLOCK_PER_JOB_COSTS['deduplicate']
    assert estimate_cost(files, pipeline) == expected
