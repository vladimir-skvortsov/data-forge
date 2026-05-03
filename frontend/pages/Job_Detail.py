import time

import pandas as pd
import streamlit as st

import api_client

_STATUS_ICON: dict[str, str] = {
    'draft': '⬜',
    'pending': '🟡',
    'processing': '🔵',
    'completed': '✅',
    'failed': '❌',
}
_FILE_STATUS_ICON = {'queued': '⬜', 'processing': '🔵', 'done': '✅', 'failed': '❌'}

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
icon = _STATUS_ICON.get(status, '⬜')
is_running = status in ('pending', 'processing')
has_files = bool(job.get('files'))

col_title, col_run = st.columns([5, 1])
with col_title:
    st.header(job['title'])
with col_run:
    st.write('')  # vertical nudge
    btn_label = f'⏳ {status.capitalize()}…' if is_running else 'Run'
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

# ── Status metrics ─────────────────────────────────────────────────────────────
col_s, col_e, col_c = st.columns(3)
with col_s:
    st.metric('Status', f'{icon} {status.upper()}')
with col_e:
    st.metric('Credits Estimate', job.get('credits_estimate') or '—')
with col_c:
    st.metric('Credits Charged', job.get('credits_charged') or '—')

if status == 'failed' and job.get('error_message'):
    with st.expander('Error Details', expanded=True):
        st.code(job['error_message'], language='text')

if status == 'draft' and has_files:
    est_resp = api_client.get_estimate(job_id)
    if est_resp.status_code == 200:
        est = est_resp.json()
        with st.expander(
            f'💰 Estimate: **{est["total_credits"]} credits**'
            f' (balance: {est["current_balance"]})',
            expanded=False,
        ):
            for item in est.get('breakdown', []):
                st.write(f'• {item["item"]} — {item["credits"]:.2f} credits')
        if not est['can_proceed']:
            st.warning('Insufficient balance. Please top up your account.')

if status == 'draft':
    st.subheader('Upload Files')
    uploaded = st.file_uploader(
        'Choose files',
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

files = job.get('files', [])
if files:
    st.subheader('Files')
    for file_info in files:
        f_icon = _FILE_STATUS_ICON.get(file_info['status'], '⬜')
        size_kb = file_info['file_size_bytes'] // 1024
        st.write(
            f'{f_icon} `{file_info["original_name"]}` — {size_kb} KB'
            f' ({file_info["file_type"]}, {file_info["status"]})'
        )

pipeline = job.get('pipeline_config', [])
if pipeline:
    with st.expander('Pipeline', expanded=False):
        for i, block in enumerate(pipeline):
            st.write(f'`{i + 1}. {block["type"]}`')
else:
    st.caption('Identity pipeline (no processing blocks).')

if status == 'completed':
    st.subheader('Results')
    result_resp = api_client.get_result(job_id)

    if result_resp.status_code == 200:
        records = result_resp.json()
        structured = [r for r in records if r.get('structured')]

        col_r, col_d = st.columns([3, 1])
        col_r.success(
            f'{len(records)} record(s) processed, {len(structured)} structured.'
        )
        with col_d:
            dl_resp = api_client.download_result(job_id)
            if dl_resp.status_code == 200:
                ext = job.get('schema_config', {}).get('output_format', 'json')
                st.download_button(
                    '⬇ Download',
                    data=dl_resp.content,
                    file_name=f'result_{job_id[:8]}.{ext}',
                    use_container_width=True,
                )

        if structured:
            tab_table, tab_json = st.tabs(['Table', 'JSON'])
            with tab_table:
                try:
                    df = pd.DataFrame([r['structured'] for r in structured])
                    st.dataframe(df, use_container_width=True)
                except Exception:  # noqa: BLE001
                    st.warning('Could not render as table — showing raw JSON.')
                    st.json([r['structured'] for r in structured])
            with tab_json:
                st.json(records)
        else:
            st.write(
                'No structured data — files were processed without the Structure block.'
            )
            for r in records:
                st.write(
                    f'• `{r.get("file", "file")}` → `{r.get("processed_path", "—")}`'
                )
    elif result_resp.status_code == 409:
        st.warning(result_resp.json().get('detail', 'Result not available yet.'))
    else:
        st.error('Could not fetch results.')

if is_running:
    with st.spinner(f'Job is {status}… refreshing in 5 s'):
        time.sleep(5)
    st.rerun()
