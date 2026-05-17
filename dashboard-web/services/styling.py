"""Global CSS injection — Anthropic-inspired dark theme.

CRITICAL: do NOT apply font-family broadly via [data-testid] or [class*="st-"] —
that breaks Material Symbols icons. We only style `body` and explicit roots.
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

:root {
    --bg-page:        #08090A;
    --bg-card:        #101113;
    --bg-elev:        #16181B;
    --bd-sub:         #1C1D20;
    --bd:             #26282D;
    --bd-str:         #3A3D44;
    --tx:             #F7F8F8;
    --tx2:            #B4B8BF;
    --tx3:            #8A8F98;
    --accent:         #C2522D;
    --accent-h:       #D26142;
    --accent-a:       #A8421F;
    --accent-tint:    rgba(194,82,45,0.12);
    --status-pending:    #8A8F98;
    --status-eval:       #C2522D;
    --status-applied:    #5B8DEF;
    --status-responded:  #D4A574;
    --status-interview:  #4ADE80;
    --status-offer:      #34D399;
    --status-rejected:   #E5484D;
    --status-discarded:  #62666D;
}

/* Scoped font — body only, NOT data-testid (which would break Material Symbols) */
body, .stApp, .main, [data-testid="stSidebar"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-feature-settings: 'cv11', 'ss01';
    -webkit-font-smoothing: antialiased;
    color: var(--tx2);
    font-size: 15px;
    line-height: 1.55;
}

/* Material Symbols — override the inherited Inter font so icons render as glyphs */
[data-testid*="stIconMaterial"],
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
.material-symbols-sharp,
span[class*="material-symbols"],
i.material-icons {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
    font-weight: normal !important;
    font-style: normal !important;
    font-size: 20px;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -webkit-font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
    font-feature-settings: 'liga';
}

.stApp { background: var(--bg-page); }

/* Hide default Streamlit chrome — keep the header itself (top nav lives there) */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"],
[data-testid="stMainMenu"] { display: none !important; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

/* Header styling — host for top nav */
header[data-testid="stHeader"] {
    background: var(--bg-page) !important;
    border-bottom: 1px solid var(--bd-sub) !important;
    height: 56px !important;
}

/* Top navigation tabs */
[data-testid="stTopNav"] {
    background: transparent !important;
    padding: 0 1.5rem !important;
}
[data-testid="stTopNav"] a, [data-testid="stTopNav"] [role="tab"] {
    color: var(--tx2) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 6px 14px !important;
    border-radius: 6px !important;
}
[data-testid="stTopNav"] a:hover, [data-testid="stTopNav"] [role="tab"]:hover {
    color: var(--tx) !important;
    background: var(--bg-elev) !important;
}
[data-testid="stTopNav"] a[aria-current="page"],
[data-testid="stTopNav"] [aria-selected="true"] {
    color: var(--tx) !important;
    background: rgba(194,82,45,0.10) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Main container */
.main .block-container {
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    max-width: 1280px;
}

/* Typography — color heading text PRIMARY, not opaque grey */
h1, h2, h3, h4, h5, h6 { color: var(--tx); font-weight: 600; letter-spacing: -0.015em; }
h1 { font-size: 1.875rem !important; line-height: 1.2; margin-bottom: 0.5rem !important; }
h2 { font-size: 1.4rem !important; line-height: 1.25; margin-top: 1.75rem !important; margin-bottom: 0.5rem !important; }
h3 { font-size: 1.1rem !important; margin-top: 1.25rem !important; margin-bottom: 0.4rem !important; }
h4, h5 { font-size: 0.94rem !important; margin-top: 1rem !important; margin-bottom: 0.35rem !important; }

p, li, label, .stMarkdown { color: var(--tx2); }
[data-testid="stCaptionContainer"] { color: var(--tx3); font-size: 0.82rem; }
code, pre, [data-testid="stCodeBlock"] { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 0.82rem; }

/* Metrics */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--bd);
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] {
    color: var(--tx3) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] p { color: inherit !important; }
[data-testid="stMetricValue"] {
    color: var(--tx) !important;
    font-size: 1.85rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricValue"] > div { color: inherit !important; }

/* Buttons — primary uses Anthropic terracotta */
.stButton > button, .stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 9px 14px !important;
    border: 1px solid var(--bd) !important;
    background: var(--bg-elev) !important;
    color: var(--tx) !important;
    transition: background 120ms ease, border-color 120ms ease, transform 80ms ease !important;
    min-height: 40px !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: var(--bd) !important;
    border-color: var(--bd-str) !important;
}
.stButton > button[kind="primary"], button[kind="primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover, button[kind="primary"]:hover {
    background: var(--accent-h) !important;
    border-color: var(--accent-h) !important;
}
.stButton > button:focus, .stDownloadButton > button:focus {
    box-shadow: 0 0 0 3px var(--accent-tint) !important;
    outline: none !important;
}
.stButton > button:disabled, .stButton > button[disabled],
.stDownloadButton > button:disabled, .stDownloadButton > button[disabled] {
    background: rgba(255,255,255,0.025) !important;
    border-color: rgba(255,255,255,0.06) !important;
    color: rgba(247,248,248,0.40) !important;
    cursor: not-allowed !important;
    opacity: 1 !important;
}

/* Link buttons */
.stLinkButton a {
    background: var(--bg-elev) !important;
    border: 1px solid var(--bd) !important;
    color: var(--tx) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 9px 14px !important;
    text-decoration: none !important;
}
.stLinkButton a:hover { background: var(--bd) !important; border-color: var(--bd-str) !important; }

/* Bordered containers — cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 12px !important;
    padding: 18px 20px !important;
}

/* Column gap so buttons never overlap */
[data-testid="stHorizontalBlock"] { gap: 1.25rem !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--bd) !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.25rem 1rem 1.25rem; }
[data-testid="stSidebar"] h3 { font-size: 1rem !important; margin-top: 0 !important; }
[data-testid="stSidebar"] hr { margin: 0.75rem 0; border-color: var(--bd) !important; }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-baseweb="select"] > div, .stSelectbox div[data-baseweb="select"] > div {
    background: var(--bg-page) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 8px !important;
    color: var(--tx) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    border-bottom: 1px solid var(--bd) !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--tx3) !important;
    background: transparent !important;
    padding: 8px 14px !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    border-radius: 6px 6px 0 0 !important;
}
.stTabs [aria-selected="true"] {
    color: var(--tx) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: rgba(194,82,45,0.05) !important;
}

/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid var(--bd) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* Toggle (Show inactive etc.) */
.stToggle > label { color: var(--tx2) !important; font-size: 0.9rem; }

/* HR */
hr { border-color: var(--bd-sub) !important; margin: 1.5rem 0 !important; }

/* Custom helper classes */
.hero-card {
    background: linear-gradient(135deg, rgba(194,82,45,0.10) 0%, rgba(194,82,45,0.02) 100%);
    border: 1px solid rgba(194,82,45,0.18);
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
}
.hero-card h1 { margin: 0 0 0.35rem 0 !important; color: var(--tx); }
.hero-sub { color: var(--tx2); font-size: 0.95rem; }

.kpi-strip { display: flex; gap: 24px; flex-wrap: wrap; }
.kpi-item { display: flex; flex-direction: column; gap: 2px; }
.kpi-label { color: var(--tx3); font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-value { color: var(--tx); font-size: 1.5rem; font-weight: 600; letter-spacing: -0.02em; }

.section-label {
    color: var(--tx3);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
}
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)
