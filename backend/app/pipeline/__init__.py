import logging
from dataclasses import dataclass, field

from app.db.enums import FileType
from app.db.models.job_file import JobFile
from app.pipeline import audio_blocks, image_blocks, structure_block, text_blocks

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    file_path: str
    file_type: FileType
    structured_data: dict | None = field(default=None)


async def run_pipeline(
    file: JobFile,
    pipeline_config: list[dict],
    schema_config: dict,
) -> PipelineState:
    state = PipelineState(file_path=file.file_path, file_type=file.file_type)
    for block in pipeline_config:
        block_type = str(block.get('type', ''))
        params = dict(block.get('params') or {})
        await _apply_block(state, block_type, params, schema_config)
    return state


async def _apply_block(
    state: PipelineState,
    block_type: str,
    params: dict,
    schema_config: dict,
) -> None:
    match block_type:
        # ── image ──
        case 'image_resize':
            state.file_path = image_blocks.resize(state.file_path, params)
        case 'image_upscale':
            state.file_path = image_blocks.upscale(state.file_path, params)
        case 'image_enhance':
            state.file_path = image_blocks.enhance(state.file_path, params)
        case 'image_grayscale':
            state.file_path = image_blocks.grayscale(state.file_path, params)
        # ── audio ──
        case 'audio_remove_silence':
            state.file_path = audio_blocks.remove_silence(state.file_path, params)
        case 'audio_normalize':
            state.file_path = audio_blocks.normalize(state.file_path, params)
        case 'audio_boost_volume':
            state.file_path = audio_blocks.boost_volume(state.file_path, params)
        case 'audio_denoise':
            state.file_path = audio_blocks.denoise(state.file_path, params)
        # ── text extraction ──
        case 'extract_text':
            state.file_path, state.file_type = await text_blocks.extract_text(
                state.file_path, state.file_type, params
            )
        # ── text transformation ──
        case 'translate':
            state.file_path = await text_blocks.translate(state.file_path, params)
        case 'lemmatize':
            state.file_path = text_blocks.lemmatize(state.file_path, params)
        case 'remove_stopwords':
            state.file_path = text_blocks.remove_stopwords(state.file_path, params)
        # ── structuring ──
        case 'structure':
            state.structured_data = await structure_block.structure(
                state.file_path, state.file_type, schema_config, params
            )
        # ── post-processing blocks are applied at job level, not per-file ──
        case 'deduplicate' | 'remove_outliers':
            pass
        case _:
            logger.warning('Unknown pipeline block type: %s', block_type)
