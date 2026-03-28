"""Streamlit frontend for the Recipe RAG Knowledge Graph.

Run with:
    cd frontend
    streamlit run app.py
"""

from pathlib import Path

import streamlit as st

from api_client import check_health, stream_chat
from components import dedup_tools, render_empty_state, render_health_indicator, render_tool_card
from config import config
from styles import get_carbon_css

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=config.app_title,
    page_icon="\U0001F373",
    layout="centered",
    initial_sidebar_state="auto",
)

st.markdown(get_carbon_css(), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "session_id": None,
    "last_response": None,
    "last_tools": [],
    "last_query": None,
    "_just_streamed": False,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## Search Tools")

    if st.session_state.last_tools:
        for tool in dedup_tools(st.session_state.last_tools):
            st.markdown(render_tool_card(tool), unsafe_allow_html=True)
    else:
        st.caption("Tools used in the last query will appear here.")

    st.markdown("---")

    if st.button("New Search"):
        for key, default in _DEFAULTS.items():
            st.session_state[key] = default
        st.rerun()

    st.markdown("---")

    @st.cache_data(ttl=30)
    def _cached_health(base_url: str) -> dict | None:
        return check_health(base_url)

    health = _cached_health(config.api_base_url)
    st.markdown(render_health_indicator(health), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main area - header
# ---------------------------------------------------------------------------

_logo = Path(__file__).parent / "chef_recipe_logo_white.png"
if _logo.exists():
    _col1, _col2, _col3 = st.columns([1, 0.5, 1])
    with _col2:
        st.image(str(_logo), width=120)
st.title(config.app_title)
st.markdown(f'<p class="subtitle">{config.app_subtitle}</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Search form
# ---------------------------------------------------------------------------

with st.form("search_form", clear_on_submit=True):
    query = st.text_input(
        "Query",
        placeholder="Ask about recipes, ingredients, cuisines, or techniques...",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Search")

# ---------------------------------------------------------------------------
# Handle submission
# ---------------------------------------------------------------------------

if submitted and query.strip():
    text_generator, result = stream_chat(
        base_url=config.api_base_url,
        message=query.strip(),
        session_id=st.session_state.session_id,
        timeout=config.request_timeout,
    )

    st.markdown("---")
    st.write_stream(text_generator)

    # Check for errors surfaced during streaming
    if result.error:
        st.error(result.error)

    # Persist results in session state
    st.session_state.session_id = result.session_id or st.session_state.session_id
    st.session_state.last_tools = result.tools
    st.session_state.last_response = result.full_text
    st.session_state.last_query = query.strip()
    st.session_state._just_streamed = True

    # Rerun so the sidebar refreshes with tool cards
    st.rerun()

# ---------------------------------------------------------------------------
# Display previous response (after rerun) or empty state
# ---------------------------------------------------------------------------

elif st.session_state._just_streamed and st.session_state.last_response:
    st.markdown("---")
    st.markdown(st.session_state.last_response)
    st.session_state._just_streamed = False

elif st.session_state.last_response:
    st.markdown("---")
    st.markdown(st.session_state.last_response)

else:
    st.markdown(render_empty_state(), unsafe_allow_html=True)
