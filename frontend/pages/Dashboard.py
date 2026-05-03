import streamlit as st

import api_client
import auth

with st.sidebar:
    st.caption(st.session_state.get('user_email', ''))

    balance_resp = api_client.get_balance()
    if balance_resp.status_code == 200:
        balance = balance_resp.json().get('balance', '—')
        st.metric('Credits', balance)
    else:
        st.metric('Credits', '—')

    with st.expander('Top up'):
        with st.form('topup_form', border=False):
            amount = st.number_input('Amount', min_value=1.0, value=10.0, step=1.0)
            if st.form_submit_button('Add credits', use_container_width=True):
                resp = api_client.topup(amount)
                if resp.status_code == 201:
                    st.success('Credits added!')
                    st.rerun()
                else:
                    detail = resp.json().get('detail', 'Top-up failed')
                    st.error(detail)

    with st.expander('Promo code'):
        with st.form('promo_form', border=False):
            code = st.text_input('Code')
            if st.form_submit_button('Apply', use_container_width=True):
                resp = api_client.activate_promo(code)
                if resp.status_code == 201:
                    st.success('Promo activated!')
                    st.rerun()
                else:
                    detail = resp.json().get('detail', 'Invalid code')
                    st.error(detail)

    st.divider()
    if st.button('Sign Out', use_container_width=True):
        auth.logout()

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.header('My Jobs')
with col_btn:
    st.write('')  # vertical align spacer
    if st.button('New job', type='primary', use_container_width=True):
        st.switch_page('pages/New_Job.py')

jobs_resp = api_client.list_jobs()

if jobs_resp.status_code != 200:
    st.error('Failed to load jobs.')
    st.stop()

jobs = jobs_resp.json().get('items', [])

if not jobs:
    st.info('No jobs yet. Click **New job** to get started.')
else:
    for job in jobs:
        file_count = len(job.get('files', []))
        created = job.get('created_at', '')[:10]
        estimate = job.get('credits_estimate')

        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                st.markdown(f'**{job["title"]}**')
                meta_parts = [
                    job['status'].capitalize(),
                    f'{file_count} file(s)',
                    created,
                ]
                if estimate:
                    meta_parts.append(f'{estimate} credits')
                st.caption(' · '.join(meta_parts))
            with c2:
                if st.button('View', key=f'view_{job["id"]}', use_container_width=True):
                    st.session_state['selected_job_id'] = job['id']
                    st.switch_page('pages/Job_Detail.py')
            with c3:
                confirm_key = f'confirm_del_{job["id"]}'
                if st.session_state.get(confirm_key):
                    if st.button(
                        'Sure?',
                        key=f'del_yes_{job["id"]}',
                        type='primary',
                        use_container_width=True,
                    ):
                        api_client.delete_job(job['id'])
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if st.button(
                        'Delete',
                        key=f'del_{job["id"]}',
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()
