import math
from decimal import Decimal

from app.db.enums import FileType
from app.db.models.job_file import JobFile

_TEXT_BYTES_PER_CREDIT = 2000
_IMAGE_CREDIT = Decimal('3')
_AUDIO_CREDIT_PER_MINUTE = Decimal('2')

BLOCK_PER_FILE_COSTS: dict[str, Decimal] = {
    'image_resize': Decimal('0.5'),
    'image_upscale': Decimal('1.0'),
    'image_enhance': Decimal('0.5'),
    'image_grayscale': Decimal('0.5'),
    'audio_remove_silence': Decimal('0.5'),
    'audio_normalize': Decimal('0.5'),
    'audio_boost_volume': Decimal('0.5'),
    'audio_denoise': Decimal('1.0'),
    'translate': Decimal('1.0'),
    'lemmatize': Decimal('0.5'),
    'remove_stopwords': Decimal('0.5'),
    'extract_text': Decimal('0'),
    'structure': Decimal('0'),
}

BLOCK_PER_JOB_COSTS: dict[str, Decimal] = {
    'deduplicate': Decimal('2'),
    'remove_outliers': Decimal('2'),
}


def estimate_file_base_cost(file: JobFile) -> Decimal:
    if file.file_type == FileType.TEXT:
        pages = max(1, math.ceil(file.file_size_bytes / _TEXT_BYTES_PER_CREDIT))
        return Decimal(pages)
    if file.file_type == FileType.IMAGE:
        return _IMAGE_CREDIT
    if file.file_type == FileType.AUDIO:
        if file.duration_seconds:
            minutes = math.ceil(file.duration_seconds / 60)
        else:
            # rough fallback: assume 128 kbps
            minutes = max(1, math.ceil(file.file_size_bytes / (128 * 1024 // 8 * 60)))
        return Decimal(minutes) * _AUDIO_CREDIT_PER_MINUTE
    return Decimal('1')


def estimate_cost(files: list[JobFile], pipeline_config: list[dict]) -> Decimal:
    if not files:
        return Decimal('0')

    block_types = [str(b.get('type', '')) for b in pipeline_config]

    per_job_extra = sum(
        (BLOCK_PER_JOB_COSTS[bt] for bt in block_types if bt in BLOCK_PER_JOB_COSTS),
        Decimal('0'),
    )

    per_file_extra = sum(
        (BLOCK_PER_FILE_COSTS[bt] for bt in block_types if bt in BLOCK_PER_FILE_COSTS),
        Decimal('0'),
    )

    file_total = sum(
        (estimate_file_base_cost(f) + per_file_extra for f in files),
        Decimal('0'),
    )

    return file_total + per_job_extra


def estimate_breakdown(
    files: list[JobFile], pipeline_config: list[dict]
) -> list[dict[str, object]]:
    if not files:
        return []

    block_types = [str(b.get('type', '')) for b in pipeline_config]
    items: list[dict[str, object]] = []

    # Base cost per file type group
    by_type: dict[str, list[JobFile]] = {}
    for f in files:
        ftype = (
            f.file_type.value if isinstance(f.file_type, FileType) else str(f.file_type)
        )
        by_type.setdefault(ftype, []).append(f)

    for ftype, group in by_type.items():
        base = sum((estimate_file_base_cost(f) for f in group), Decimal('0'))
        items.append({'item': f'{len(group)}× {ftype.upper()}', 'credits': float(base)})

    # Per-file pipeline block costs
    seen_per_file: list[str] = []
    for bt in block_types:
        if (
            bt in BLOCK_PER_FILE_COSTS
            and BLOCK_PER_FILE_COSTS[bt] > 0
            and bt not in seen_per_file
        ):
            seen_per_file.append(bt)
            cost = BLOCK_PER_FILE_COSTS[bt] * len(files)
            items.append(
                {'item': f'Блок {bt} × {len(files)} файлов', 'credits': float(cost)}
            )

    # Per-job pipeline block costs
    seen_per_job: list[str] = []
    for bt in block_types:
        if bt in BLOCK_PER_JOB_COSTS and bt not in seen_per_job:
            seen_per_job.append(bt)
            items.append(
                {
                    'item': f'Блок {bt} (за задачу)',
                    'credits': float(BLOCK_PER_JOB_COSTS[bt]),
                }
            )

    return items
