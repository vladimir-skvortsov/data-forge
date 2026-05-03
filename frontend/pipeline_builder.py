"""Shared pipeline block builder for New_Job and Edit_Job pages."""

from __future__ import annotations

import json

import streamlit as st

BLOCKS: dict[str, list[tuple[str, str]]] = {
    'Video': [
        ('video_to_audio', 'Extract Audio'),
    ],
    'Image': [
        ('image_resize', 'Resize'),
        ('image_upscale', 'Upscale'),
        ('image_enhance', 'Enhance'),
        ('image_grayscale', 'Grayscale'),
    ],
    'Audio': [
        ('audio_remove_silence', 'Remove Silence'),
        ('audio_normalize', 'Normalize Volume'),
        ('audio_boost_volume', 'Boost Volume'),
        ('audio_denoise', 'Denoise'),
    ],
    'Text': [
        ('extract_text', 'Extract Text'),
        ('translate', 'Translate'),
        ('lemmatize', 'Lemmatize'),
        ('remove_stopwords', 'Remove Stopwords'),
    ],
    'Structuring': [
        ('structure', 'Structure (LLM)'),
    ],
    'Post-processing': [
        ('deduplicate', 'Deduplicate'),
        ('remove_outliers', 'Remove Outliers'),
    ],
}

DEFAULT_PARAMS: dict[str, dict] = {
    'video_to_audio': {'format': 'mp3'},
    'image_resize': {'width': 800, 'height': 600},
    'image_upscale': {'factor': 2},
    'image_enhance': {'brightness': 1.2, 'contrast': 1.1, 'sharpness': 1.0},
    'image_grayscale': {},
    'audio_remove_silence': {'min_silence_len': 1000, 'silence_thresh': -40},
    'audio_normalize': {'target_dbfs': -20.0},
    'audio_boost_volume': {'db': 6.0},
    'audio_denoise': {},
    'extract_text': {},
    'translate': {'target_lang': 'en'},
    'lemmatize': {'lang': 'en'},
    'remove_stopwords': {'lang': 'en'},
    'structure': {},
    'deduplicate': {},
    'remove_outliers': {},
}


def render_pipeline_editor(key_prefix: str) -> None:
    """Render the current pipeline list with reorder/remove controls.

    Reads and mutates ``st.session_state[key_prefix + '_pipeline']``.
    """
    pipeline: list[dict] = st.session_state.get(f'{key_prefix}_pipeline', [])
    if not pipeline:
        st.caption('Identity pipeline — no processing blocks.')
        return

    for i, blk in enumerate(pipeline):
        bc1, bc_nav, bc4 = st.columns([6, 2, 1])
        with bc1:
            if blk['type'] == 'structure':
                schema_len = len(blk['params'].get('schema', []))
                fmt = blk['params'].get('output_format', 'json')
                preview = f'schema: {schema_len} field(s), format: {fmt}'
            elif blk.get('params'):
                preview = json.dumps(blk['params'])
            else:
                preview = 'no params'
            st.write(f'`{i + 1}. {blk["type"]}` — {preview}')
        with bc_nav:
            nav_up, nav_dn = st.columns(2)
            with nav_up:
                if st.button(
                    '↑',
                    key=f'{key_prefix}_up_{i}',
                    disabled=i == 0,
                    use_container_width=True,
                ):
                    pipeline[i - 1], pipeline[i] = blk, pipeline[i - 1]
                    st.rerun()
            with nav_dn:
                if st.button(
                    '↓',
                    key=f'{key_prefix}_dn_{i}',
                    disabled=i == len(pipeline) - 1,
                    use_container_width=True,
                ):
                    pipeline[i + 1], pipeline[i] = blk, pipeline[i + 1]
                    st.rerun()
        with bc4:
            if st.button('✕', key=f'{key_prefix}_rm_{i}', use_container_width=True):
                pipeline.pop(i)
                st.rerun()


