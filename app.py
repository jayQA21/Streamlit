import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import re
import os
import time
from datetime import datetime, date
from scheduler import start_scheduler
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────
def get_secret(key, default=""):
    try:
        val = st.secrets[key]
        return val
    except:
        return os.getenv(key, default)

JIRA_EMAIL    = get_secret("JIRA_EMAIL")
JIRA_TOKEN    = get_secret("JIRA_API_TOKEN").replace("\n","").replace("\r","").replace(" ","").strip()
JIRA_BASE     = get_secret("JIRA_BASE_URL", "https://minehub.atlassian.net")
SLACK_WEBHOOK = get_secret("SLACK_WEBHOOK_URL")
DASHBOARD_PIN = get_secret("DASHBOARD_PIN")

PROJECT       = "JENG"
SPRINT_NAME   = "Release Sprint 3"
SPRINT_START  = date(2026, 2, 24)
SPRINT_DAYS   = 48

DONE_STATUSES    = {"Done", "PO/QA VALID", "In demo", "In production", "CS reviewed", "Demo", "In Production", "CS Reviewed"}
BLOCKED_STATUSES = {"Blocked"}
ACTIVE_STATUSES  = {"In Progress", "AIM OF THE DAY", "Tech review", "PO review",
                     "PO/QA Test run", "Aim Of The week", "PO not valid", "Tech strategy"}

DEV_COLORS = {
    "Nikita Vaidya": "#818cf8",
    "Satadru Roy":   "#f472b6",
    "Rizky Ario":    "#fb923c",
    "Jay Pitroda":   "#34d399",
    "Unassigned":    "#64748b",
}
STATUS_COLORS = {
    "Done": "#10b981", "PO/QA VALID": "#34d399", "PO/QA Test run": "#6ee7b7",
    "Demo": "#a7f3d0", "In Production": "#059669", "CS Reviewed": "#065f46",
    "PO review": "#818cf8", "Tech review": "#a78bfa", "In Progress": "#38bdf8",
    "AIM OF THE DAY": "#7dd3fc", "Aim Of The week": "#bae6fd",
    "To Do": "#64748b", "Blocked": "#f87171", "PO not valid": "#f97316",
}
STATUS_ORDER = [
    "Done", "PO/QA VALID", "In demo", "In production", "CS reviewed",
    "Demo", "In Production", "CS Reviewed",
    "PO/QA Test run", "Tech review", "PO review", "Tech strategy",
    "AIM OF THE DAY", "In Progress", "Aim Of The week",
    "To Do", "Blocked", "PO not valid",
]

# ─── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(page_title="Jules Sprint Dashboard", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;900&family=Space+Mono:wght@400;700&display=swap');

/* ── BASE ── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; background-color: #080c1a !important; color: #e2e8f0 !important; }
.stApp { background: radial-gradient(ellipse at 20% 10%, #0d1b3e 0%, #080c1a 55%, #050710 100%) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }

/* ── TABS ── */
[data-baseweb="tab-list"] { background: rgba(15,22,41,0.8) !important; border-radius: 12px !important; padding: 4px !important; }
[data-baseweb="tab"] { background: transparent !important; color: #475569 !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 0.75rem !important; transition: all 0.2s !important; }
[aria-selected="true"] { background: rgba(0,212,255,0.1) !important; color: #00d4ff !important; border-bottom: 2px solid #00d4ff !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: linear-gradient(135deg, rgba(0,212,255,0.08), rgba(129,140,248,0.08)) !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    color: #00d4ff !important; border-radius: 10px !important;
    font-weight: 700 !important; transition: all 0.25s ease !important;
    position: relative; overflow: hidden !important;
}
.stButton > button::before {
    content: ''; position: absolute; top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0,212,255,0.1), transparent);
    transition: left 0.5s ease;
}
.stButton > button:hover::before { left: 100% !important; }
.stButton > button:hover {
    border-color: #00d4ff !important;
    background: rgba(0,212,255,0.15) !important;
    box-shadow: 0 0 20px rgba(0,212,255,0.25) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0px) !important; }

