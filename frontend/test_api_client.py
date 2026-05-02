import sys
from unittest.mock import MagicMock, patch

_mock_st = MagicMock()
_mock_st.session_state = {}
sys.modules['streamlit'] = _mock_st

import api_client  # noqa: E402  (must be after mock)


def _set_token(token: str | None) -> None:
    if token:
        _mock_st.session_state = {'access_token': token}
    else:
        _mock_st.session_state = {}


def test_auth_headers_with_token() -> None:
    _set_token('my-jwt')
    assert api_client._auth_headers() == {'Authorization': 'Bearer my-jwt'}


def test_auth_headers_empty_without_token() -> None:
    _set_token(None)
    assert api_client._auth_headers() == {}


def test_login_posts_to_correct_url() -> None:
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        api_client.login('a@b.com', 'secret')
    url = mock_post.call_args[0][0]
    assert url.endswith('/api/v1/auth/login')


def test_login_sends_credentials() -> None:
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        api_client.login('a@b.com', 'secret')
    kwargs = mock_post.call_args[1]
    assert kwargs['json'] == {'email': 'a@b.com', 'password': 'secret'}


def test_register_posts_to_correct_url() -> None:
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        api_client.register('a@b.com', 'secret')
    url = mock_post.call_args[0][0]
    assert url.endswith('/api/v1/auth/register')


def test_me_calls_get() -> None:
    _set_token('tok')
    with patch('api_client.httpx.get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        api_client.me()
    url = mock_get.call_args[0][0]
    assert url.endswith('/api/v1/auth/me')


def test_get_balance_calls_correct_url() -> None:
    _set_token('tok')
    with patch('api_client.httpx.get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        api_client.get_balance()
    url = mock_get.call_args[0][0]
    assert url.endswith('/api/v1/billing/balance')


def test_topup_sends_amount_as_string() -> None:
    _set_token('tok')
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        api_client.topup(50.0)
    kwargs = mock_post.call_args[1]
    assert kwargs['json']['amount'] == '50.0'


def test_activate_promo_sends_code() -> None:
    _set_token('tok')
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        api_client.activate_promo('PROMO123')
    kwargs = mock_post.call_args[1]
    assert kwargs['json']['code'] == 'PROMO123'


def test_list_jobs_calls_correct_url() -> None:
    _set_token('tok')
    with patch('api_client.httpx.get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        api_client.list_jobs()
    url = mock_get.call_args[0][0]
    assert url.endswith('/api/v1/jobs')


def test_create_job_sends_payload() -> None:
    _set_token('tok')
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        api_client.create_job(
            title='Test',
            schema_config={'fields': []},
            pipeline_config=[{'type': 'structure', 'params': {}}],
        )
    kwargs = mock_post.call_args[1]
    body = kwargs['json']
    assert body['title'] == 'Test'
    assert body['schema_config'] == {'fields': []}
    assert body['pipeline_config'][0]['type'] == 'structure'


def test_upload_file_posts_multipart() -> None:
    _set_token('tok')
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=201)
        api_client.upload_file('job-123', b'data', 'doc.pdf')
    url = mock_post.call_args[0][0]
    assert 'job-123' in url
    assert 'files' in url


def test_run_job_posts_to_run_url() -> None:
    _set_token('tok')
    with patch('api_client.httpx.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        api_client.run_job('job-456')
    url = mock_post.call_args[0][0]
    assert 'job-456' in url
    assert url.endswith('/run')


def test_get_result_calls_correct_url() -> None:
    _set_token('tok')
    with patch('api_client.httpx.get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        api_client.get_result('job-789')
    url = mock_get.call_args[0][0]
    assert 'job-789' in url
    assert url.endswith('/result')


def test_delete_job_calls_correct_url() -> None:
    _set_token('tok')
    with patch('api_client.httpx.delete') as mock_del:
        mock_del.return_value = MagicMock(status_code=204)
        api_client.delete_job('job-999')
    url = mock_del.call_args[0][0]
    assert 'job-999' in url


def test_authenticated_request_includes_bearer_header() -> None:
    _set_token('secret-token')
    with patch('api_client.httpx.get') as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        api_client.list_jobs()
    kwargs = mock_get.call_args[1]
    assert kwargs['headers'].get('Authorization') == 'Bearer secret-token'
