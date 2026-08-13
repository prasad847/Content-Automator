import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from db import get_connection
from services.facebook_service import get_login_url

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Connections")

st.subheader("📘 Facebook")

connection = get_connection("facebook")
if connection:
    st.success(f"Connected — Page ID: {connection.page_id}")
else:
    st.warning("Not connected.")

st.link_button("Connect Facebook", get_login_url())
st.caption(
    "Opens Facebook's login dialog. After you approve, Facebook redirects to the "
    "OAuth callback server (see routers/facebook.py) which saves the connection. "
    "Refresh this page afterward to see the updated status."
)
