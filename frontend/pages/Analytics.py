from __future__ import annotations

import pandas as pd
import streamlit as st

import api_client

st.title('Analytics')

resp = api_client.get_stats()
if resp.status_code != 200:
    st.error('Failed to load stats')
    st.stop()

data = resp.json()

total_spent = float(data.get('total_credits_spent', 0))
jobs_by_status: dict[str, int] = data.get('jobs_by_status', {})
total_jobs = sum(jobs_by_status.values())

col1, col2, col3 = st.columns(3)
col1.metric('Total jobs', total_jobs)
col2.metric('Completed', jobs_by_status.get('completed', 0))
col3.metric('Credits spent', f'{total_spent:.1f}')

st.divider()

st.subheader('Jobs by status')
if jobs_by_status:
    df_status = pd.DataFrame(
        list(jobs_by_status.items()), columns=['Status', 'Count']
    ).set_index('Status')
    st.bar_chart(df_status)
else:
    st.info('No jobs yet.')

st.subheader('Credits spent (last 30 days)')
credits_by_day: list[dict] = data.get('credits_by_day', [])
if credits_by_day:
    df_credits = (
        pd.DataFrame(credits_by_day)
        .rename(columns={'date': 'Date', 'credits': 'Credits'})
        .set_index('Date')
    )
    st.line_chart(df_credits)
else:
    st.info('No spending data yet.')

st.subheader('Top file types')
top_file_types: list[dict] = data.get('top_file_types', [])
if top_file_types:
    df_types = (
        pd.DataFrame(top_file_types)
        .rename(columns={'file_type': 'Type', 'count': 'Count'})
        .set_index('Type')
    )
    st.bar_chart(df_types)
else:
    st.info('No files uploaded yet.')
