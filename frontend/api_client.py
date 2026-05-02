from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
_TIMEOUT = 30.0
_UPLOAD_TIMEOUT = 120.0


def _token() -> str:
    return str(st.session_state.get('access_token', ''))


def _auth_headers() -> dict[str, str]:
    token = _token()
    return {'Authorization': f'Bearer {token}'} if token else {}


def _url(path: str) -> str:
    return f'{BACKEND_URL}{path}'


def _get(path: str) -> httpx.Response:
    return httpx.get(_url(path), headers=_auth_headers(), timeout=_TIMEOUT)


def _post(path: str, **kwargs: Any) -> httpx.Response:
    return httpx.post(_url(path), headers=_auth_headers(), timeout=_TIMEOUT, **kwargs)


def _delete(path: str) -> httpx.Response:
    return httpx.delete(_url(path), headers=_auth_headers(), timeout=_TIMEOUT)


def login(email: str, password: str) -> httpx.Response:
    return httpx.post(
        _url('/api/v1/auth/login'),
        json={'email': email, 'password': password},
        timeout=_TIMEOUT,
    )


def register(email: str, password: str) -> httpx.Response:
    return httpx.post(
        _url('/api/v1/auth/register'),
        json={'email': email, 'password': password},
        timeout=_TIMEOUT,
    )


def me() -> httpx.Response:
    return _get('/api/v1/auth/me')


def get_balance() -> httpx.Response:
    return _get('/api/v1/billing/balance')


def topup(amount: float) -> httpx.Response:
    return _post('/api/v1/billing/topup', json={'amount': str(amount)})


def activate_promo(code: str) -> httpx.Response:
    return _post('/api/v1/billing/promo', json={'code': code})


def get_transactions() -> httpx.Response:
    return _get('/api/v1/billing/transactions')


def list_jobs() -> httpx.Response:
    return _get('/api/v1/jobs')


def create_job(
    title: str,
    schema_config: dict[str, Any],
    pipeline_config: list[dict[str, Any]],
) -> httpx.Response:
    return _post(
        '/api/v1/jobs',
        json={
            'title': title,
            'schema_config': schema_config,
            'pipeline_config': pipeline_config,
        },
    )


def get_job(job_id: str) -> httpx.Response:
    return _get(f'/api/v1/jobs/{job_id}')


def delete_job(job_id: str) -> httpx.Response:
    return _delete(f'/api/v1/jobs/{job_id}')


def upload_file(job_id: str, content: bytes, filename: str) -> httpx.Response:
    return httpx.post(
        _url(f'/api/v1/jobs/{job_id}/files'),
        files={'file': (filename, content, 'application/octet-stream')},
        headers=_auth_headers(),
        timeout=_UPLOAD_TIMEOUT,
    )


def run_job(job_id: str) -> httpx.Response:
    return _post(f'/api/v1/jobs/{job_id}/run')


def get_result(job_id: str) -> httpx.Response:
    return _get(f'/api/v1/jobs/{job_id}/result')


def get_estimate(job_id: str) -> httpx.Response:
    return _get(f'/api/v1/jobs/{job_id}/estimate')


def download_result(job_id: str) -> httpx.Response:
    return _get(f'/api/v1/jobs/{job_id}/download')


def get_stats() -> httpx.Response:
    return _get('/api/v1/dashboard/stats')
