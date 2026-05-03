import time

import streamlit as st

import api_client

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
status = job['status']
is_running = status in ('pending', 'processing')
has_files = bool(job.get('files'))
can_edit = not is_running

# ── Title row ─────────────────────────────────────────────────────────────────
col_title, col_edit, col_run = st.columns([5, 1, 1])
with col_title:
    st.header(job['title'])
with col_edit:
    st.write('')
    if st.button('Edit', disabled=is_running, use_container_width=True):
        st.switch_page('pages/Edit_Job.py')
with col_run:
    st.write('')
    btn_label = f'{status.capitalize()}...' if is_running else 'Run'
    run_clicked = st.button(
        btn_label,
        type='primary',
        disabled=is_running or not has_files,
        use_container_width=True,
        help='Upload at least one file to enable.' if not has_files else None,
    )

if run_clicked:
    est_resp = api_client.get_estimate(job_id)
    if est_resp.status_code == 200 and not est_resp.json().get('can_proceed'):
        st.error('Insufficient balance. Please top up your account.')
    else:
        run_resp = api_client.run_job(job_id)
        if run_resp.status_code == 200:
            run_data = run_resp.json()
            st.success(f'Job started! {run_data["credits_held"]} credits held.')
            st.rerun()
        elif run_resp.status_code == 402:
            st.error('Insufficient balance. Please top up your account.')
        elif run_resp.status_code == 409:
            st.error(run_resp.json().get('detail', 'Conflict'))
        else:
            st.error('Failed to start job.')

# ── Metrics ───────────────────────────────────────────────────────────────────
col_s, col_e, col_c = st.columns(3)
with col_s:
    st.metric('Status', status.capitalize())
with col_e:
    st.metric('Credits estimate', job.get('credits_estimate') or '—')
with col_c:
    st.metric('Credits charged', job.get('credits_charged') or '—')

if status == 'failed' and job.get('error_message'):
    with st.expander('Error Details', expanded=True):
        st.code(job['error_message'], language='text')

if status == 'draft' and has_files:
    est_resp = api_client.get_estimate(job_id)
    if est_resp.status_code == 200:
        est = est_resp.json()
        with st.expander(
            f'Estimate: **{est["total_credits"]} credits**'
            f' (balance: {est["current_balance"]})',
            expanded=False,
        ):
            for item in est.get('breakdown', []):
                st.write(f'• {item["item"]} — {item["credits"]:.2f} credits')
        if not est['can_proceed']:
            st.warning('Insufficient balance. Please top up your account.')

# ── Files ─────────────────────────────────────────────────────────────────────
st.subheader('Files')

files = job.get('files', [])
for file_info in files:
    size_kb = file_info['file_size_bytes'] // 1024
    fc1, fc2 = st.columns([8, 1])
    with fc1:
        st.write(
            f'`{file_info["original_name"]}` — {size_kb} KB'
            f' ({file_info["file_type"]}, {file_info["status"]})'
        )
    with fc2:
        if can_edit and st.button(
            '✕',
            key=f'del_file_{file_info["id"]}',
            help='Remove file',
            use_container_width=True,
        ):
            resp = api_client.delete_file(job_id, file_info['id'])
            if resp.status_code == 204:
                st.rerun()
            else:
                st.error('Failed to remove file.')

if can_edit:
    uploaded = st.file_uploader(
        'Add files',
        accept_multiple_files=True,
        type=[
            'txt',
            'pdf',
            'docx',
            'csv',
            'md',
            'png',
            'jpg',
            'jpeg',
            'webp',
            'mp3',
            'wav',
            'm4a',
            'ogg',
        ],
        label_visibility='collapsed',
    )
    if uploaded:
        if st.button('Upload', type='primary'):
            progress = st.progress(0, text='Uploading…')
            errors: list[str] = []
            for i, f in enumerate(uploaded):
                resp = api_client.upload_file(job_id, f.read(), f.name)
                if resp.status_code not in (200, 201):
                    detail = resp.json().get('detail', 'error')
                    errors.append(f'`{f.name}`: {detail}')
                progress.progress((i + 1) / len(uploaded), text=f'Uploading {f.name}…')
            if errors:
                for err in errors:
                    st.error(err)
            else:
                st.success(f'Uploaded {len(uploaded)} file(s).')
            st.rerun()

# ── Pipeline ──────────────────────────────────────────────────────────────────
pipeline = job.get('pipeline_config', [])
with st.expander('Pipeline', expanded=False):
    if pipeline:
        for i, block in enumerate(pipeline):
            st.write(f'`{i + 1}. {block["type"]}`')
    else:
        st.caption('Identity pipeline (no processing blocks).')

# ── Download ──────────────────────────────────────────────────────────────────
if status == 'completed':
    dl_resp = api_client.download_result(job_id)
    if dl_resp.status_code == 200:
        st.download_button(
            'Download results',
            data=dl_resp.content,
            file_name=f'result_{job_id[:8]}.zip',
            mime='application/zip',
        )

if is_running:
    with st.spinner(f'Job is {status}… refreshing in 5 s'):
        time.sleep(5)
    st.rerun()
