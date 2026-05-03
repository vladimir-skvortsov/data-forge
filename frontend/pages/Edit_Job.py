import streamlit as st

import api_client
import pipeline_builder

PREFIX = 'ej'

job_id = st.session_state.get('selected_job_id')
if not job_id:
    st.error('No job selected. Please open a job from the Dashboard.')
    st.stop()

job_resp = api_client.get_job(job_id)
if job_resp.status_code == 404:
    st.error('Job not found.')
    st.stop()
if job_resp.status_code == 403:
    st.error('Access denied.')
    st.stop()
if job_resp.status_code != 200:
    st.error('Failed to load job.')
    st.stop()

job = job_resp.json()

if job['status'] in ('pending', 'processing'):
    st.warning('Job is currently running — editing is disabled.')
    st.stop()

# Seed edit pipeline from job on first load (or after explicit reset)
if (
    f'{PREFIX}_pipeline' not in st.session_state
    or st.session_state.get(f'{PREFIX}_job_id') != job_id
):
    st.session_state[f'{PREFIX}_pipeline'] = list(job.get('pipeline_config', []))
    st.session_state[f'{PREFIX}_job_id'] = job_id

col_back, col_title = st.columns([1, 6])
with col_back:
    if st.button('Back'):
        st.switch_page('pages/Job_Detail.py')
with col_title:
    st.header(f'Edit — {job["title"]}')

new_title = st.text_input('Title', value=job['title'], key=f'{PREFIX}_title')

st.subheader('Pipeline')

pipeline: list[dict] = st.session_state[f'{PREFIX}_pipeline']
if pipeline:
    pipeline_builder.render_pipeline_editor(PREFIX)
else:
    st.info('No blocks — files will pass through unchanged (identity pipeline).')

pipeline_builder.render_block_adder(PREFIX)

st.divider()
if st.button('Save', type='primary', use_container_width=True):
    patch_resp = api_client.update_job(
        job_id,
        title=new_title.strip() if new_title.strip() != job['title'] else None,
        pipeline_config=st.session_state[f'{PREFIX}_pipeline'],
    )
    if patch_resp.status_code == 200:
        st.session_state.pop(f'{PREFIX}_pipeline', None)
        st.session_state.pop(f'{PREFIX}_job_id', None)
        st.success('Saved.')
        st.switch_page('pages/Job_Detail.py')
    elif patch_resp.status_code == 409:
        st.error(patch_resp.json().get('detail', 'Conflict'))
    else:
        st.error('Failed to save changes.')
