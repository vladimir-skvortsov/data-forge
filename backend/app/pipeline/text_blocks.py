import base64
from functools import lru_cache
from pathlib import Path

import nltk
import spacy

from app.config import settings
from app.core.openrouter import safe_audio_transcription, safe_chat_completion
from app.db.enums import FileType


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
    with Path(file_path).open('rb') as audio_file:
        transcript = await safe_audio_transcription(model=model, file=audio_file)
    return transcript.text  # type: ignore[union-attr]


async def _describe_image(file_path: str, params: dict) -> str:
    model = str(params.get('model', settings.openrouter_vision_model))
    ext = Path(file_path).suffix.lstrip('.').lower()
    mime = (
        f'image/{ext}' if ext in ('png', 'jpg', 'jpeg', 'webp', 'gif') else 'image/png'
    )

    with Path(file_path).open('rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

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
    return response.choices[0].message.content or ''  # type: ignore[union-attr]


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
    translated = response.choices[0].message.content or ''  # type: ignore[union-attr]
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
