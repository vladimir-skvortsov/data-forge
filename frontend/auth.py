import streamlit as st

import api_client

_TOKEN_KEY = 'access_token'
_REFRESH_KEY = 'refresh_token'
_USER_KEY = 'user_email'


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
        return True
    try:
        detail = resp.json().get('detail', 'Invalid email or password')
    except Exception:
        detail = 'Login failed'
    return str(detail)


def do_register(email: str, password: str) -> bool | str:
    resp = api_client.register(email, password)
    if resp.status_code == 201:
        return login(email, password)
    try:
        detail = resp.json().get('detail', 'Registration failed')
    except Exception:
        detail = 'Registration failed'
    return str(detail)


def logout() -> None:
    st.session_state.clear()
    st.switch_page('app.py')
