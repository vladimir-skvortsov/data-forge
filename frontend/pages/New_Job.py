import json

import streamlit as st

import api_client

if 'nj_pipeline' not in st.session_state:
    st.session_state['nj_pipeline'] = []

st.header('Create New Job')

st.subheader('1. Job Details')
title = st.text_input('Job Title', placeholder='My data extraction job')

st.subheader('2. Pipeline')

_BLOCKS: dict[str, list[tuple[str, str]]] = {
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

_DEFAULT_PARAMS: dict[str, dict] = {
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

pc1, pc2 = st.columns(2)
with pc1:
    category = st.selectbox('Category', list(_BLOCKS.keys()), key='blk_cat')
with pc2:
    options = _BLOCKS[category]
    blk_idx = st.selectbox(
        'Block',
        range(len(options)),
        format_func=lambda i: options[i][1],
        key='blk_idx',
    )

selected_type, selected_label = options[blk_idx]
is_structure = selected_type == 'structure'
default_params = _DEFAULT_PARAMS.get(selected_type, {})

# ── Structure block: inline schema + format editor ────────────────────────────
if is_structure:
    if 'nj_struct_fields' not in st.session_state:
        st.session_state['nj_struct_fields'] = []

    with st.expander('Schema & Output Format', expanded=True):
        struct_format = st.selectbox(
            'Output Format', ['json', 'csv', 'yaml', 'parquet'], key='struct_fmt'
        )

        schema_mode = st.radio(
            'Schema Mode',
            ['Visual Builder', 'JSON Editor'],
            horizontal=True,
            key='struct_mode',
        )

        if schema_mode == 'Visual Builder':
            fc1, fc2, fc3 = st.columns([2, 1, 2])
            with fc1:
                f_name = st.text_input('Field Name', key='sf_name')
            with fc2:
                f_type = st.selectbox(
                    'Type',
                    ['string', 'integer', 'float', 'boolean', 'array'],
                    key='sf_type',
                )
            with fc3:
                f_desc = st.text_input('Description (optional)', key='sf_desc')

            if st.button('Add Field', disabled=not f_name, key='sf_add'):
                st.session_state['nj_struct_fields'].append(
                    {'name': f_name, 'type': f_type, 'description': f_desc}
                )
                st.rerun()

            fields = st.session_state['nj_struct_fields']
            if fields:
                for i, field in enumerate(fields):
                    rc1, rc2 = st.columns([8, 1])
                    with rc1:
                        st.write(
                            f'• `{field["name"]}` ({field["type"]})'
                            + (
                                f' — {field["description"]}'
                                if field['description']
                                else ''
                            )
                        )
                    with rc2:
                        if st.button('✕', key=f'sf_del_{i}'):
                            st.session_state['nj_struct_fields'].pop(i)
                            st.rerun()
            else:
                st.caption('No fields — LLM will infer structure from content.')

            block_params = {
                'schema': st.session_state['nj_struct_fields'],
                'output_format': struct_format,
            }

        else:
            default_schema_json = json.dumps(
                {'schema': [], 'output_format': struct_format}, indent=2
            )
            raw = st.text_area(
                'Params JSON', value=default_schema_json, height=200, key='struct_raw'
            )
            try:
                block_params = json.loads(raw)
                block_params.setdefault('output_format', struct_format)
                block_params.setdefault('schema', [])
            except json.JSONDecodeError:
                st.error('Invalid JSON.')
                block_params = {'schema': [], 'output_format': struct_format}

# ── Other blocks: simple params editor ───────────────────────────────────────
else:
    if default_params:
        with st.expander('Block Parameters', expanded=True):
            params_raw = st.text_area(
                'Params (JSON)',
                value=json.dumps(default_params, indent=2),
                height=90,
                key='blk_params',
            )
            try:
                block_params = json.loads(params_raw)
            except json.JSONDecodeError:
                st.error('Invalid JSON params.')
                block_params = default_params
    else:
        block_params = {}

if st.button('＋ Add Block', type='primary'):
    st.session_state['nj_pipeline'].append(
        {'type': selected_type, 'params': block_params}
    )
    if is_structure:
        st.session_state.pop('nj_struct_fields', None)
    st.rerun()

pipeline: list[dict] = st.session_state['nj_pipeline']

if pipeline:
    st.write('**Pipeline blocks:**')
    for i, blk in enumerate(pipeline):
        bc1, bc2, bc3, bc4 = st.columns([5, 1, 1, 1])
        with bc1:
            if blk['type'] == 'structure':
                schema_len = len(blk['params'].get('schema', []))
                fmt = blk['params'].get('output_format', 'json')
                preview = f'schema: {schema_len} field(s), format: {fmt}'
            elif blk['params']:
                preview = json.dumps(blk['params'])
            else:
                preview = 'no params'
            st.write(f'`{i + 1}. {blk["type"]}` — {preview}')
        with bc2:
            if i > 0 and st.button('↑', key=f'up_{i}'):
                pipeline[i - 1], pipeline[i] = blk, pipeline[i - 1]
                st.rerun()
        with bc3:
            if i < len(pipeline) - 1 and st.button('↓', key=f'dn_{i}'):
                pipeline[i + 1], pipeline[i] = blk, pipeline[i + 1]
                st.rerun()
        with bc4:
            if st.button('✕', key=f'rm_{i}'):
                pipeline.pop(i)
                st.rerun()
else:
    st.info('No blocks added — files will pass through unchanged (identity pipeline).')

st.divider()
if st.button(
    'Create Job', type='primary', use_container_width=True, disabled=not title.strip()
):
    resp = api_client.create_job(
        title=title.strip(),
        pipeline_config=pipeline,
    )
    if resp.status_code == 201:
        job = resp.json()
        st.session_state['selected_job_id'] = job['id']
        st.session_state.pop('nj_pipeline', None)
        st.session_state.pop('nj_struct_fields', None)
        st.success('Job created! Redirecting…')
        st.switch_page('pages/Job_Detail.py')
    else:
        try:
            detail = resp.json().get('detail', resp.text or f'HTTP {resp.status_code}')
        except Exception:  # noqa: BLE001
            detail = resp.text or f'HTTP {resp.status_code}'
        st.error(f'Failed to create job: {detail}')
