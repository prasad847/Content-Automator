import streamlit as st

with st.sidebar:
    st.markdown("""
    <div style='padding:10px 0 20px 0;'>
        <h2 style='margin-bottom:0;color:#1C1C28;'>🚀 Content Studio</h2>
        <p style='color:#6B6B7B;margin-top:4px;font-size:13px;'>
            AI Content Automation
        </p>
    </div>
    """, unsafe_allow_html=True)

pages = [
    st.Page("app.py", title="Dashboard", icon="🏠", default=True),
    st.Page("pages/1_scheduled_posts.py", title="Scheduled Posts", icon="📅"),
    st.Page("pages/2_Analytics.py", title="Analytics", icon="📊"),
    st.Page("pages/3_Logs.py", title="Logs", icon="📋"),
    st.Page("pages/4_Connections.py", title="Connections", icon="🔗"),
]

nav = st.navigation(pages)
nav.run()