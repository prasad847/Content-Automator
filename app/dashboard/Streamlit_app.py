import streamlit as st

pages = [
    st.Page("app.py", title="App", icon="🏠", default=True),
    st.Page("pages/1_scheduled_posts.py", title="Schedule Posts", icon="📅", url_path="Scheduled_Posts"),
    st.Page("pages/2_Analytics.py", title="Analytics", icon="📊"),
    st.Page("pages/3_Logs.py", title="Logs", icon="📋"),
    st.Page("pages/4_Connections.py", title="Connections", icon="🔗"),
]

# Navigation UI is hidden and rebuilt manually below with st.page_link so the
# "Content Automator" title can sit above the nav links - st.navigation still
# owns routing/URLs exactly as before, only the auto-rendered link list is off.
nav = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown("""
    <div class='sidebar-brand'>
        <h2>🚀 Content Automator</h2>
    </div>
    """, unsafe_allow_html=True)

    for page in pages:
        st.page_link(page, icon_position="right")

nav.run()
