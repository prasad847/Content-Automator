import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from db import get_scheduled_posts, get_all_jobs

st.title("Scheduled Posts")

items = get_scheduled_posts()

if not items:
    st.info("No approved, scheduled posts yet. Approve and schedule posts from the main Dashboard first.")
    st.stop()

jobs = {job.id: job.file_name for job in get_all_jobs()}

TYPE_LABELS = {
    "facebook_post": "Facebook",
    "linkedin_post": "LinkedIn",
    "x_post": "X (Twitter)",
    "news_article": "News Article",
    "reel_idea": "Instagram Reel",
    "youtube_idea": "YouTube",
}

for item in items:
    data = json.loads(item.content)
    preview = data.get("text") or data.get("headline") or data.get("hook") or data.get("seo_title") or "(no preview)"

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 3, 2])
        with col1:
            st.markdown(f"**{TYPE_LABELS.get(item.content_type, item.content_type)}** — Post {item.item_index}")
            st.caption(f"From job #{item.job_id} — {jobs.get(item.job_id, 'unknown file')}")
        with col2:
            st.write(preview[:150] + ("..." if len(preview) > 150 else ""))
        with col3:
            st.write(f"📅 {item.scheduled_at.strftime('%b %d, %Y — %I:%M %p')}")