import base64
import logging
from functools import lru_cache
from pathlib import Path

import httpx
import nltk
import spacy
from pydub import AudioSegment

from app.config import settings
from app.core.openrouter import safe_chat_completion
from app.db.enums import FileType

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _spacy_model(lang: str) -> spacy.Language:
    model_name = 'ru_core_news_sm' if lang == 'ru' else 'en_core_web_sm'
    return spacy.load(model_name)


async def extract_text(
    file_path: str,
    file_type: FileType,
    params: dict,
) -> tuple[str, FileType]:
    ext = Path(file_path).suffix.lower()

    if file_type == FileType.TEXT and ext == '.txt':
        return file_path, FileType.TEXT

    txt_path = str(Path(file_path).with_suffix('.txt'))

    if ext == '.pdf':
        text = _extract_pdf(file_path)
    elif ext in ('.docx', '.doc'):
        text = _extract_docx(file_path)
    elif file_type == FileType.AUDIO:
        text = await _transcribe_audio(file_path, params)
    elif file_type == FileType.IMAGE:
        text = await _describe_image(file_path, params)
    elif file_type == FileType.TEXT:
        # .csv, .md, etc. — return as-is after renaming to .txt
        text = Path(file_path).read_text(encoding='utf-8')
    else:
        return file_path, file_type

    Path(txt_path).write_text(text, encoding='utf-8')
    return txt_path, FileType.TEXT


def _extract_pdf(file_path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    return '\n'.join(page.extract_text() or '' for page in reader.pages)


def _extract_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    return '\n'.join(p.text for p in doc.paragraphs if p.text)


async def _transcribe_audio(file_path: str, params: dict) -> str:
    model = str(params.get('model', settings.openrouter_stt_model))
    path = Path(file_path)

    compressed = _compress_for_whisper(path)

    file_size = compressed.stat().st_size
    max_bytes = 24 * 1024 * 1024  # 24 MB safety margin

    if file_size <= max_bytes:
        text = await _transcribe_chunk(compressed, model)
    else:
        text = await _transcribe_chunked(compressed, model, max_bytes)

    if compressed != path:
        compressed.unlink(missing_ok=True)

    return text


def _compress_for_whisper(path: Path) -> Path:
    """Re-encode audio to mono 32 kbps MP3 to minimise upload size."""

    out = path.with_suffix('._whisper.mp3')
    if out.exists():
        return out
    audio = AudioSegment.from_file(str(path))
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(str(out), format='mp3', bitrate='32k')
    return out


async def _transcribe_chunk(path: Path, model: str) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f'{settings.openrouter_base_url}/audio/transcriptions',
            headers={
                'Authorization': f'Bearer {settings.openrouter_api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://dataforge.app',
                'X-Title': 'DataForge',
            },
            json={
                'model': model,
                'input_audio': {'data': b64, 'format': 'mp3'},
            },
        )
        if not response.is_success:
            logger.error('Whisper error %s: %s', response.status_code, response.text)
        response.raise_for_status()
    return str(response.json().get('text', ''))


async def _transcribe_chunked(path: Path, model: str, max_bytes: int) -> str:
    audio = AudioSegment.from_file(str(path))
    # Estimate how many bytes per millisecond so we can size the chunks
    total_ms = len(audio)
    total_bytes = path.stat().st_size
    bytes_per_ms = total_bytes / total_ms if total_ms else 1

    chunk_ms = int(max_bytes / bytes_per_ms)
    parts: list[str] = []
    chunk_dir = path.parent / '__chunks__'
    chunk_dir.mkdir(exist_ok=True)

    try:
        start = 0
        idx = 0
        while start < total_ms:
            end = min(start + chunk_ms, total_ms)
            chunk = audio[start:end]
            chunk_path = chunk_dir / f'chunk_{idx}.mp3'
            chunk.export(str(chunk_path), format='mp3', bitrate='32k')
            parts.append(await _transcribe_chunk(chunk_path, model))
            chunk_path.unlink(missing_ok=True)
            start = end
            idx += 1
    finally:
        try:
            chunk_dir.rmdir()
        except OSError:
            pass

    return ' '.join(parts)


async def _describe_image(file_path: str, params: dict) -> str:
    model = str(params.get('model', settings.openrouter_vision_model))
    ext = Path(file_path).suffix.lstrip('.').lower()
    mime = (
        f'image/{ext}' if ext in ('png', 'jpg', 'jpeg', 'webp', 'gif') else 'image/png'
    )

    raw = Path(file_path).read_bytes()
    b64 = base64.b64encode(raw).decode('utf-8')

    response = await safe_chat_completion(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': 'Extract all text from this image. Return only the text content.',
                    },
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:{mime};base64,{b64}'},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content or ''  # type: ignore[union-attr,attr-defined]


async def translate(file_path: str, params: dict) -> str:
    target_lang = params.get('target_lang', 'en')
    model = str(params.get('model', settings.openrouter_llm_model))

    content = Path(file_path).read_text(encoding='utf-8')
    response = await safe_chat_completion(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': (
                    f'Translate the following text to {target_lang}. '
                    f'Return only the translated text:\n\n{content}'
                ),
            }
        ],
    )
    translated = response.choices[0].message.content or ''  # type: ignore[union-attr,attr-defined]
    Path(file_path).write_text(translated, encoding='utf-8')
    return file_path


def lemmatize(file_path: str, params: dict) -> str:
    lang = str(params.get('lang', 'en'))
    nlp = _spacy_model(lang)
    content = Path(file_path).read_text(encoding='utf-8')
    doc = nlp(content)
    lemmatized = ' '.join(token.lemma_ for token in doc if not token.is_space)
    Path(file_path).write_text(lemmatized, encoding='utf-8')
    return file_path


def remove_stopwords(file_path: str, params: dict) -> str:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt_tab', quiet=True)

    from nltk.corpus import stopwords as sw
    from nltk.tokenize import word_tokenize

    lang = str(params.get('lang', 'en'))
    nltk_lang = 'russian' if lang == 'ru' else 'english'
    stop_words = set(sw.words(nltk_lang))

    content = Path(file_path).read_text(encoding='utf-8')
    tokens = word_tokenize(content)
    filtered = [t for t in tokens if t.lower() not in stop_words]
    Path(file_path).write_text(' '.join(filtered), encoding='utf-8')
    return file_path
