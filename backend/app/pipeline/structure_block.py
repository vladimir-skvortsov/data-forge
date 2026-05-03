import base64
import json
import re
from pathlib import Path

from app.config import settings
from app.core.openrouter import safe_chat_completion
from app.db.enums import FileType


def _parse_json(text: str) -> dict:
    clean = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    clean = re.sub(r'\s*```\s*$', '', clean.strip(), flags=re.MULTILINE)
    return json.loads(clean.strip())


def _schema_prompt(schema: list[dict]) -> str:
    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
    return (
        'Extract structured data from the content below according to this schema and return '
        'ONLY valid JSON matching it — no extra text or explanation.\n\n'
        f'Schema fields:\n{schema_str}\n\n'
    )


async def structure(
    file_path: str,
    file_type: FileType,
    params: dict,
) -> dict:
    schema: list[dict] = params.get('schema', [])
    if file_type == FileType.IMAGE:
        model = str(params.get('model', settings.openrouter_vision_model))
        return await _structure_image(file_path, schema, model)
    model = str(params.get('model', settings.openrouter_llm_model))
    return await _structure_text(file_path, schema, model)


async def _structure_text(file_path: str, schema: list[dict], model: str) -> dict:
    content = Path(file_path).read_text(encoding='utf-8')
    prompt = _schema_prompt(schema) + f'Content:\n{content}'

    response = await safe_chat_completion(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        response_format={'type': 'json_object'},
    )
    return _parse_json(response.choices[0].message.content or '{}')  # type: ignore[union-attr]


async def _structure_image(file_path: str, schema: list[dict], model: str) -> dict:
    ext = Path(file_path).suffix.lstrip('.').lower()
    mime = f'image/{ext}' if ext in ('png', 'jpg', 'jpeg', 'webp') else 'image/png'

    with Path(file_path).open('rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = _schema_prompt(schema) + 'Extract the data from the image above.'

    response = await safe_chat_completion(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:{mime};base64,{b64}'},
                    },
                ],
            }
        ],
        response_format={'type': 'json_object'},
    )
    return _parse_json(response.choices[0].message.content or '{}')  # type: ignore[union-attr]