def render_block_adder(key_prefix: str) -> None:
    """Render block-type selector + params form + 'Add' button."""
    pc1, pc2 = st.columns(2)
    with pc1:
        category = st.selectbox(
            'Category', list(BLOCKS.keys()), key=f'{key_prefix}_blk_cat'
        )
    with pc2:
        options = BLOCKS[category]
        blk_idx = st.selectbox(
            'Block',
            range(len(options)),
            format_func=lambda i: options[i][1],
            key=f'{key_prefix}_blk_idx',
        )

    selected_type, _ = options[blk_idx]
    is_structure = selected_type == 'structure'
    default_params = DEFAULT_PARAMS.get(selected_type, {})

    if is_structure:
        struct_fields_key = f'{key_prefix}_struct_fields'
        if struct_fields_key not in st.session_state:
            st.session_state[struct_fields_key] = []

        with st.expander('Schema & Output Format', expanded=True):
            struct_format = st.selectbox(
                'Output Format',
                ['json', 'csv', 'yaml', 'parquet'],
                key=f'{key_prefix}_struct_fmt',
            )
            schema_mode = st.radio(
                'Schema Mode',
                ['Visual Builder', 'JSON Editor'],
                horizontal=True,
                key=f'{key_prefix}_struct_mode',
            )

            if schema_mode == 'Visual Builder':
                fc1, fc2, fc3 = st.columns([2, 1, 2])
                with fc1:
                    f_name = st.text_input('Field Name', key=f'{key_prefix}_sf_name')
                with fc2:
                    f_type = st.selectbox(
                        'Type',
                        ['string', 'integer', 'float', 'boolean', 'array'],
                        key=f'{key_prefix}_sf_type',
                    )
                with fc3:
                    f_desc = st.text_input(
                        'Description (optional)', key=f'{key_prefix}_sf_desc'
                    )

                if st.button(
                    'Add Field', disabled=not f_name, key=f'{key_prefix}_sf_add'
                ):
                    st.session_state[struct_fields_key].append(
                        {'name': f_name, 'type': f_type, 'description': f_desc}
                    )
                    st.rerun()

                fields = st.session_state[struct_fields_key]
                for fi, field in enumerate(fields):
                    rc1, rc2 = st.columns([8, 1])
                    with rc1:
                        desc_part = (
                            f' — {field["description"]}' if field['description'] else ''
                        )
                        st.write(f'• `{field["name"]}` ({field["type"]}){desc_part}')
                    with rc2:
                        if st.button(
                            '✕',
                            key=f'{key_prefix}_sf_del_{fi}',
                            use_container_width=True,
                        ):
                            fields.pop(fi)
                            st.rerun()
                if not fields:
                    st.caption('No fields — LLM will infer structure from content.')

                block_params: dict = {
                    'schema': st.session_state[struct_fields_key],
                    'output_format': struct_format,
                }
            else:
                raw = st.text_area(
                    'Params JSON',
                    value=json.dumps(
                        {'schema': [], 'output_format': struct_format}, indent=2
                    ),
                    height=180,
                    key=f'{key_prefix}_struct_raw',
                )
                try:
                    block_params = json.loads(raw)
                    block_params.setdefault('output_format', struct_format)
                    block_params.setdefault('schema', [])
                except json.JSONDecodeError:
                    st.error('Invalid JSON.')
                    block_params = {'schema': [], 'output_format': struct_format}
    else:
        if default_params:
            with st.expander('Block parameters', expanded=True):
                params_raw = st.text_area(
                    'Params (JSON)',
                    value=json.dumps(default_params, indent=2),
                    height=90,
                    key=f'{key_prefix}_blk_params',
                )
                try:
                    block_params = json.loads(params_raw)
                except json.JSONDecodeError:
                    st.error('Invalid JSON params.')
                    block_params = default_params
        else:
            block_params = {}

    if st.button('Add block', type='primary', key=f'{key_prefix}_add_blk'):
        pipeline = st.session_state.setdefault(f'{key_prefix}_pipeline', [])
        pipeline.append({'type': selected_type, 'params': block_params})
        if is_structure:
            st.session_state.pop(f'{key_prefix}_struct_fields', None)
        st.rerun()
