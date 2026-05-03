from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.enums import FileType
from app.pipeline.text_blocks import (
    extract_text,
    lemmatize,
    remove_stopwords,
    translate,
)


@pytest.fixture
def txt_file(tmp_path: Path) -> str:
    p = tmp_path / 'doc.txt'
    p.write_text('Hello world foo bar', encoding='utf-8')
    return str(p)


@pytest.fixture
def pdf_file(tmp_path: Path) -> str:
    p = tmp_path / 'doc.pdf'
    p.write_bytes(b'%PDF fake')
    return str(p)


@pytest.fixture
def docx_file(tmp_path: Path) -> str:
    p = tmp_path / 'doc.docx'
    p.write_bytes(b'fake docx')
    return str(p)


@pytest.mark.anyio
async def test_extract_text_plain_txt_noop(txt_file: str) -> None:
    path, ftype = await extract_text(txt_file, FileType.TEXT, {})
    assert path == txt_file
    assert ftype == FileType.TEXT


@pytest.mark.anyio
async def test_extract_text_pdf(pdf_file: str) -> None:
    mock_page = MagicMock()
    mock_page.extract_text.return_value = 'pdf content'
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch('app.pipeline.text_blocks._extract_pdf', return_value='pdf content'):
        path, ftype = await extract_text(pdf_file, FileType.TEXT, {})

    assert path.endswith('.txt')
    assert ftype == FileType.TEXT
    assert Path(path).read_text() == 'pdf content'


@pytest.mark.anyio
async def test_extract_text_docx(docx_file: str) -> None:
    with patch('app.pipeline.text_blocks._extract_docx', return_value='docx content'):
        path, ftype = await extract_text(docx_file, FileType.TEXT, {})

    assert path.endswith('.txt')
    assert ftype == FileType.TEXT
    assert Path(path).read_text() == 'docx content'


@pytest.mark.anyio
async def test_extract_text_audio_calls_whisper(tmp_path: Path) -> None:
    audio_path = str(tmp_path / 'file.mp3')
    Path(audio_path).write_bytes(b'fake')

    with patch(
        'app.pipeline.text_blocks._transcribe_audio',
        new=AsyncMock(return_value='transcript'),
    ) as mock_transcribe:
        path, ftype = await extract_text(audio_path, FileType.AUDIO, {})

    mock_transcribe.assert_called_once()
    assert ftype == FileType.TEXT
    assert Path(path).read_text() == 'transcript'


@pytest.mark.anyio
async def test_extract_text_image_calls_vision(tmp_path: Path) -> None:
    img_path = str(tmp_path / 'img.png')
    Path(img_path).write_bytes(b'fake')

    with patch(
        'app.pipeline.text_blocks._describe_image',
        new=AsyncMock(return_value='image text'),
    ) as mock_vision:
        path, ftype = await extract_text(img_path, FileType.IMAGE, {})

    mock_vision.assert_called_once()
    assert ftype == FileType.TEXT
    assert Path(path).read_text() == 'image text'


@pytest.mark.anyio
async def test_translate_writes_translated_content(txt_file: str) -> None:
    mock_response = MagicMock()
    mock_response.choices[0].message.content = 'Привет мир'
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch(
        'app.pipeline.text_blocks.safe_chat_completion',
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await translate(txt_file, {'target_lang': 'ru'})

    assert result == txt_file
    assert Path(txt_file).read_text() == 'Привет мир'


def test_lemmatize_en(txt_file: str) -> None:
    mock_token = MagicMock()
    mock_token.lemma_ = 'hello'
    mock_token.is_space = False
    mock_nlp = MagicMock()
    mock_nlp.return_value = [mock_token]

    with patch('app.pipeline.text_blocks._spacy_model', return_value=mock_nlp):
        result = lemmatize(txt_file, {'lang': 'en'})

    assert result == txt_file
    assert Path(txt_file).read_text() == 'hello'


def test_lemmatize_ru_loads_ru_model(txt_file: str) -> None:
    mock_nlp = MagicMock()
    mock_nlp.return_value = []

    with patch(
        'app.pipeline.text_blocks._spacy_model', return_value=mock_nlp
    ) as mock_loader:
        lemmatize(txt_file, {'lang': 'ru'})

    mock_loader.assert_called_once_with('ru')


def test_remove_stopwords_filters_english(txt_file: str) -> None:
    with (
        patch('app.pipeline.text_blocks.nltk.download'),
        patch('nltk.corpus.stopwords.words', return_value=['hello', 'world']),
        patch(
            'nltk.tokenize.word_tokenize', return_value=['Hello', 'world', 'foo', 'bar']
        ),
    ):
        result = remove_stopwords(txt_file, {'lang': 'en'})

    assert result == txt_file
    assert Path(txt_file).read_text() == 'foo bar'


def test_remove_stopwords_uses_russian_corpus(txt_file: str) -> None:
    with (
        patch('app.pipeline.text_blocks.nltk.download'),
        patch('nltk.corpus.stopwords.words', return_value=[]) as mock_words,
        patch('nltk.tokenize.word_tokenize', return_value=[]),
    ):
        remove_stopwords(txt_file, {'lang': 'ru'})

    mock_words.assert_called_once_with('russian')
