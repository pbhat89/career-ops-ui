"""Global CSS — shadcn-inspired charcoal + teal dark theme (v2).

Palette:
  --bg-page  #12161B   secondary surface
  --bg-card  #1A1F26   primary card / panel  (raised 1 stop)
  --bg-elev  #232A33   raised element / hover
  --bg-deep  #0B0E12   sidebar — darker than main
  --accent   #2DAF7E   primary teal

Typography:
  Inter (UI) + JetBrains Mono (code), Material Symbols Rounded preserved.

CRITICAL: font-family is scoped to body roots only — do NOT broadcast to
[data-testid] (breaks Material Symbols glyphs).
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

:root {
    /* Page surfaces — distinct levels so the chrome reads */
    --bg-page:        #12161B;
    --bg-card:        #1A1F26;
    --bg-elev:        #232A33;
    --bg-elev-hi:     #2B333D;
    --bg-deep:        #0B0E12;
    --bg-glass:       rgba(26,31,38,0.72);

    --bd-sub:         rgba(255,255,255,0.04);
    --bd:             rgba(255,255,255,0.08);
    --bd-str:         rgba(255,255,255,0.14);
    --bd-bright:      rgba(255,255,255,0.22);

    --tx:             #ECEEF1;
    --tx2:            #C4C8CD;
    --tx3:            #858A91;
    --tx4:            #5F6469;

    /* Accent — deeper teal; readable with dark button labels, less neon glare */
    --accent:         #2DAF7E;
    --accent-h:       #3FC58F;
    --accent-d:       #1E8F66;
    --accent-tint:    rgba(45,175,126,0.18);
    --accent-soft:    rgba(45,175,126,0.08);

    --info:           #5B8FE6;
    --warn:           #FBBF24;
    --danger:         #F87171;
    --success:        #6EE7B7;
    --violet:         #C4B5FD;

    --status-pending:    #858A91;
    --status-watch:      #C4B5FD;
    --status-eval:       #2DAF7E;
    --status-applied:    #5B8FE6;
    --status-responded:  #FBBF24;
    --status-interview:  #6EE7B7;
    --status-offer:      #2DAF7E;
    --status-rejected:   #F87171;
    --status-discarded:  #5F6469;
    --status-inprog:     #FBBF24;

    --radius-sm:      6px;
    --radius:         10px;
    --radius-lg:      14px;
    --radius-xl:      18px;

    --shadow-sm:      0 1px 2px rgba(0,0,0,0.30);
    --shadow:         0 4px 12px rgba(0,0,0,0.30), 0 1px 0 rgba(255,255,255,0.04) inset;
    --shadow-lg:      0 12px 32px rgba(0,0,0,0.36), 0 1px 0 rgba(255,255,255,0.05) inset;
    --shadow-glow:    0 0 0 1px rgba(45,175,126,0.18), 0 6px 24px rgba(45,175,126,0.12);
}

/* Scoped font — body only */
body, .stApp, .main, [data-testid="stSidebar"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: var(--tx2);
    font-size: 14px;
    line-height: 1.55;
    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
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

.stApp {
    background:
        radial-gradient(900px 500px at 12% -10%, rgba(45,175,126,0.06), transparent 60%),
        radial-gradient(700px 400px at 88% 8%, rgba(91,143,230,0.04), transparent 60%),
        var(--bg-page);
}

/* Hide default Streamlit chrome */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"],
[data-testid="stMainMenu"] { display: none !important; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

header[data-testid="stHeader"] {
    background: rgba(11,14,18,0.72) !important;
    backdrop-filter: saturate(140%) blur(10px);
    -webkit-backdrop-filter: saturate(140%) blur(10px);
    border-bottom: 1px solid var(--bd-sub) !important;
    height: 52px !important;
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
    border-radius: var(--radius-sm) !important;
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
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    max-width: 1340px;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    color: var(--tx);
    font-weight: 600;
    letter-spacing: -0.018em;
    font-family: 'Inter', sans-serif;
}
h1 { font-size: 1.85rem !important; line-height: 1.18; margin-bottom: 0.45rem !important; }
h2 { font-size: 1.35rem !important; line-height: 1.25; margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; }
h3 { font-size: 1.05rem !important; margin-top: 1.15rem !important; margin-bottom: 0.4rem !important; }
h4, h5 { font-size: 0.92rem !important; margin-top: 0.9rem !important; margin-bottom: 0.3rem !important; }

p, li, label, .stMarkdown { color: var(--tx2); }
[data-testid="stCaptionContainer"] { color: var(--tx3); font-size: 0.8rem; }
code, pre, [data-testid="stCodeBlock"] {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 0.8rem;
    font-feature-settings: 'calt' 1, 'ss01' 1;
}
[data-testid="stCodeBlock"] {
    background: var(--bg-deep) !important;
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius) !important;
}

/* Metrics — shadcn-style metric card */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--bd);
    border-radius: var(--radius-lg);
    padding: 16px 20px;
    transition: border-color 150ms ease-out, transform 150ms ease-out, box-shadow 150ms ease-out;
    position: relative;
    overflow: hidden;
}
[data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--bd-bright), transparent);
    opacity: 0;
    transition: opacity 200ms ease-out;
}
[data-testid="stMetric"]:hover {
    border-color: var(--bd-str);
    transform: translateY(-1px);
    box-shadow: var(--shadow);
}
[data-testid="stMetric"]:hover::before { opacity: 1; }
[data-testid="stMetricLabel"] {
    color: var(--tx3) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] p { color: inherit !important; }
[data-testid="stMetricValue"] {
    color: var(--tx) !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em;
    line-height: 1.1;
    margin-top: 4px;
}
[data-testid="stMetricValue"] > div { color: inherit !important; }
[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    margin-top: 4px;
}

/* Buttons — shadcn-like with subtle micro-interactions */
.stButton > button, .stDownloadButton > button {
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 8px 14px !important;
    border: 1px solid var(--bd) !important;
    background: rgba(255,255,255,0.03) !important;
    color: var(--tx) !important;
    transition: background 140ms ease-out, border-color 140ms ease-out, transform 80ms ease, box-shadow 140ms ease-out !important;
    min-height: 36px !important;
    letter-spacing: -0.005em !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(255,255,255,0.06) !important;
    border-color: var(--bd-str) !important;
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}
.stButton > button:active, .stDownloadButton > button:active {
    transform: translateY(0);
}
.stButton > button[kind="primary"], button[kind="primary"] {
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-d) 100%) !important;
    border-color: var(--accent-d) !important;
    color: #07120D !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 0 rgba(255,255,255,0.18) inset, 0 1px 2px rgba(0,0,0,0.30);
}
.stButton > button[kind="primary"]:hover, button[kind="primary"]:hover {
    background: linear-gradient(180deg, var(--accent-h) 0%, var(--accent) 100%) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 1px 0 rgba(255,255,255,0.22) inset, var(--shadow-glow);
    transform: translateY(-1px);
}
.stButton > button:focus, .stDownloadButton > button:focus {
    box-shadow: 0 0 0 3px var(--accent-tint) !important;
    outline: none !important;
}
.stButton > button:disabled, .stButton > button[disabled],
.stDownloadButton > button:disabled, .stDownloadButton > button[disabled] {
    background: rgba(255,255,255,0.02) !important;
    border-color: rgba(255,255,255,0.05) !important;
    color: rgba(231,233,236,0.30) !important;
    cursor: not-allowed !important;
    opacity: 1 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Link buttons */
.stLinkButton a {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--bd) !important;
    color: var(--tx) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 8px 14px !important;
    text-decoration: none !important;
    transition: background 140ms ease-out, transform 80ms ease !important;
}
.stLinkButton a:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: var(--bd-str) !important;
    transform: translateY(-1px);
}

/* Bordered containers — cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius-lg) !important;
    padding: 16px 18px !important;
    transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--bd-str);
    box-shadow: var(--shadow-sm);
}

/* Column gap */
[data-testid="stHorizontalBlock"] { gap: 1.1rem !important; }

/* Sidebar — visibly darker than the main canvas so it reads as chrome */
[data-testid="stSidebar"] {
    background: var(--bg-deep) !important;
    border-right: 1px solid var(--bd) !important;
    box-shadow: inset -1px 0 0 rgba(255,255,255,0.02);
}
[data-testid="stSidebar"] .block-container { padding: 1.3rem 1rem 1rem 1rem; }
[data-testid="stSidebar"] h3 {
    font-size: 0.95rem !important;
    margin-top: 0 !important;
    color: var(--accent) !important;
    letter-spacing: -0.015em;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] hr { margin: 0.7rem 0; border-color: var(--bd) !important; }

/* Sidebar buttons — tighter, quieter so the command list reads as a list */
[data-testid="stSidebar"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 7px 10px !important;
    min-height: 34px !important;
    font-size: 0.83rem !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    box-shadow: none !important;
    transform: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(45,175,126,0.08) !important;
    border-color: rgba(45,175,126,0.22) !important;
    color: var(--accent-h) !important;
    transform: translateX(2px);
}

/* Sidebar KPI tiles — shadcn-style mini metric */
.kpi-tile-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    margin: 10px 0 4px;
}
.kpi-tile {
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    border: 1px solid var(--bd);
    border-radius: var(--radius);
    padding: 10px 12px;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    transition: border-color 150ms ease-out, background 150ms ease-out;
}
.kpi-tile:hover {
    border-color: var(--bd-str);
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
}
.kpi-tile-label {
    color: var(--tx3);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.kpi-tile-value {
    color: var(--tx);
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: -0.015em;
    font-feature-settings: 'tnum';
}
.kpi-tile-value.accent { color: var(--accent); }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-baseweb="select"] > div, .stSelectbox div[data-baseweb="select"] > div {
    background: var(--bg-deep) !important;
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--tx) !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-tint) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: var(--tx4) !important;
}

/* Tabs — shadcn-style with pill-shaped active */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important;
    border-bottom: 1px solid var(--bd) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--tx3) !important;
    background: transparent !important;
    padding: 9px 16px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    transition: color 150ms ease-out, background 150ms ease-out !important;
    letter-spacing: -0.005em !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--tx) !important; background: rgba(255,255,255,0.03) !important; }
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: var(--accent-soft) !important;
    font-weight: 600 !important;
}

/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] table, [data-testid="stDataEditor"] table {
    background: var(--bg-card) !important;
    font-family: 'Inter', sans-serif !important;
}

/* Toggle */
.stToggle > label { color: var(--tx2) !important; font-size: 0.88rem; }

/* HR */
hr { border-color: var(--bd-sub) !important; margin: 1.4rem 0 !important; }

/* Hero card — refined gradient + glow */
.hero-card {
    background:
        linear-gradient(135deg, rgba(45,175,126,0.16) 0%, rgba(45,175,126,0.03) 45%, rgba(26,31,38,0.0) 100%),
        var(--bg-card);
    border: 1px solid rgba(45,175,126,0.28);
    border-radius: var(--radius-xl);
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.3rem;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
}
.hero-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, var(--accent), var(--accent-d));
    box-shadow: 0 0 16px rgba(45,175,126,0.32);
}
.hero-card::after {
    content: "";
    position: absolute;
    top: -50%; right: -10%;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(45,175,126,0.10) 0%, transparent 60%);
    pointer-events: none;
}
.hero-card h1 {
    margin: 0 0 0.3rem 0 !important;
    color: var(--tx);
    font-size: 1.95rem !important;
    letter-spacing: -0.025em;
    font-weight: 700;
}
.hero-sub { color: var(--tx2); font-size: 0.95rem; position: relative; z-index: 1; }
.hero-sub strong { color: var(--tx); font-weight: 600; }

/* KPI strip */
.kpi-strip { display: flex; gap: 22px; flex-wrap: wrap; }
.kpi-item { display: flex; flex-direction: column; gap: 2px; }
.kpi-label { color: var(--tx3); font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; }
.kpi-value { color: var(--tx); font-size: 1.45rem; font-weight: 700; letter-spacing: -0.02em; }

/* Section label */
.section-label {
    color: var(--tx3);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.55rem;
}

/* Section header with optional badge — used by section_header() helper */
.section-header {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin: 0.4rem 0 0.8rem;
}
.section-header .sh-title {
    color: var(--tx);
    font-size: 1.08rem;
    font-weight: 600;
    letter-spacing: -0.015em;
}
.section-header .sh-desc {
    color: var(--tx3);
    font-size: 0.85rem;
    font-weight: 400;
}
.section-header .sh-badge {
    background: var(--accent-soft);
    color: var(--accent);
    border: 1px solid rgba(45,175,126,0.30);
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Action card v2 — single clickable area (button extends across whole card) */
.action-card {
    background: linear-gradient(180deg, var(--bg-card), rgba(26,31,38,0.85));
    border: 1px solid var(--bd);
    border-radius: var(--radius-lg);
    padding: 16px 18px 14px;
    margin-bottom: 10px;
    transition: border-color 160ms ease-out, background 160ms ease-out, transform 160ms ease-out, box-shadow 160ms ease-out;
    min-height: 132px;
    display: flex;
    flex-direction: column;
    border-left: 3px solid var(--accent);
    position: relative;
    overflow: hidden;
}
.action-card::before {
    content: "";
    position: absolute;
    top: 0; right: 0;
    width: 90px; height: 90px;
    background: radial-gradient(circle at 100% 0%, rgba(45,175,126,0.10), transparent 70%);
    pointer-events: none;
    opacity: 0;
    transition: opacity 200ms ease-out;
}
.action-card:hover {
    border-color: var(--bd-str);
    border-left-color: var(--accent-h);
    background: linear-gradient(180deg, var(--bg-elev), var(--bg-card));
    transform: translateY(-2px);
    box-shadow: var(--shadow);
}
.action-card:hover::before { opacity: 1; }
.action-card .ac-label {
    color: var(--accent);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 5px;
    font-weight: 700;
}
.action-card .ac-headline {
    color: var(--tx);
    font-weight: 600;
    font-size: 1.08rem;
    margin-bottom: 5px;
    letter-spacing: -0.015em;
}
.action-card .ac-sub {
    color: var(--tx2);
    font-size: 0.82rem;
    line-height: 1.45;
    flex: 1;
}

/* Pill / badge — shadcn-style */
.pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid;
    font-family: 'Inter', sans-serif;
    line-height: 1.4;
    white-space: nowrap;
}
.pill-default  { background: rgba(255,255,255,0.04); color: var(--tx2); border-color: var(--bd-str); }
.pill-accent   { background: var(--accent-soft); color: var(--accent); border-color: rgba(45,175,126,0.30); }
.pill-info     { background: rgba(91,143,230,0.10); color: #8FB4DF; border-color: rgba(91,143,230,0.28); }
.pill-warn     { background: rgba(251,191,36,0.10); color: var(--warn); border-color: rgba(251,191,36,0.30); }
.pill-danger   { background: rgba(248,113,113,0.10); color: var(--danger); border-color: rgba(248,113,113,0.30); }
.pill-success  { background: rgba(110,231,183,0.10); color: var(--success); border-color: rgba(110,231,183,0.30); }
.pill-violet   { background: rgba(196,181,253,0.10); color: var(--violet); border-color: rgba(196,181,253,0.30); }
.pill-muted    { background: rgba(255,255,255,0.02); color: var(--tx3); border-color: var(--bd); }

.pill-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
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

/* Banner — used for inline alerts (info / warn / danger / success) */
.banner {
    padding: 11px 15px; border-radius: var(--radius); font-size: 0.86rem;
    display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
    border: 1px solid;
    backdrop-filter: blur(4px);
}
.banner-info    { background: rgba(91,143,230,0.10); border-color: rgba(91,143,230,0.28); color: #8FB4DF; }
.banner-success { background: rgba(45,175,126,0.10); border-color: rgba(45,175,126,0.30); color: var(--success); }
.banner-warn    { background: rgba(251,191,36,0.10); border-color: rgba(251,191,36,0.30); color: var(--warn); }
.banner-danger  { background: rgba(248,113,113,0.10); border-color: rgba(248,113,113,0.30); color: var(--danger); }

/* Verdict card — used on Role page */
.verdict-card {
    border-radius: var(--radius);
    padding: 14px 18px;
    margin-bottom: 14px;
    border: 1px solid;
    background-clip: padding-box;
    position: relative;
}
.verdict-card .vc-head { font-weight: 700; font-size: 0.96rem; margin-bottom: 4px; letter-spacing: -0.01em; }
.verdict-card .vc-body { color: var(--tx2); font-size: 0.88rem; line-height: 1.5; }

/* Dialog */
[data-testid="stDialog"] > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-lg);
}

/* Popover */
[data-testid="stPopover"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius) !important;
}

/* Slider */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* Expander — cleaner */
[data-testid="stExpander"] {
    border: 1px solid var(--bd) !important;
    border-radius: var(--radius) !important;
    background: var(--bg-card) !important;
}
[data-testid="stExpander"] summary {
    padding: 10px 14px !important;
    font-weight: 500 !important;
    color: var(--tx) !important;
}
[data-testid="stExpander"] summary:hover {
    background: var(--bg-elev) !important;
}

/* Status overlay strip (used on Desk) */
.status-strip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(180deg, var(--bg-card), rgba(26,31,38,0.92));
    border: 1px solid var(--bd);
    border-radius: var(--radius-lg);
    padding: 14px 18px;
    margin-bottom: 14px;
    box-shadow: var(--shadow-sm);
}
.status-strip-left { display: flex; flex-direction: column; gap: 2px; }
.status-strip-label {
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--tx3);
    font-weight: 600;
}
.status-strip-headline {
    color: var(--tx);
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: -0.01em;
}
.status-strip-stats { display: flex; gap: 22px; }
.status-strip-stat { text-align: right; }
.status-strip-stat-label {
    font-size: 10.5px;
    color: var(--tx3);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}
.status-strip-stat-value {
    color: var(--tx);
    font-weight: 700;
    font-size: 1rem;
    font-feature-settings: 'tnum';
}
.status-strip-bar {
    margin-top: 10px;
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.05);
    overflow: hidden;
}
.status-strip-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent-h));
    border-radius: 2px;
    transition: width 400ms ease-out;
    box-shadow: 0 0 8px rgba(45,175,126,0.40);
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-page); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.20); }

/* Subtle entrance for cards (page load) */
@keyframes card-rise {
    0%   { opacity: 0; transform: translateY(6px); }
    100% { opacity: 1; transform: translateY(0); }
}
.action-card, .hero-card, .status-strip, [data-testid="stMetric"] {
    animation: card-rise 360ms ease-out both;
}
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)
