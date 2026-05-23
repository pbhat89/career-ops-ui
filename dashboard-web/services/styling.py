"""Global CSS — nellavio-inspired charcoal + green dark theme.

Palette:
  --bg-page  #161A1F   secondary surface
  --bg-card  #1C2025   primary card / panel
  --bg-elev  #232830   raised element / hover
  --accent   #3DB985   primary green
Opacity ladder for hovers: 0.03 → 0.07 → 0.10 over rgba(255,255,255).

CRITICAL: font-family is scoped to body roots only — do NOT broadcast to
[data-testid] (breaks Material Symbols glyphs).
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

:root {
    /* Page surfaces — distinct levels so the chrome reads */
    --bg-page:        #161A1F;
    --bg-card:        #1C2025;
    --bg-elev:        #262C34;
    --bg-deep:        #0D1115;   /* sidebar — darker than main */
    --bd-sub:         rgba(255,255,255,0.04);
    --bd:             rgba(255,255,255,0.08);
    --bd-str:         rgba(255,255,255,0.16);
    --tx:             #E7E9EC;
    --tx2:            #C9CBCF;
    --tx3:            #8C9196;
    /* Accent green — brighter than before so primary buttons pop */
    --accent:         #44D49A;
    --accent-h:       #5BE1AC;
    --accent-d:       #34B27F;
    --accent-tint:    rgba(68,212,154,0.16);
    --accent-soft:    rgba(68,212,154,0.07);
    --info:           #5385C6;
    --warn:           #FDBA74;
    --danger:         #FDA4AF;
    --success:        #6EE7B7;
    --status-pending:    #8C9196;
    --status-watch:      #C4B5FD;
    --status-eval:       #44D49A;
    --status-applied:    #5385C6;
    --status-responded:  #FDBA74;
    --status-interview:  #6EE7B7;
    --status-offer:      #44D49A;
    --status-rejected:   #FDA4AF;
    --status-discarded:  #62666D;
    --status-inprog:     #FBBF24;
}

/* Scoped font — body only */
body, .stApp, .main, [data-testid="stSidebar"] {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    -webkit-font-smoothing: antialiased;
    color: var(--tx2);
    font-size: 14.5px;
    line-height: 1.55;
}

/* Material Symbols — keep glyphs */
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

/* Hide default Streamlit chrome */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"],
[data-testid="stMainMenu"] { display: none !important; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

header[data-testid="stHeader"] {
    background: var(--bg-deep) !important;
    border-bottom: 1px solid var(--bd-sub) !important;
    height: 56px !important;
}

/* Top nav */
[data-testid="stTopNav"] {
    background: transparent !important;
    padding: 0 1.5rem !important;
}
[data-testid="stTopNav"] a, [data-testid="stTopNav"] [role="tab"] {
    color: var(--tx3) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 6px 14px !important;
    border-radius: 6px !important;
    transition: background 150ms ease-out, color 150ms ease-out !important;
}
[data-testid="stTopNav"] a:hover, [data-testid="stTopNav"] [role="tab"]:hover {
    color: var(--tx) !important;
    background: rgba(255,255,255,0.03) !important;
}
[data-testid="stTopNav"] a[aria-current="page"],
[data-testid="stTopNav"] [aria-selected="true"] {
    color: var(--accent) !important;
    background: var(--accent-soft) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Main container */
.main .block-container {
    padding-top: 1.75rem;
    padding-bottom: 4rem;
    max-width: 1320px;
}

/* Typography */
h1, h2, h3, h4, h5, h6 { color: var(--tx); font-weight: 600; letter-spacing: -0.015em; }
h1 { font-size: 1.85rem !important; line-height: 1.2; margin-bottom: 0.5rem !important; }
h2 { font-size: 1.35rem !important; line-height: 1.25; margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; }
h3 { font-size: 1.05rem !important; margin-top: 1.15rem !important; margin-bottom: 0.4rem !important; }
h4, h5 { font-size: 0.92rem !important; margin-top: 0.9rem !important; margin-bottom: 0.3rem !important; }

p, li, label, .stMarkdown { color: var(--tx2); }
[data-testid="stCaptionContainer"] { color: var(--tx3); font-size: 0.8rem; }
code, pre, [data-testid="stCodeBlock"] { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 0.8rem; }
[data-testid="stCodeBlock"] { background: var(--bg-deep) !important; border: 1px solid var(--bd) !important; border-radius: 8px !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--bd);
    border-radius: 12px;
    padding: 14px 18px;
    transition: border-color 150ms ease-out;
}
[data-testid="stMetric"]:hover { border-color: var(--bd-str); }
[data-testid="stMetricLabel"] {
    color: var(--tx3) !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] p { color: inherit !important; }
[data-testid="stMetricValue"] {
    color: var(--tx) !important;
    font-size: 1.75rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricValue"] > div { color: inherit !important; }

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 8px 14px !important;
    border: 1px solid var(--bd) !important;
    background: rgba(255,255,255,0.03) !important;
    color: var(--tx) !important;
    transition: background 150ms ease-out, border-color 150ms ease-out, transform 80ms ease !important;
    min-height: 38px !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: var(--bd-str) !important;
}
.stButton > button[kind="primary"], button[kind="primary"] {
    background: var(--accent-d) !important;
    border-color: var(--accent-d) !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover, button[kind="primary"]:hover {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}
.stButton > button:focus, .stDownloadButton > button:focus {
    box-shadow: 0 0 0 3px var(--accent-tint) !important;
    outline: none !important;
}
.stButton > button:disabled, .stButton > button[disabled],
.stDownloadButton > button:disabled, .stDownloadButton > button[disabled] {
    background: rgba(255,255,255,0.02) !important;
    border-color: rgba(255,255,255,0.05) !important;
    color: rgba(231,233,236,0.32) !important;
    cursor: not-allowed !important;
    opacity: 1 !important;
}

/* Link buttons */
.stLinkButton a {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--bd) !important;
    color: var(--tx) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 8px 14px !important;
    text-decoration: none !important;
    transition: background 150ms ease-out !important;
}
.stLinkButton a:hover { background: rgba(255,255,255,0.07) !important; border-color: var(--bd-str) !important; }

/* Bordered containers — cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
    transition: border-color 150ms ease-out;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: var(--bd-str); }

/* Column gap */
[data-testid="stHorizontalBlock"] { gap: 1.1rem !important; }

/* Sidebar — visibly darker than the main canvas so it reads as chrome */
[data-testid="stSidebar"] {
    background: var(--bg-deep) !important;
    border-right: 1px solid var(--bd) !important;
    box-shadow: inset -1px 0 0 rgba(255,255,255,0.02);
}
[data-testid="stSidebar"] .block-container { padding: 1.4rem 1.1rem 1rem 1.1rem; }
[data-testid="stSidebar"] h3 {
    font-size: 0.95rem !important;
    margin-top: 0 !important;
    color: var(--accent) !important;
    letter-spacing: -0.01em;
}
[data-testid="stSidebar"] hr { margin: 0.7rem 0; border-color: var(--bd) !important; }

/* Sidebar buttons — tighter, quieter so the command list reads as a list */
[data-testid="stSidebar"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 6px 10px !important;
    min-height: 32px !important;
    font-size: 0.82rem !important;
    background: transparent !important;
    border: 1px solid transparent !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(68,212,154,0.08) !important;
    border-color: rgba(68,212,154,0.20) !important;
    color: var(--accent-h) !important;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-baseweb="select"] > div, .stSelectbox div[data-baseweb="select"] > div {
    background: var(--bg-deep) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 8px !important;
    color: var(--tx) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-tint) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    border-bottom: 1px solid var(--bd) !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--tx3) !important;
    background: transparent !important;
    padding: 8px 14px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    border-radius: 6px 6px 0 0 !important;
    transition: color 150ms ease-out, background 150ms ease-out !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--tx2) !important; background: rgba(255,255,255,0.03) !important; }
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: var(--accent-soft) !important;
}

/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid var(--bd) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] table, [data-testid="stDataEditor"] table {
    background: var(--bg-card) !important;
}

/* Toggle */
.stToggle > label { color: var(--tx2) !important; font-size: 0.88rem; }

/* HR */
hr { border-color: var(--bd-sub) !important; margin: 1.4rem 0 !important; }

/* Hero card */
.hero-card {
    background:
        linear-gradient(135deg, rgba(61,185,133,0.18) 0%, rgba(61,185,133,0.04) 50%, rgba(28,32,37,0.0) 100%),
        var(--bg-card);
    border: 1px solid rgba(61,185,133,0.32);
    border-radius: 16px;
    padding: 1.6rem 1.9rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(0,0,0,0.25);
    position: relative;
    overflow: hidden;
}
.hero-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, var(--accent), var(--accent-d));
}
.hero-card h1 {
    margin: 0 0 0.35rem 0 !important;
    color: var(--tx);
    font-size: 1.95rem !important;
    letter-spacing: -0.02em;
}
.hero-sub { color: var(--tx2); font-size: 0.95rem; }
.hero-sub strong { color: var(--tx); }

/* KPI strip */
.kpi-strip { display: flex; gap: 22px; flex-wrap: wrap; }
.kpi-item { display: flex; flex-direction: column; gap: 2px; }
.kpi-label { color: var(--tx3); font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-value { color: var(--tx); font-size: 1.45rem; font-weight: 600; letter-spacing: -0.02em; }

/* Section label */
.section-label {
    color: var(--tx3);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
}

/* Action card (used in Desk bulk-action row) — flex layout so buttons line up
   no matter how long the description is. */
.action-card {
    background: var(--bg-card);
    border: 1px solid var(--bd);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    transition: border-color 150ms ease-out, background 150ms ease-out, transform 150ms ease-out;
    min-height: 138px;
    display: flex;
    flex-direction: column;
    border-left: 3px solid var(--accent);
}
.action-card:hover {
    border-color: var(--bd-str);
    border-left-color: var(--accent-h);
    background: var(--bg-elev);
    transform: translateY(-1px);
}
.action-card .ac-label {
    color: var(--accent);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
    font-weight: 600;
}
.action-card .ac-headline {
    color: var(--tx);
    font-weight: 600;
    font-size: 1.08rem;
    margin-bottom: 6px;
    letter-spacing: -0.01em;
}
.action-card .ac-sub {
    color: var(--tx2);
    font-size: 0.82rem;
    line-height: 1.45;
    flex: 1;
}

/* Inline progress badge (per-row evaluation) */
.row-progress {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 2px 8px; border-radius: 999px;
    background: rgba(251,191,36,0.10);
    border: 1px solid rgba(251,191,36,0.30);
    color: #FBBF24; font-size: 0.72rem; font-weight: 600;
}
.row-progress .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #FBBF24;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.4; transform: scale(0.85); }
    50%      { opacity: 1.0; transform: scale(1.1);  }
}

/* Banner for status / freshness */
.banner {
    padding: 10px 14px; border-radius: 10px; font-size: 0.86rem;
    display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
}
.banner-info    { background: rgba(83,133,198,0.10); border: 1px solid rgba(83,133,198,0.28); color: #8FB4DF; }
.banner-success { background: rgba(61,185,133,0.10); border: 1px solid rgba(61,185,133,0.30); color: #6EE7B7; }
.banner-warn    { background: rgba(253,186,116,0.10); border: 1px solid rgba(253,186,116,0.30); color: #FDBA74; }
.banner-danger  { background: rgba(253,164,175,0.10); border: 1px solid rgba(253,164,175,0.30); color: #FDA4AF; }

/* Dialog */
[data-testid="stDialog"] > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 14px !important;
}

/* Popover */
[data-testid="stPopover"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 12px !important;
}

/* Slider */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-page); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)
