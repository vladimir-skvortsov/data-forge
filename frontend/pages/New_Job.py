import json

import streamlit as st

import api_client

if 'nj_schema_fields' not in st.session_state:
    st.session_state['nj_schema_fields'] = []
if 'nj_pipeline' not in st.session_state:
    st.session_state['nj_pipeline'] = []

st.header('Create New Job')

st.subheader('1. Job Details')
title = st.text_input('Job Title', placeholder='My data extraction job')
output_format = st.selectbox('Output Format', ['json', 'csv', 'yaml', 'parquet'])

st.subheader('2. Schema Definition')
schema_mode = st.radio('Mode', ['Visual Builder', 'JSON Editor'], horizontal=True)

schema_config: dict = {}

if schema_mode == 'Visual Builder':
    with st.expander(
        'Add Field',
        expanded=len(st.session_state['nj_schema_fields']) == 0,
    ):
        fc1, fc2, fc3 = st.columns([2, 1, 2])
        with fc1:
            f_name = st.text_input('Field Name', key='f_name')
        with fc2:
            f_type = st.selectbox(
                'Type',
                ['string', 'integer', 'float', 'boolean', 'array'],
                key='f_type',
            )
        with fc3:
            f_desc = st.text_input('Description (optional)', key='f_desc')

        if st.button('Add Field', disabled=not f_name):
            st.session_state['nj_schema_fields'].append(
                {'name': f_name, 'type': f_type, 'description': f_desc}
            )
            st.rerun()

    fields = st.session_state['nj_schema_fields']
    if fields:
        st.write('**Fields:**')
        for i, field in enumerate(fields):
            rc1, rc2 = st.columns([8, 1])
            with rc1:
                st.write(
                    f'• `{field["name"]}` ({field["type"]})'
                    + (f' — {field["description"]}' if field['description'] else '')
                )
            with rc2:
                if st.button('✕', key=f'del_field_{i}'):
                    st.session_state['nj_schema_fields'].pop(i)
                    st.rerun()
    else:
        st.caption('No fields defined — LLM will infer structure from context.')

    schema_config = {
        'output_format': output_format,
        'fields': st.session_state['nj_schema_fields'],
    }

else:
    default_schema = json.dumps(
        {'output_format': output_format, 'fields': []}, indent=2
    )
    raw = st.text_area('Schema JSON', value=default_schema, height=220)
    try:
        schema_config = json.loads(raw)
        schema_config.setdefault('output_format', output_format)
    except json.JSONDecodeError:
        st.error('Invalid JSON — fix it before creating the job.')
        schema_config = {}

st.subheader('3. Pipeline')

_BLOCKS: dict[str, list[tuple[str, str, dict]]] = {
    'Image': [
        ('image_resize', 'Resize', {'width': 800, 'height': 600}),
        ('image_upscale', 'Upscale', {'factor': 2}),
        (
            'image_enhance',
            'Enhance',
            {'brightness': 1.2, 'contrast': 1.1, 'sharpness': 1.0},
        ),
        ('image_grayscale', 'Grayscale', {}),
    ],
    'Audio': [
        (
            'audio_remove_silence',
            'Remove Silence',
            {'min_silence_len': 1000, 'silence_thresh': -40},
        ),
        ('audio_normalize', 'Normalize Volume', {'target_dbfs': -20.0}),
        ('audio_boost_volume', 'Boost Volume', {'db': 6.0}),
        ('audio_denoise', 'Denoise', {}),
    ],
    'Text': [
        ('extract_text', 'Extract Text', {}),
        ('translate', 'Translate', {'target_lang': 'en'}),
        ('lemmatize', 'Lemmatize', {'lang': 'en'}),
        ('remove_stopwords', 'Remove Stopwords', {'lang': 'en'}),
    ],
    'Structuring': [
        ('structure', 'Structure (LLM)', {}),
    ],
    'Post-processing': [
        ('deduplicate', 'Deduplicate', {}),
        ('remove_outliers', 'Remove Outliers', {}),
    ],
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

selected_type, selected_label, default_params = options[blk_idx]

with st.expander('Block Parameters', expanded=bool(default_params)):
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

if st.button('＋ Add Block', type='primary'):
    st.session_state['nj_pipeline'].append(
        {'type': selected_type, 'params': block_params}
    )
    st.rerun()

pipeline: list[dict] = st.session_state['nj_pipeline']

if pipeline:
    st.write('**Pipeline blocks:**')
    for i, blk in enumerate(pipeline):
        bc1, bc2, bc3, bc4 = st.columns([5, 1, 1, 1])
        with bc1:
            params_preview = json.dumps(blk['params']) if blk['params'] else 'no params'
            st.write(f'`{i + 1}. {blk["type"]}` — {params_preview}')
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
can_create = bool(title.strip()) and bool(schema_config)
if st.button(
    'Create Job', type='primary', use_container_width=True, disabled=not can_create
):
    resp = api_client.create_job(
        title=title.strip(),
        schema_config=schema_config,
        pipeline_config=pipeline,
    )
    if resp.status_code == 201:
        job = resp.json()
        st.session_state['selected_job_id'] = job['id']
        # Reset wizard state
        del st.session_state['nj_schema_fields']
        del st.session_state['nj_pipeline']
        st.success('Job created! Redirecting…')
        st.switch_page('pages/Job_Detail.py')
    else:
        detail = resp.json().get('detail', 'Unknown error')
        st.error(f'Failed to create job: {detail}')
