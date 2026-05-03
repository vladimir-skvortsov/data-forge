import uuid

import streamlit as st

import api_client

_TOKEN_KEY = 'access_token'
_REFRESH_KEY = 'refresh_token'
_USER_KEY = 'user_email'
_PARAM_KEY = 'session'

# Server-side session store — survives browser refreshes, cleared on server restart.
_SESSIONS: dict[str, dict[str, str]] = {}


def init_from_session_param() -> None:
    """Restore auth state from the ?session= query param after a hard page reload."""
    if st.session_state.get(_TOKEN_KEY):
        return
    session_id = st.query_params.get(_PARAM_KEY)
    if session_id and session_id in _SESSIONS:
        data = _SESSIONS[session_id]
        st.session_state[_TOKEN_KEY] = data['access_token']
        st.session_state[_REFRESH_KEY] = data['refresh_token']
        st.session_state[_USER_KEY] = data['user_email']


def is_authenticated() -> bool:
    return bool(st.session_state.get(_TOKEN_KEY))


def require_auth() -> None:
    if not is_authenticated():
        st.rerun()


def login(email: str, password: str) -> bool | str:
    resp = api_client.login(email, password)
    if resp.status_code == 200:
        data = resp.json()
        st.session_state[_TOKEN_KEY] = data['access_token']
        st.session_state[_REFRESH_KEY] = data['refresh_token']
        st.session_state[_USER_KEY] = email
        session_id = str(uuid.uuid4())
        _SESSIONS[session_id] = {
            'access_token': data['access_token'],
            'refresh_token': data['refresh_token'],
            'user_email': email,
        }
        st.query_params[_PARAM_KEY] = session_id
        return True
    try:
        detail = resp.json().get('detail', 'Invalid email or password')
    except Exception:  # noqa: BLE001
        detail = 'Login failed'
    return str(detail)


def do_register(email: str, password: str) -> bool | str:
    resp = api_client.register(email, password)
    if resp.status_code == 201:
        return login(email, password)
    try:
        detail = resp.json().get('detail', 'Registration failed')
    except Exception:  # noqa: BLE001
        detail = 'Registration failed'
    return str(detail)


def logout() -> None:
    session_id = st.query_params.get(_PARAM_KEY)
    if session_id:
        _SESSIONS.pop(session_id, None)
    st.query_params.clear()
    st.session_state.clear()
    st.switch_page('app.py')
