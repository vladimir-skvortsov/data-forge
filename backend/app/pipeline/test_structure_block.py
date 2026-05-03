from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.enums import FileType
from app.pipeline.structure_block import _parse_json, structure


def test_parse_json_clean() -> None:
    assert _parse_json('{"a": 1}') == {'a': 1}


def test_parse_json_strips_markdown_block() -> None:
    raw = '```json\n{"key": "value"}\n```'
    assert _parse_json(raw) == {'key': 'value'}


def test_parse_json_strips_markdown_no_lang() -> None:
    raw = '```\n{"x": 42}\n```'
    assert _parse_json(raw) == {'x': 42}


@pytest.mark.anyio
async def test_structure_text_calls_llm(tmp_path: Path) -> None:
    txt = tmp_path / 'doc.txt'
    txt.write_text('some content', encoding='utf-8')

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"title": "Test"}'

    with patch(
        'app.pipeline.structure_block.safe_chat_completion',
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_cc:
        result = await structure(str(txt), FileType.TEXT, {'fields': []}, {})

    mock_cc.assert_called_once()
    assert result == {'title': 'Test'}


@pytest.mark.anyio
async def test_structure_image_sends_base64(tmp_path: Path) -> None:
    img = tmp_path / 'pic.png'
    img.write_bytes(b'\x89PNG')

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"caption": "a dog"}'

    with patch(
        'app.pipeline.structure_block.safe_chat_completion',
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_cc:
        result = await structure(str(img), FileType.IMAGE, {}, {})

    call_kwargs = mock_cc.call_args.kwargs
    content = call_kwargs['messages'][0]['content']
    image_part = next(p for p in content if p.get('type') == 'image_url')
    assert image_part['image_url']['url'].startswith('data:image/png;base64,')
    assert result == {'caption': 'a dog'}


@pytest.mark.anyio
async def test_structure_uses_model_from_params(tmp_path: Path) -> None:
    txt = tmp_path / 'doc.txt'
    txt.write_text('text', encoding='utf-8')

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{}'

    with patch(
        'app.pipeline.structure_block.safe_chat_completion',
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_cc:
        await structure(
            str(txt), FileType.TEXT, {}, {'model': 'anthropic/claude-3-haiku'}
        )

    call_kwargs = mock_cc.call_args.kwargs
    assert call_kwargs['model'] == 'anthropic/claude-3-haiku'
