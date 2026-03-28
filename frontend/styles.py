"""IBM Carbon-inspired CSS styles for the Streamlit frontend."""


def get_carbon_css() -> str:
    """Return a <style> block with IBM Carbon Design-inspired styles."""
    return """
    <style>
    /* IBM Plex fonts */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    /* Global font override */
    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Reduce top padding on main content area */
    .stMainBlockContainer {
        padding-top: 1.5rem !important;
    }

    /* Logo container - override Streamlit element backgrounds */
    .stMarkdown img {
        background-color: #ffffff !important;
    }
    .element-container:has(img) {
        background: transparent !important;
    }

    /* Main title */
    h1 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 600 !important;
        color: #161616 !important;
        letter-spacing: -0.02em;
    }

    /* Subtitle text */
    .subtitle {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.95rem;
        color: #525252;
        margin-top: -0.8rem;
        margin-bottom: 1.5rem;
    }

    /* Text input - Carbon underline style */
    .stTextInput > div > div > input {
        font-family: 'IBM Plex Sans', sans-serif !important;
        border: none !important;
        border-bottom: 1px solid #e0e0e0 !important;
        border-radius: 0 !important;
        background-color: #f4f4f4 !important;
        padding: 0.75rem !important;
        font-size: 0.95rem !important;
        color: #161616 !important;
    }

    .stTextInput > div > div > input:focus {
        border-bottom: 2px solid #0f62fe !important;
        box-shadow: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #a8a8a8 !important;
    }

    /* Submit / Search button - Carbon primary */
    .stFormSubmitButton > button {
        font-family: 'IBM Plex Sans', sans-serif !important;
        background-color: #0f62fe !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0.75rem 2rem !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        text-transform: none !important;
        min-height: 2.5rem !important;
    }

    .stFormSubmitButton > button:hover {
        background-color: #0353e9 !important;
    }

    .stFormSubmitButton > button:active {
        background-color: #002d9c !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f4f4f4 !important;
        border-right: 1px solid #e0e0e0;
    }

    section[data-testid="stSidebar"] h2 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: #525252 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        margin-bottom: 0.75rem;
    }

    /* Tool card */
    .tool-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }

    .tool-card .tool-name {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        font-weight: 500;
        color: #0f62fe;
        margin-bottom: 0.35rem;
    }

    .tool-card .tool-args {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.75rem;
        color: #525252;
        line-height: 1.4;
    }

    .tool-card .tool-args .arg-key {
        color: #6f6f6f;
    }

    /* New Search button - Carbon ghost style */
    section[data-testid="stSidebar"] .stButton > button {
        font-family: 'IBM Plex Sans', sans-serif !important;
        background-color: transparent !important;
        color: #0f62fe !important;
        border: 1px solid #0f62fe !important;
        border-radius: 0 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
        width: 100%;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #0f62fe !important;
        color: #ffffff !important;
    }

    /* Health indicator */
    .health-indicator {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.75rem;
        color: #6f6f6f;
        padding: 0.5rem 0;
    }

    .health-indicator .dot-ok {
        color: #24a148;
    }

    .health-indicator .dot-err {
        color: #da1e28;
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
    }

    .empty-state .empty-title {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.1rem;
        font-weight: 500;
        color: #161616;
        margin-bottom: 0.5rem;
    }

    .empty-state .empty-desc {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.875rem;
        color: #525252;
        margin-bottom: 1.5rem;
    }

    .empty-state .example-query {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.8rem;
        color: #6f6f6f;
        background-color: #f4f4f4;
        padding: 0.4rem 0.75rem;
        margin: 0.25rem auto;
        display: inline-block;
        border-left: 2px solid #0f62fe;
    }

    /* Markdown content in main area */
    .stMarkdown {
        font-family: 'IBM Plex Sans', sans-serif !important;
        color: #525252;
        line-height: 1.6;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    </style>
    """
