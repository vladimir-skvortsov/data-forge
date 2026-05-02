import streamlit as st

import auth

st.set_page_config(
    page_title='DataForge',
    page_icon='⚙️',
    layout='wide',
)


def _login_page() -> None:
    st.markdown(
        """
        <div style='text-align:center; padding: 3rem 0 1.5rem 0'>
            <h1 style='font-size:2.5rem; margin-bottom:0'>⚙️ DataForge</h1>
            <p style='color: #888; margin-top:0.25rem'>Automatic document structuring service</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col, _ = st.columns([1, 1])
    with col:
        tab_login, tab_register = st.tabs(['Sign In', 'Sign Up'])

        with tab_login:
            with st.form('login_form'):
                email = st.text_input('Email', placeholder='you@example.com')
                password = st.text_input('Password', type='password')
                submitted = st.form_submit_button(
                    'Sign In', use_container_width=True, type='primary'
                )
            if submitted:
                if not email or not password:
                    st.error('Please fill in all fields.')
                else:
                    result = auth.login(email, password)
                    if result is True:
                        st.rerun()
                    else:
                        st.error(result)

        with tab_register:
            with st.form('register_form'):
                reg_email = st.text_input(
                    'Email', placeholder='you@example.com', key='reg_email'
                )
                reg_password = st.text_input(
                    'Password', type='password', key='reg_password'
                )
                reg_submitted = st.form_submit_button(
                    'Create Account', use_container_width=True, type='primary'
                )
            if reg_submitted:
                if not reg_email or not reg_password:
                    st.error('Please fill in all fields.')
                elif len(reg_password) < 8:
                    st.error('Password must be at least 8 characters.')
                else:
                    result = auth.do_register(reg_email, reg_password)
                    if result is True:
                        st.rerun()
                    else:
                        st.error(result)


if auth.is_authenticated():
    pg = st.navigation(
        [
            st.Page('pages/Dashboard.py', title='Dashboard', icon='🏠', default=True),
            st.Page('pages/New_Job.py', title='New Job', icon='➕'),
            st.Page('pages/Job_Detail.py', title='Job Detail', icon='📄'),
        ]
    )
else:
    pg = st.navigation(
        [st.Page(_login_page, title='Sign In', default=True)],
        position='hidden',
    )

pg.run()
