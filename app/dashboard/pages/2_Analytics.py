import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from db import get_analytics_summary

st.title("Analytics")

summary = get_analytics_summary()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total audio uploads", summary["total_jobs"])
col2.metric("Total content generated", summary["total_content_items"])
col3.metric("Approved", summary["approved_items"])
col4.metric("Scheduled", summary["scheduled_items"])

st.divider()

col5, col6 = st.columns(2)
col5.metric("Rejected", summary["rejected_items"])
col6.metric("Still in draft (awaiting review)", summary["draft_items"])

st.divider()

st.subheader("Content by platform")

TYPE_LABELS = {
    "facebook_post": "Facebook",
    "linkedin_post": "LinkedIn",
    "x_post": "X (Twitter)",
    "news_article": "News Article",
    "reel_idea": "Instagram Reels",
    "youtube_idea": "YouTube",
}

type_counts = summary["type_counts"]
if type_counts:
    for content_type, count in type_counts.items():
        st.write(f"**{TYPE_LABELS.get(content_type, content_type)}**: {count}")
else:
    st.caption("No content generated yet.")