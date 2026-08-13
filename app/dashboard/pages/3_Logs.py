import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from db import get_logs, get_all_jobs

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Pipeline Logs")

jobs = {job.id: job.file_name for job in get_all_jobs()}

logs = get_logs()

if not logs:
    st.info("No logs yet.")
    st.stop()

for log in logs:
    icon = "✅" if log.status == "success" else "❌"
    job_label = jobs.get(log.job_id, f"Job #{log.job_id}")
    with st.container(border=True):
        st.write(f"{icon} **{log.stage}** — {job_label} — {log.created_at.strftime('%b %d, %Y %I:%M %p')}")
        if log.message:
            st.caption(log.message)