/* ── PROGRESS BAR ── */
.stProgress > div > div { background: linear-gradient(90deg, #00d4ff, #818cf8) !important; border-radius: 99px !important; transition: width 1s ease !important; }

/* ── METRICS ── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(15,22,41,0.95), rgba(20,30,55,0.9)) !important;
    border: 1px solid rgba(0,212,255,0.15) !important; border-radius: 14px !important; padding: 14px 16px !important;
    transition: all 0.3s ease !important; cursor: default !important;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(0,212,255,0.45) !important;
    box-shadow: 0 0 24px rgba(0,212,255,0.15), 0 4px 24px rgba(0,0,0,0.3) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stMetricValue"] { color: #00d4ff !important; font-family: 'Space Mono', monospace !important; }
div[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.7rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }

/* ── TICKET LINKS ── */
.ticket-key a {
    color: #00d4ff !important; font-family: 'Space Mono', monospace !important;
    font-size: 11px !important; text-decoration: none !important;
    border-bottom: 1px dotted rgba(0,212,255,0.4);
    transition: all 0.2s !important;
}
.ticket-key a:hover { color: #fff !important; border-bottom-color: #fff !important; }
.ticket-summary a { color: #94a3b8 !important; text-decoration: none !important; transition: color 0.2s !important; }
.ticket-summary a:hover { color: #c4b5fd !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #080c1a; }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg,#00d4ff,#818cf8); border-radius: 99px; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] { background: rgba(8,12,26,0.95) !important; border-right: 1px solid rgba(0,212,255,0.08) !important; }

/* ── ANIMATIONS ── */
@keyframes pulse       { 0%,100%{opacity:1} 50%{opacity:0.3} }
@keyframes pulse-ring  { 0%{transform:scale(0.9);opacity:1} 100%{transform:scale(1.8);opacity:0} }
@keyframes fadeInUp    { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeInLeft  { from{opacity:0;transform:translateX(-20px)} to{opacity:1;transform:translateX(0)} }
@keyframes slideIn     { from{opacity:0;transform:translateY(-10px)} to{opacity:1;transform:translateY(0)} }
@keyframes countUp     { from{opacity:0;transform:scale(0.8)} to{opacity:1;transform:scale(1)} }
@keyframes shimmerBar  { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
@keyframes borderGlow  { 0%,100%{border-color:rgba(0,212,255,0.2)} 50%{border-color:rgba(0,212,255,0.6)} }
@keyframes floatUp     { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
@keyframes spin-slow   { to{transform:rotate(360deg)} }
@keyframes dash        { to{stroke-dashoffset:0} }
@keyframes barFill     { from{width:0%} to{width:var(--target-width)} }

/* ── ANIMATED CARDS ── */
.anim-card {
    animation: fadeInUp 0.5s cubic-bezier(0.16,1,0.3,1) both;
    background: rgba(15,22,41,0.9);
    border: 1px solid rgba(0,212,255,0.08);
    border-radius: 16px; padding: 20px 22px; margin-bottom: 12px;
    transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s;
}
.anim-card:hover {
    border-color: rgba(0,212,255,0.22) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 0 1px rgba(0,212,255,0.1) !important;
    transform: translateY(-2px) !important;
}

/* ── ANIMATED BARS ── */
.bar-wrap { background:#1e2d47; border-radius:999px; height:6px; overflow:hidden; }
.bar-fill {
    height:100%; border-radius:999px;
    background-size:200% auto;
    animation: shimmerBar 3s linear infinite;
}

/* ── LIVE DOT ── */
.live-dot-wrap { position:relative; display:inline-flex; align-items:center; }
.live-dot { width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981;animation:pulse 2s infinite;display:inline-block;margin-right:6px; }
.live-dot::after { content:'';position:absolute;top:-2px;left:-2px;width:12px;height:12px;border-radius:50%;background:rgba(16,185,129,0.3);animation:pulse-ring 2s infinite; }

/* ── STATUS BADGE ── */
.status-badge { display:inline-block;padding:2px 8px;border-radius:99px;font-size:9px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase; }

/* ── TICKET ROW HOVER ── */
.ticket-row-wrap {
    display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;
    margin-bottom:3px;background:rgba(255,255,255,0.015);
    border:1px solid rgba(255,255,255,0.04);
    transition: all 0.2s ease; cursor:default;
}
.ticket-row-wrap:hover {
    background:rgba(0,212,255,0.04) !important;
    border-color:rgba(0,212,255,0.12) !important;
    transform:translateX(3px) !important;
}
.ticket-row-blocked {
    background:rgba(248,113,113,0.04) !important;
    border-color:rgba(248,113,113,0.15) !important;
}
.ticket-row-blocked:hover {
    background:rgba(248,113,113,0.07) !important;
    border-color:rgba(248,113,113,0.3) !important;
}

/* ── SKELETON LOADING ── */
.skeleton { background:linear-gradient(90deg,#1e2d47 25%,rgba(0,212,255,0.06) 50%,#1e2d47 75%); background-size:400% 100%; animation:shimmerBar 1.5s infinite; border-radius:8px; }

/* ── SECTION HEADERS ── */
.section-header {
    font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
    color:#475569;margin-bottom:14px;
    display:flex;align-items:center;gap:8px;
}
.section-header::after { content:'';flex:1;height:1px;background:linear-gradient(90deg,rgba(0,212,255,0.2),transparent); }

/* ── BLOCKED PULSE ── */
.blocked-alert { animation: borderGlow 2s ease-in-out infinite; }

/* ── DEV CARD HOVER ── */
.dev-card { transition: all 0.25s ease !important; }
.dev-card:hover { transform: translateY(-3px) !important; box-shadow: 0 12px 32px rgba(0,0,0,0.3) !important; }

/* ── TYPEWRITER CURSOR ── */
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.cursor { animation: blink 1s infinite; color:#00d4ff; }

/* ── FLOATING PARTICLES ── */
@keyframes float-particle {
    0%   { transform: translateY(100vh) translateX(0)    rotate(0deg);   opacity: 0; }
    10%  { opacity: 0.4; }
    90%  { opacity: 0.2; }
    100% { transform: translateY(-10vh) translateX(50px) rotate(360deg); opacity: 0; }
}
.particle {
    position: fixed; border-radius: 50%; pointer-events: none;
    animation: float-particle linear infinite;
}
</style>
""", unsafe_allow_html=True)


# ─── PIN PROTECTION# ─── PIN PROTECTION ───────────────────────────────────────
def check_pin():
    if not DASHBOARD_PIN:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
    <style>
    @keyframes float    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-16px)} }
    @keyframes shimmer  { 0%{background-position:-300% center} 100%{background-position:300% center} }
    @keyframes pulse3   { 0%,100%{opacity:.3;transform:scale(1)} 50%{opacity:.7;transform:scale(1.08)} }
    @keyframes fadeUp   { from{opacity:0;transform:translateY(28px)} to{opacity:1;transform:translateY(0)} }
    @keyframes confetti {
        0%  { transform: translateY(-10px) rotate(0deg);   opacity: 1; }
        100%{ transform: translateY(110vh) rotate(720deg); opacity: 0; }
    }
    @keyframes spin2 { to{ transform: rotate(360deg); } }

    .login-wrap {
        position:fixed;top:0;left:0;width:100%;height:100%;
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        overflow:hidden;
    }
    .orb-a {
        position:fixed;top:-120px;right:-80px;width:420px;height:420px;border-radius:50%;
        background:radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%);
        animation:pulse3 5s ease-in-out infinite;
    }
    .orb-b {
        position:fixed;bottom:-180px;left:-120px;width:520px;height:520px;border-radius:50%;
        background:radial-gradient(circle, rgba(16,185,129,0.09) 0%, transparent 70%);
        animation:pulse3 7s ease-in-out infinite reverse;
    }
    .orb-c {
        position:fixed;top:45%;left:5%;width:180px;height:180px;border-radius:50%;
        background:radial-gradient(circle, rgba(56,189,248,0.07) 0%, transparent 70%);
        animation:pulse3 9s ease-in-out infinite;
    }
    .grid-lines {
        position:fixed;top:0;left:0;width:100%;height:100%;
        background-image: linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
        background-size: 60px 60px;
    }
    .login-card {
        animation: fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) both;
    }
    .rocket {
        font-size:68px;
        animation:float 3s ease-in-out infinite;
        display:block;
        filter:drop-shadow(0 0 18px rgba(0,212,255,0.9)) drop-shadow(0 0 40px rgba(16,185,129,0.5));
    }
    .login-title {
        font-size:40px !important; font-weight:900 !important;
        background: linear-gradient(90deg, #00d4ff, #10b981, #38bdf8, #00d4ff) !important;
        background-size: 300% auto !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        animation: shimmer 4s linear infinite !important;
        letter-spacing: -1px !important;
    }
    .divider-line {
        width:50px;height:3px;margin:16px auto;
        background:linear-gradient(90deg,#00d4ff,#10b981);
        border-radius:99px;
    }
    .confetti-piece {
        position:fixed;
        width:10px;height:10px;
        border-radius:2px;
        animation: confetti 3s ease-in forwards;
        z-index:9999;
    }
    </style>
    <div class="login-wrap"></div>
    <div class="orb-a"></div><div class="orb-b"></div><div class="orb-c"></div>
    <div class="grid-lines"></div>
    <div class="login-card" style="max-width:400px;margin:50px auto 0;text-align:center;padding:0 24px;position:relative;z-index:10;">
        <span class="rocket">🚀</span>
        <div style="margin-top:20px;">
            <div class="login-title">Jules Dashboard</div>
            <div class="divider-line"></div>
            <div style="color:#4b6a7a;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;margin-top:4px;">
                Sprint Intelligence · MineHub
            </div>
        </div>
        <div style="margin-top:28px;background:rgba(0,0,0,0.25);border:1px solid rgba(0,212,255,0.15);
             border-radius:20px;padding:28px 24px;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);">
            <p style="color:#4b7a8a;font-size:11px;letter-spacing:2px;margin-bottom:18px;text-transform:uppercase;">
                🔐 &nbsp; Enter Access PIN
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <style>
        div[data-testid="stTextInput"] input {
            background: rgba(0,0,0,0.3) !important;
            border: 1px solid rgba(0,212,255,0.3) !important;
            border-radius: 14px !important;
            color: #e2e8f0 !important;
            font-size: 22px !important;
            text-align: center !important;
            letter-spacing: 10px !important;
            padding: 16px !important;
            transition: all 0.3s !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: rgba(0,212,255,0.7) !important;
            box-shadow: 0 0 24px rgba(0,212,255,0.2), inset 0 0 12px rgba(0,212,255,0.05) !important;
            outline: none !important;
        }
        div[data-testid="stTextInput"] input::placeholder { color: #1e3a4a !important; letter-spacing: 6px !important; }
        </style>
        """, unsafe_allow_html=True)

        pin = st.text_input("pin", type="password", placeholder="· · · ·", label_visibility="collapsed")
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("✦  Enter Dashboard", use_container_width=True):
            if pin == DASHBOARD_PIN:
                # CSS confetti burst instead of balloons
                st.markdown("""
                <style>
                @keyframes confetti { 0%{transform:translateY(-10px) rotate(0deg);opacity:1} 100%{transform:translateY(110vh) rotate(720deg);opacity:0} }
                </style>
                <div id="confetti-box">
                """ + "".join([
                    f'<div class="confetti-piece" style="left:{i*5+2}%;top:-5%;background:{"#00d4ff" if i%4==0 else "#10b981" if i%4==1 else "#38bdf8" if i%4==2 else "#a78bfa"};animation-delay:{i*0.08:.2f}s;animation-duration:{2.5+i*0.1:.1f}s;transform:rotate({i*17}deg);"></div>'
                    for i in range(20)
                ]) + """
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1.5)
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.markdown("""
                <div style="background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.3);
                     border-radius:10px;padding:10px 16px;text-align:center;color:#fca5a5;font-size:13px;margin-top:8px;">
                    ⚠️ &nbsp; Incorrect PIN — please try again
                </div>
                """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-top:36px;color:#1e3a4a;font-size:10px;letter-spacing:1.5px;position:relative;z-index:10;">
        JULES PRODUCT &nbsp;·&nbsp; MINEHUB &nbsp;·&nbsp; RELEASE SPRINT 3
    </div>
    """, unsafe_allow_html=True)
    return False


# ─── JIRA FETCH ───────────────────────────────────────────
def clean_title(s):
    s = re.sub(r'^(AAWU,?\s*|AAD,?\s*)', '', s, flags=re.IGNORECASE)
    return s.lstrip(',').strip()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_available_sprints():
    """Fetch all sprints (active + closed) from Jira"""
    url  = f"{JIRA_BASE}/rest/agile/1.0/board"
    auth = (JIRA_EMAIL, JIRA_TOKEN)
    # Get board ID first
    resp = requests.get(url, headers={"Accept": "application/json"},
                        auth=auth, params={"projectKeyOrId": PROJECT}, timeout=15)
    if not resp.ok:
        return []
    boards = resp.json().get("values", [])
    if not boards:
        return []
    board_id = boards[0]["id"]

    # Get all sprints for this board
    sprints = []
    start = 0
    while True:
        r = requests.get(
            f"{JIRA_BASE}/rest/agile/1.0/board/{board_id}/sprint",
            headers={"Accept": "application/json"}, auth=auth,
            params={"startAt": start, "maxResults": 50, "state": "active,closed"},
            timeout=15
        )
        if not r.ok:
            break
        data = r.json()
        for s in data.get("values", []):
            sprints.append({
                "id":    s["id"],
                "name":  s["name"],
                "state": s["state"],
                "start": s.get("startDate", "")[:10] if s.get("startDate") else "",
                "end":   s.get("completeDate", s.get("endDate", ""))[:10] if s.get("completeDate") or s.get("endDate") else "",
            })
        if data.get("isLast", True):
            break
        start += 50

    # Sort newest first
    sprints.sort(key=lambda x: x["start"], reverse=True)
    return sprints


@st.cache_data(ttl=300, show_spinner=False)
def fetch_jira_tickets(sprint_id=None):
    url = f"{JIRA_BASE}/rest/api/3/search/jql"
    auth = (JIRA_EMAIL, JIRA_TOKEN)
    headers = {"Accept": "application/json"}
    tickets = []
    next_page_token = None

    # Build JQL — filter by specific sprint or open sprint
    if sprint_id:
        jql = f"project = {PROJECT} AND sprint = {sprint_id} ORDER BY created DESC"
    else:
        jql = f"project = {PROJECT} AND sprint in openSprints() ORDER BY created DESC"

    while True:
        params = {
            "jql": jql,
            "maxResults": 100,
            "fields": "summary,status,assignee,customfield_10024,issuetype,customfield_10020",
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        resp = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for issue in data.get("issues", []):
            f = issue.get("fields", {})
            raw_sp = f.get("customfield_10024")
            # Extract sprint names from customfield_10020
            sprint_list = f.get("customfield_10020") or []
            sprint_names = [s.get("name","") for s in sprint_list if isinstance(s, dict)]
            carried_over = len(sprint_names) > 1  # ticket spans multiple sprints
            tickets.append({
                "key":          issue["key"],
                "summary":      clean_title(f.get("summary", "")),
                "status":       f.get("status", {}).get("name", "Unknown"),
                "assignee":     (f.get("assignee") or {}).get("displayName", "Unassigned"),
                "sp":           int(raw_sp) if raw_sp is not None else None,
                "type":         f.get("issuetype", {}).get("name", ""),
                "sprints":      sprint_names,
                "carried_over": carried_over,
            })

        if data.get("isLast", True):
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return tickets


# ─── METRICS ──────────────────────────────────────────────
def build_metrics(tickets, sprint_start=None, sprint_days=None):
    """Build metrics — accepts dynamic sprint dates for correct burndown per sprint"""
    # Use passed sprint dates or fall back to constants
    s_start = sprint_start or SPRINT_START
    s_days  = sprint_days  or SPRINT_DAYS

    total = len(tickets)
    done    = [t for t in tickets if t["status"] in DONE_STATUSES]
    blocked = [t for t in tickets if t["status"] in BLOCKED_STATUSES]
    sc = {}
    for t in tickets:
        sc[t["status"]] = sc.get(t["status"], 0) + 1
    dev_map = {}
    for t in tickets:
        d = t["assignee"]
        if d not in dev_map:
            dev_map[d] = dict(total=0,done=0,active=0,blocked=0,todo=0,totalSP=0,doneSP=0,blockedSP=0)
        m = dev_map[d]; sp = t["sp"] or 0
        m["total"] += 1; m["totalSP"] += sp
        if t["status"] in DONE_STATUSES:      m["done"] += 1;    m["doneSP"] += sp
        elif t["status"] in BLOCKED_STATUSES: m["blocked"] += 1; m["blockedSP"] += sp
        elif t["status"] in ACTIVE_STATUSES:  m["active"] += 1
        else:                                 m["todo"] += 1
    total_sp   = sum(t["sp"] or 0 for t in tickets)
    done_sp    = sum(t["sp"] or 0 for t in done)
    blocked_sp = sum(t["sp"] or 0 for t in blocked)
    today = date.today()
    current_day = max(1, min((today - s_start).days + 1, s_days))
    ideal = max(0, round(total - (total / s_days) * (current_day - 1))) if s_days else total
    actual = total - len(done)
    gap = actual - ideal
    return dict(total=total, done=done, blocked=blocked, sc=sc, dev_map=dev_map,
                total_sp=total_sp, done_sp=done_sp, blocked_sp=blocked_sp,
                missing_sp=sum(1 for t in tickets if not t["sp"]),
                current_day=current_day, ideal=ideal, actual=actual, gap=gap,
                sprint_start=s_start, sprint_days=s_days,
                status=("on-track" if gap<=0 else "slight-risk" if gap<=5 else "behind"),
                tickets=tickets)


# ─── SLACK ────────────────────────────────────────────────
def post_to_slack(blocked, m):
    if not SLACK_WEBHOOK:
        return False, "No webhook"
    pct = round(len(m["done"])/m["total"]*100) if m["total"] else 0
    emoji = {"on-track":"🎯","slight-risk":"⚠️","behind":"🚨"}[m["status"]]
    label = {"on-track":"On Track","slight-risk":"Slight Risk","behind":"Behind"}[m["status"]]
    lines = [f"• `{t['key']}` — {t['summary'][:55]}{'...' if len(t['summary'])>55 else ''} _({t['assignee'].split()[0]})_" for t in blocked]
    payload = {"blocks":[
        {"type":"header","text":{"type":"plain_text","text":f"🚀 Jules Sprint Update — Day {m['current_day']}/{SPRINT_DAYS}"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*Sprint Health*\n{emoji} {label}"},
            {"type":"mrkdwn","text":f"*Progress*\n✅ {len(m['done'])}/{m['total']} ({pct}%)"},
            {"type":"mrkdwn","text":f"*Story Points*\n💎 {m['done_sp']}/{m['total_sp']} SP"},
            {"type":"mrkdwn","text":f"*Days Left*\n📅 {SPRINT_DAYS-m['current_day']} days"},
        ]},
        {"type":"divider"},
    ]}
    if blocked:
        payload["blocks"].append({"type":"section","text":{"type":"mrkdwn","text":f"🚫 *{len(blocked)} Blocked*\n"+"\n".join(lines)}})
        payload["blocks"].append({"type":"actions","elements":[{"type":"button","text":{"type":"plain_text","text":"📊 Open Dashboard"},"url":"https://julesdashboard.streamlit.app","style":"primary"}]})
    r = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
    return r.status_code == 200, r.text


# ─── OVERVIEW TAB ─────────────────────────────────────────
def render_overview(m, tickets=[]):
    total = m["total"]; done_ct = len(m["done"]); blocked_ct = len(m["blocked"])
    carried_ct = sum(1 for t in tickets if t.get("carried_over", False))

    # KPI row using st.metric (native — always renders correctly)
    c = st.columns(7)
    c[0].metric("🎯 Total", total)
    c[1].metric("✅ Done", done_ct, help="Jules definition")
    c[2].metric("⏳ Remaining", total - done_ct)
    c[3].metric("🚫 Blocked", blocked_ct)
    c[4].metric("💎 Total SP", m["total_sp"])
    c[5].metric("✨ SP Done", m["done_sp"])
    pct = round(done_ct/total*100) if total else 0
    c[6].metric("📊 Sprint Done", f"{pct}%")

    # Carried over indicator
    if carried_ct > 0:
        st.markdown(
            f'<div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);'
            f'border-radius:10px;padding:10px 16px;margin-top:8px;display:flex;align-items:center;gap:10px;">'
            f'<span style="font-size:20px;">↩</span>'
            f'<div><div style="color:#fbbf24;font-weight:700;font-size:13px;">{carried_ct} Carried-Over Tickets</div>'
            f'<div style="color:#92400e;font-size:11px;">These tickets were started in a previous sprint — metrics include them</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        # ── Attractive grouped donut chart ──
        # Group into 5 clean categories for clarity
        done_ct2   = len(m["done"])
        review_ct  = m["sc"].get("PO review",0) + m["sc"].get("Tech review",0) + m["sc"].get("Tech strategy",0)
        qa_ct      = m["sc"].get("PO/QA Test run",0)
        active_ct  = m["sc"].get("In Progress",0) + m["sc"].get("AIM OF THE DAY",0) + m["sc"].get("Aim Of The week",0)
        pending_ct = m["sc"].get("To Do",0) + m["sc"].get("PO not valid",0)
        blocked_ct2= len(m["blocked"])

        pie_labels = ["✅ Done", "👀 In Review", "🧪 QA Test", "⚡ Active", "📋 Pending", "🚫 Blocked"]
        pie_values = [done_ct2, review_ct, qa_ct, active_ct, pending_ct, blocked_ct2]
        pie_colors = ["#10b981", "#818cf8", "#6ee7b7", "#38bdf8", "#64748b", "#f87171"]
        pie_pulls  = [0.04, 0, 0, 0, 0, 0.06]  # pull out Done and Blocked slightly

        fig = go.Figure(go.Pie(
            labels=pie_labels,
            values=pie_values,
            hole=0.62,
            pull=pie_pulls,
            marker=dict(
                colors=pie_colors,
                line=dict(color="#080c1a", width=3),
            ),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value} tickets<br>%{percent}<extra></extra>",
            direction="clockwise",
            sort=False,
        ))

        # Center annotation
        pct_done = round(done_ct2 / total * 100) if total else 0
        fig.add_annotation(
            text=f"<b>{pct_done}%</b><br><span style='font-size:11px;'>Done</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=22, color="#10b981", family="DM Sans"),
            xanchor="center", yanchor="middle",
        )

        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="v",
                x=1.02, y=0.5,
                xanchor="left",
                font=dict(size=11, color="#94a3b8"),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(0,0,0,0)",
            ),
            height=300,
            margin=dict(l=0, r=10, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">📋 Group Summary</div>', unsafe_allow_html=True)
        groups = [
            ("✅ Done", done_ct, "#10b981"),
            ("👀 In Review", m["sc"].get("PO review",0)+m["sc"].get("Tech review",0), "#818cf8"),
            ("🧪 QA / Test run", m["sc"].get("PO/QA Test run",0), "#6ee7b7"),
            ("⚡ Active", m["sc"].get("In Progress",0)+m["sc"].get("AIM OF THE DAY",0), "#38bdf8"),
            ("📅 Aim of Week", m["sc"].get("Aim Of The week",0), "#bae6fd"),
            ("📋 To Do", m["sc"].get("To Do",0), "#64748b"),
            ("⚠️ PO Not Valid", m["sc"].get("PO not valid",0), "#f97316"),
            ("🔬 Tech Strategy", m["sc"].get("Tech strategy",0), "#a78bfa"),
            ("🚫 Blocked", blocked_ct, "#f87171"),
        ]
        for label, val, color in groups:
            pct_bar = (val/total*100) if total else 0
            st.markdown(f"""
<div style="margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:4px;">
<span>{label}</span>
<span style="color:{color};font-weight:700;font-family:'Space Mono',monospace;">{val}<span style="color:#1e3a5f">/{total}</span></span>
</div>
<div style="background:#1e2d47;border-radius:999px;height:6px;overflow:hidden;">
<div style="width:{pct_bar:.1f}%;height:100%;border-radius:999px;
  background:linear-gradient(90deg,{color},{color}88,{color});background-size:200% auto;
  animation:shimmerBar 2.5s linear infinite;box-shadow:0 0 6px {color}40;">
</div></div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Team Workload — using native st.columns + st.markdown per card ──
    st.markdown('<div class="section-header">👥 Team Workload</div>', unsafe_allow_html=True)
    devs = [(n,d) for n,d in m["dev_map"].items() if n!="Unassigned"]
    devs.sort(key=lambda x: x[1]["total"], reverse=True)
    cols = st.columns(len(devs))
    for i, (name, d) in enumerate(devs):
        color = DEV_COLORS.get(name, "#64748b")
        pct = round(d["done"]/d["total"]*100) if d["total"] else 0
        initials = "".join(p[0] for p in name.split()[:2])
        fname = name.split()[0]
        linitial = name.split()[1][0] if len(name.split())>1 else ""
        with cols[i]:
            # Use native metrics for the numbers
            if d["blocked"] >= 2:
                st.error(f"⚠️ {d['blocked']} BLOCKED", icon=None)
            st.markdown(f"""<div style="background:{color}15;border:1px solid {color}30;border-radius:12px;padding:12px;margin-bottom:8px;">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
<div style="width:30px;height:30px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#0a0e1a;">{initials}</div>
<div><b style="font-size:12px;">{fname} {linitial}.</b><br><span style="font-size:9px;color:#475569;">{d['total']} tickets · {d['totalSP']} SP</span></div>
<b style="margin-left:auto;color:{color};font-size:16px;">{pct}%</b>
</div>
<div style="background:#1e2d47;border-radius:99px;height:4px;margin-bottom:8px;">
<div style="width:{pct}%;height:100%;border-radius:99px;background:{color};"></div>
</div></div>""", unsafe_allow_html=True)
            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(f"<div style='text-align:center;font-size:9px;color:#10b981;font-weight:700;'>✅<br>{d['done']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='text-align:center;font-size:9px;color:#38bdf8;font-weight:700;'>⚡<br>{d['active']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align:center;font-size:9px;color:#f87171;font-weight:700;'>🚫<br>{d['blocked']}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div style='text-align:center;font-size:9px;color:#64748b;font-weight:700;'>📋<br>{d['todo']}</div>", unsafe_allow_html=True)


# ─── BURNDOWN TAB ─────────────────────────────────────────
def render_burndown(m):
    total   = m["total"]; cd = m["current_day"]
    s_start = m.get("sprint_start", SPRINT_START)
    s_days  = m.get("sprint_days",  SPRINT_DAYS)
    # Build key day markers dynamically based on sprint length
    step = max(1, s_days // 8)
    key_days = sorted(set([1] + list(range(step, s_days, step)) + [s_days, cd]))
    rows = []
    for d in key_days:
        dt = s_start + pd.Timedelta(days=d-1)
        ideal = max(0, round(total-(total/s_days)*(d-1))) if s_days else 0
        actual = total if d==1 else (total-len(m["done"]) if d==cd else None)
        rows.append({"label": f"Today {dt.strftime('%d %b')}" if d==cd else dt.strftime('%d %b'), "ideal": ideal, "actual": actual})
    df = pd.DataFrame(rows)

    gap = m["gap"]
    gap_color = "#10b981" if gap<=0 else "#fbbf24" if gap<=5 else "#f87171"
    st.markdown(f"**🔥 Sprint Burndown** — Day {cd}/{SPRINT_DAYS} · {SPRINT_DAYS-cd} days left")

    c = st.columns(5)
    for col, (lbl, val, clr) in zip(c, [
        ("Sprint Day", f"{cd}/{SPRINT_DAYS}", "#00d4ff"),
        ("Days Left", SPRINT_DAYS-cd, "#818cf8"),
        ("Ideal", m["ideal"], "#f87171"),
        ("Actual", m["actual"], "#00d4ff"),
        ("Gap", "On Track 🎯" if gap<=0 else f"+{gap} Behind", gap_color),
    ]):
        col.markdown(f"<div style='background:rgba(15,22,41,0.8);border:1px solid {clr}25;border-radius:10px;padding:10px;text-align:center;'><div style='font-size:16px;font-weight:900;color:{clr};font-family:Space Mono,monospace;'>{val}</div><div style='font-size:9px;color:#475569;text-transform:uppercase;margin-top:3px;'>{lbl}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["label"], y=df["ideal"], name="Ideal", mode="lines+markers",
        line=dict(color="#f87171",width=2,dash="dash"), marker=dict(color="#f87171",size=6),
        fill="tozeroy", fillcolor="rgba(248,113,113,0.05)", hovertemplate="<b>%{x}</b><br>Ideal: %{y}<extra></extra>"))
    fig.add_trace(go.Scatter(x=df["label"], y=df["actual"], name="Actual", mode="lines+markers",
        line=dict(color="#00d4ff",width=3), marker=dict(color="#00d4ff",size=8),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.06)", connectgaps=True,
        hovertemplate="<b>%{x}</b><br>Actual: %{y}<extra></extra>"))
    fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans",color="#64748b"),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#94a3b8")),
        xaxis=dict(gridcolor="#1e2d47",tickfont=dict(size=10),tickangle=-20),
        yaxis=dict(gridcolor="#1e2d47",tickfont=dict(size=10),range=[0,total+3]),
        margin=dict(l=0,r=0,t=10,b=40), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    elapsed = round(((cd-1)/(SPRINT_DAYS-1))*100)
    st.progress(elapsed/100, text=f"Sprint {elapsed}% elapsed · {SPRINT_DAYS-cd} days remaining")


# ─── VELOCITY TAB ─────────────────────────────────────────
def render_velocity(m):
    devs = [(n,d) for n,d in m["dev_map"].items() if n!="Unassigned"]
    devs.sort(key=lambda x: x[1]["total"], reverse=True)
    st.markdown('<div class="section-header">⚡ Developer Velocity</div>', unsafe_allow_html=True)
    names = [n.split()[0] for n,_ in devs]
    fig = go.Figure()
    for lbl, key, clr in [("Done","done","#10b981"),("Active","active","#38bdf8"),("Blocked","blocked","#f87171"),("Todo","todo","#334155")]:
        fig.add_trace(go.Bar(name=lbl, x=names, y=[d[key] for _,d in devs], marker_color=clr,
            hovertemplate=f"<b>%{{x}}</b><br>{lbl}: %{{y}}<extra></extra>"))
    fig.update_layout(barmode="stack", height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans",color="#64748b"),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#94a3b8"),orientation="h",y=-0.15),
        xaxis=dict(gridcolor="#1e2d47"), yaxis=dict(gridcolor="#1e2d47"),
        margin=dict(l=0,r=0,t=10,b=40))
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(len(devs))
    for i, (name, d) in enumerate(devs):
        color = DEV_COLORS.get(name,"#64748b")
        pct = round(d["done"]/d["total"]*100) if d["total"] else 0
        initials = "".join(p[0] for p in name.split()[:2])
        dw = round(d["done"]/d["total"]*100) if d["total"] else 0
        aw = round(d["active"]/d["total"]*100) if d["total"] else 0
        bw = round(d["blocked"]/d["total"]*100) if d["total"] else 0
        with cols[i]:
            st.markdown(f"""<div style="background:rgba(15,22,41,0.9);border:1px solid {color}28;border-radius:14px;padding:14px;">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
<div style="width:32px;height:32px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#0a0e1a;">{initials}</div>
<div style="flex:1;"><div style="font-weight:700;font-size:12px;">{name}</div><div style="font-size:9px;color:#475569;">{d['total']} tickets · {d['totalSP']} SP</div></div>
<div style="font-size:18px;font-weight:900;color:{color};font-family:'Space Mono',monospace;">{pct}%</div>
</div>
<div style="background:#1e2d47;border-radius:999px;height:5px;margin-bottom:8px;overflow:hidden;display:flex;">
<div style="width:{dw}%;background:#10b981;"></div><div style="width:{aw}%;background:#38bdf8;"></div><div style="width:{bw}%;background:#f87171;"></div>
</div>
<div style="display:flex;gap:4px;flex-wrap:wrap;">
<span style="background:#10b98115;border-radius:4px;padding:2px 6px;font-size:8px;color:#10b981;font-weight:700;">Done {d['done']}</span>
<span style="background:#818cf815;border-radius:4px;padding:2px 6px;font-size:8px;color:#818cf8;font-weight:700;">Active {d['active']}</span>
<span style="background:#f8717115;border-radius:4px;padding:2px 6px;font-size:8px;color:#f87171;font-weight:700;">Blocked {d['blocked']}</span>
<span style="background:#fb923c15;border-radius:4px;padding:2px 6px;font-size:8px;color:#fb923c;font-weight:700;">SP {d['doneSP']}/{d['totalSP']}</span>
</div></div>""", unsafe_allow_html=True)


# ─── POINTS TAB ───────────────────────────────────────────
def render_points(m):
    c = st.columns(5)
    c[0].metric("💎 Total SP", m["total_sp"])
    c[1].metric("✅ SP Done", m["done_sp"], delta=f"{round(m['done_sp']/m['total_sp']*100) if m['total_sp'] else 0}%")
    c[2].metric("⏳ SP Left", m["total_sp"]-m["done_sp"])
    c[3].metric("🚫 SP Blocked", m["blocked_sp"])
    c[4].metric("⚠️ No SP", m["missing_sp"], help="Tickets missing story point estimates")
    st.markdown("<br>", unsafe_allow_html=True)
    devs = [(n,d) for n,d in m["dev_map"].items() if n!="Unassigned"]
    devs.sort(key=lambda x: x[1]["total"], reverse=True)
    st.markdown('<div class="section-header">📊 Story Points per Developer</div>', unsafe_allow_html=True)
    names = [n.split()[0] for n,_ in devs]
    fig = go.Figure()
    for lbl, key, clr in [("Done SP","doneSP","#10b981"),("Blocked SP","blockedSP","#f87171"),("Rest SP",None,"#334155")]:
        vals = [d.get(key,0) if key else max(0,d["totalSP"]-d.get("doneSP",0)-d.get("blockedSP",0)) for _,d in devs]
        fig.add_trace(go.Bar(name=lbl, x=names, y=vals, marker_color=clr,
            hovertemplate=f"<b>%{{x}}</b><br>{lbl}: %{{y}}<extra></extra>"))
    fig.update_layout(barmode="stack", height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans",color="#64748b"),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#94a3b8"),orientation="h",y=-0.2),
        xaxis=dict(gridcolor="#1e2d47"), yaxis=dict(gridcolor="#1e2d47"),
        margin=dict(l=0,r=0,t=10,b=40))
    st.plotly_chart(fig, use_container_width=True)


# ─── ALL TICKETS TAB ──────────────────────────────────────
def render_tickets(m, tickets=[]):
    tickets = m["tickets"]
    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px;animation:fadeInUp 0.4s ease both;">
  <div>
    <span style="font-size:16px;font-weight:700;">🎫 All Sprint Tickets ({len(tickets)})</span>
    <span style="font-size:11px;color:#475569;margin-left:10px;">Full titles · AAWU/AAD stripped · Click to open in Jira</span>
  </div>
  <span style="font-size:9px;color:#34d399;background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);padding:4px 10px;border-radius:6px;">🔗 Clickable tickets</span>
</div>""", unsafe_allow_html=True)
    for status in STATUS_ORDER:
        group = [t for t in tickets if t["status"]==status]
        if not group:
            continue
        sc = STATUS_COLORS.get(status,"#64748b")
        rows = ""
        for t in group:
            color = DEV_COLORS.get(t["assignee"],"#64748b")
            initials = "".join(p[0] for p in t["assignee"].split()[:2])
            fname = t["assignee"].split()[0]
            sp_badge = f'<span style="font-size:9px;color:#fb923c;font-weight:800;background:rgba(251,146,60,0.1);padding:2px 5px;border-radius:3px;">{t["sp"]}sp</span>' if t["sp"] else ""
            bg = "rgba(248,113,113,0.04)" if status=="Blocked" else "rgba(255,255,255,0.015)"
            row_cls = "ticket-row-wrap ticket-row-blocked" if status=="Blocked" else "ticket-row-wrap"
            rows += f'<div class="{row_cls}">'
            if t.get("carried_over"):
                rows += '<span style="font-size:9px;background:rgba(251,191,36,0.15);border:1px solid rgba(251,191,36,0.4);color:#fbbf24;border-radius:4px;padding:1px 5px;margin-right:4px;white-space:nowrap;">↩ carried</span>'
                rows += '<span style="font-size:9px;background:rgba(251,191,36,0.15);border:1px solid rgba(251,191,36,0.4);color:#fbbf24;border-radius:4px;padding:1px 5px;margin-right:4px;white-space:nowrap;">↩ carried</span>'
            rows += f'<span class="ticket-key" style="min-width:70px;flex-shrink:0;"><a href="{JIRA_BASE}/browse/{t["key"]}" target="_blank">{t["key"]}</a></span>'
            rows += f'<span style="font-size:9px;color:#7dd3fc;background:rgba(129,140,248,0.1);border-radius:3px;padding:2px 5px;min-width:44px;text-align:center;flex-shrink:0;">{t["type"][:7]}</span>'
            rows += f'<span class="ticket-summary" style="flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;"><a href="{JIRA_BASE}/browse/{t["key"]}" target="_blank">{t["summary"]}</a></span>'
            rows += f'<span style="font-size:9px;color:{color};font-weight:700;background:{color}20;padding:2px 7px;border-radius:3px;white-space:nowrap;flex-shrink:0;">{initials} {fname}</span>'
            rows += sp_badge + "</div>"
        st.markdown(f'<div style="margin-bottom:14px;"><div style="font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:5px;color:{sc};">{status} ({len(group)})</div>{rows}</div>', unsafe_allow_html=True)


# ─── MAIN ─────────────────────────────────────────────────
def main():
    # Start background scheduler once per process
    if "scheduler_started" not in st.session_state:
        start_scheduler()
        st.session_state.scheduler_started = True

    if not check_pin():
        return

    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown("---")

        # Sprint selector
        st.markdown("**🏃 Sprint Filter**")
        available_sprints = fetch_available_sprints()

        sprint_options = {"🟢 Current Sprint (Active)": None}
        for s in available_sprints:
            state_icon = "🟢" if s["state"] == "active" else "✅"
            label = f"{state_icon} {s['name']}"
            if s["end"]:
                label += f"  ·  {s['end']}"
            sprint_options[label] = s["id"]

        selected_label = st.selectbox(
            "Select sprint",
            options=list(sprint_options.keys()),
            index=0,
            label_visibility="collapsed"
        )
        selected_sprint_id   = sprint_options[selected_label]
        selected_sprint_name = selected_label.split("  ·")[0].lstrip("🟢✅ ").strip()

        # Show carried-over warning
        if selected_sprint_id:
            st.caption("📌 Tickets from previous sprints are tagged as carried over")

        st.markdown("---")
        show_carried = st.toggle("Show carried-over tickets", value=True)
        if not show_carried:
            st.caption("🚫 Carried-over tickets hidden from view")
        st.markdown("---")
        auto_slack = st.toggle("Auto-post blocked to Slack", value=False)
        st.markdown("---")
        # Show selected sprint info
        if sprint_info:
            state_color = "#10b981" if sprint_info["state"] == "active" else "#64748b"
            st.markdown(
                f'<div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.15);'
                f'border-radius:8px;padding:10px 12px;margin-bottom:8px;">'
                f'<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Selected Sprint</div>'
                f'<div style="color:#e2e8f0;font-weight:700;font-size:13px;margin-top:2px;">{selected_sprint_name}</div>'
                f'<div style="font-size:10px;margin-top:4px;">'
                f'<span style="color:{state_color};">● {sprint_info["state"].upper()}</span>'
                f'<span style="color:#475569;margin-left:8px;">{sprint_info.get("start","?")} → {sprint_info.get("end","?")}</span>'
                f'</div></div>',
                unsafe_allow_html=True
            )
        st.markdown(f"**Project:** {PROJECT}")
        st.markdown(f"**Jira:** [minehub.atlassian.net]({JIRA_BASE})")

    # Loading screen
    placeholder = st.empty()
    placeholder.markdown("""
    <style>
    @keyframes rocket-launch{0%,100%{transform:translateY(0) rotate(-5deg)}50%{transform:translateY(-20px) rotate(5deg)}}
    @keyframes prog-bar{0%{width:0%}100%{width:95%}}
    @keyframes glow-p{0%,100%{box-shadow:0 0 20px rgba(0,212,255,0.3)}50%{box-shadow:0 0 40px rgba(0,212,255,0.7)}}
    @keyframes shimBar{0%{background-position:-300% center}100%{background-position:300% center}}
    </style>
    <div style="text-align:center;padding:80px 20px;min-height:55vh;display:flex;flex-direction:column;align-items:center;justify-content:center;">
        <div style="font-size:72px;animation:rocket-launch 1.5s ease-in-out infinite;margin-bottom:28px;
            filter:drop-shadow(0 0 20px rgba(0,212,255,0.8)) drop-shadow(0 0 40px rgba(129,140,248,0.4));">🚀</div>
        <h2 style="background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6,#00d4ff);background-size:300% auto;
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:28px;font-weight:900;margin-bottom:8px;animation:shimBar 2s linear infinite;">
            Fetching Sprint Data
        </h2>
        <p style="color:#475569;font-size:13px;margin-bottom:32px;letter-spacing:1px;">Connecting to Jira · JENG Project</p>
        <div style="width:300px;height:4px;background:rgba(255,255,255,0.05);border-radius:99px;overflow:hidden;margin-bottom:24px;animation:glow-p 2s infinite;">
            <div style="height:100%;background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6);border-radius:99px;animation:prog-bar 2.5s ease-out forwards;"></div>
        </div>
        <div style="display:flex;gap:24px;font-size:10px;color:#334155;letter-spacing:1px;">
            <span>🔐 Authenticating</span><span>📡 Fetching tickets</span><span>📊 Building metrics</span>
        </div>
    </div>""", unsafe_allow_html=True)

    try:
        tickets = fetch_jira_tickets()
        fetched_at = datetime.now().strftime("%d %b %Y, %H:%M")
    except Exception as e:
        placeholder.empty()
        st.error(f"❌ Failed to fetch Jira data: {e}")
        st.info("Check JIRA_EMAIL and JIRA_API_TOKEN in Streamlit secrets.")
        return
    placeholder.empty()

    # Filter carried-over tickets if toggle is off
    if not show_carried:
        tickets = [t for t in tickets if not t.get("carried_over", False)]

    # Build sprint dates from selected sprint
    sprint_info = next((s for s in available_sprints if s["id"] == selected_sprint_id), None)
    if sprint_info and sprint_info.get("start"):
        sel_start = date.fromisoformat(sprint_info["start"])
        sel_end   = date.fromisoformat(sprint_info["end"]) if sprint_info.get("end") else date.today()
        sel_days  = max(1, (sel_end - sel_start).days)
    else:
        sel_start = SPRINT_START
        sel_days  = SPRINT_DAYS

    m = build_metrics(tickets, sprint_start=sel_start, sprint_days=sel_days)

    if auto_slack and SLACK_WEBHOOK and m["blocked"]:
        ok, _ = post_to_slack(m["blocked"], m)
        if ok: st.toast("✅ Posted to Slack!", icon="📣")

    # Animated floating particles background
    st.markdown("""
    <div id="particles">
    """ + "".join([
        f'<div class="particle" style="left:{(i*37)%100}%;width:{3+i%4}px;height:{3+i%4}px;'
        f'background:{"#00d4ff" if i%3==0 else "#818cf8" if i%3==1 else "#10b981"};'
        f'opacity:0.15;animation-duration:{8+i*1.3:.1f}s;animation-delay:{i*0.7:.1f}s;"></div>'
        for i in range(12)
    ]) + """
    </div>
    """, unsafe_allow_html=True)

    # Header
    days_left = SPRINT_DAYS - m["current_day"]
    pct = round(len(m["done"])/m["total"]*100) if m["total"] else 0
    sc = "#10b981" if m["status"]=="on-track" else "#fbbf24" if m["status"]=="slight-risk" else "#f87171"
    sl = "On Track 🎯" if m["status"]=="on-track" else "Slight Risk ⚠️" if m["status"]=="slight-risk" else "Behind 🚨"
    st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
<div><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span class="live-dot"></span><span style="font-size:10px;color:#10b981;text-transform:uppercase;letter-spacing:2px;font-weight:600;">Live · Jira · 5 min cache</span></div>
<h1 style="font-size:26px;font-weight:900;margin:0;background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:fadeInLeft 0.6s ease both;">Jules Sprint Dashboard<span class="cursor">|</span></h1>
<div style="font-size:12px;color:#475569;margin-top:4px;">{selected_sprint_name} · {sel_start.strftime("%b %d")} – {(sel_start + pd.Timedelta(days=sel_days)).strftime("%b %d, %Y")} · {fetched_at}</div></div>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<div style="background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.18);border-radius:10px;padding:10px 16px;font-size:12px;color:#7dd3fc;text-align:center;">📅 Day <strong>{m["current_day"]}</strong> / {SPRINT_DAYS}<br><span style="color:#475569;font-size:10px;">{days_left} days left</span></div>
<div style="background:{sc}12;border:1px solid {sc}35;border-radius:10px;padding:10px 16px;font-size:12px;color:{sc};text-align:center;">{sl}<br><span style="color:#475569;font-size:10px;">{pct}% done</span></div>
</div></div>""", unsafe_allow_html=True)

    # Refresh / Slack buttons
    if SLACK_WEBHOOK:
        b1, b2, b3 = st.columns([6,1,1])
        with b2:
            if st.button("📣 Slack"):
                ok, msg = post_to_slack(m["blocked"], m)
                st.toast("✅ Posted!" if ok else f"❌ {msg}", icon="📣" if ok else "⚠️")
        with b3:
            if st.button("🔄 Refresh"):
                st.cache_data.clear(); st.rerun()
    else:
        b1, b2 = st.columns([7,1])
        with b2:
            if st.button("🔄 Refresh"):
                st.cache_data.clear(); st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"📊 Overview",
        f"🔥 Burndown",
        f"⚡ Velocity",
        f"💎 Story Points",
        f"🎫 All Tickets ({len(tickets)})",
    ])
    with tab1: render_overview(m, tickets)
    with tab2: render_burndown(m)
    with tab3: render_velocity(m)
    with tab4: render_points(m)
    with tab5: render_tickets(m, tickets)

    st.markdown(
        f"<div style='text-align:center;font-size:9px;color:#334155;border-top:1px solid rgba(0,212,255,0.06);padding-top:14px;margin-top:24px;letter-spacing:1px;'>"
        f"Jules Product &nbsp;·&nbsp; MineHub &nbsp;·&nbsp; {selected_sprint_name} &nbsp;·&nbsp; {m['total']} tickets &nbsp;·&nbsp; {m['total_sp']} SP &nbsp;·&nbsp; {fetched_at}"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
