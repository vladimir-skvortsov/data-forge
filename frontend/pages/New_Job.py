import streamlit as st

import api_client
import pipeline_builder

PREFIX = 'nj'

if f'{PREFIX}_pipeline' not in st.session_state:
    st.session_state[f'{PREFIX}_pipeline'] = []

st.header('Create New Job')

st.subheader('1. Job Details')
title = st.text_input('Job Title', placeholder='My data extraction job')

st.subheader('2. Pipeline')

pipeline_builder.render_block_adder(PREFIX)

pipeline: list[dict] = st.session_state[f'{PREFIX}_pipeline']
if pipeline:
    st.write('**Pipeline blocks:**')
    pipeline_builder.render_pipeline_editor(PREFIX)
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
        st.session_state.pop(f'{PREFIX}_pipeline', None)
        st.session_state.pop(f'{PREFIX}_struct_fields', None)
        st.success('Job created! Redirecting…')
        st.switch_page('pages/Job_Detail.py')
    else:
        try:
            detail = resp.json().get('detail', resp.text or f'HTTP {resp.status_code}')
        except Exception:
            detail = f'HTTP {resp.status_code}'
        st.error(f'Failed to create job: {detail}')
