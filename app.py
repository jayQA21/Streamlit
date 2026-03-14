import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import re
import os
import json
import time
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────
JIRA_EMAIL    = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN    = os.getenv("JIRA_API_TOKEN", "").replace("\n", "").replace("\r", "").replace(" ", "").strip()
JIRA_BASE     = os.getenv("JIRA_BASE_URL", "https://minehub.atlassian.net")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
DASHBOARD_PIN = os.getenv("DASHBOARD_PIN", "")

CLOUD_ID      = "7a6832b7-8317-4cb3-b886-1a6da3749a41"
PROJECT       = "JENG"
SPRINT_NAME   = "Release Sprint 3"
SPRINT_START  = date(2026, 2, 24)
SPRINT_END    = date(2026, 4, 12)
SPRINT_DAYS   = 48

DONE_STATUSES    = {"Done", "PO/QA VALID", "Demo", "In Production", "CS Reviewed"}
BLOCKED_STATUSES = {"Blocked"}
ACTIVE_STATUSES  = {"In Progress", "AIM OF THE DAY", "Tech review", "PO review",
                     "PO/QA Test run", "Aim Of The week", "PO not valid"}

DEV_COLORS = {
    "Nikita Vaidya": "#818cf8",
    "Satadru Roy":   "#f472b6",
    "Rizky Ario":    "#fb923c",
    "Jay Pitroda":   "#34d399",
    "Unassigned":    "#64748b",
}
STATUS_COLORS = {
    "Done":            "#10b981",
    "PO/QA VALID":     "#34d399",
    "PO/QA Test run":  "#6ee7b7",
    "Demo":            "#a7f3d0",
    "In Production":   "#059669",
    "CS Reviewed":     "#065f46",
    "PO review":       "#818cf8",
    "Tech review":     "#a78bfa",
    "In Progress":     "#38bdf8",
    "AIM OF THE DAY":  "#7dd3fc",
    "Aim Of The week": "#bae6fd",
    "To Do":           "#64748b",
    "Blocked":         "#f87171",
    "PO not valid":    "#f97316",
}
STATUS_ORDER = [
    "Done", "PO/QA VALID", "Demo", "In Production", "CS Reviewed",
    "PO/QA Test run", "Tech review", "PO review",
    "AIM OF THE DAY", "In Progress", "Aim Of The week",
    "To Do", "Blocked", "PO not valid",
]

# ─── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(
    page_title="Jules Sprint Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── GLOBAL CSS ───────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;900&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #080c1a !important;
    color: #e2e8f0 !important;
}
.stApp { background: radial-gradient(ellipse at 20% 10%, #0d1b3e 0%, #080c1a 55%, #050710 100%) !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, rgba(15,22,41,0.95), rgba(20,30,55,0.9)) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 14px !important;
    padding: 14px !important;
}
[data-testid="stMetricValue"] { color: #00d4ff !important; font-family: 'Space Mono', monospace !important; font-size: 1.8rem !important; }
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.7rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* Tabs */
[data-baseweb="tab-list"] { background: rgba(15,22,41,0.8) !important; border-radius: 12px !important; padding: 4px !important; gap: 2px !important; }
[data-baseweb="tab"] { background: transparent !important; color: #475569 !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 0.75rem !important; }
[aria-selected="true"] { background: rgba(0,212,255,0.1) !important; color: #00d4ff !important; border-bottom: 2px solid #00d4ff !important; }

/* Cards */
.dash-card {
    background: rgba(15,22,41,0.9);
    border: 1px solid rgba(0,212,255,0.1);
    border-radius: 16px;
    padding: 20px 22px;
    margin-bottom: 12px;
}

/* Ticket rows */
.ticket-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 7px;
    margin-bottom: 3px;
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.05);
    font-size: 13px;
}
.ticket-row.blocked { border-color: rgba(248,113,113,0.2) !important; background: rgba(248,113,113,0.04) !important; }
.ticket-key a { color: #00d4ff !important; font-family: 'Space Mono', monospace !important; font-size: 11px !important; text-decoration: none !important; border-bottom: 1px dotted rgba(0,212,255,0.4); }
.ticket-key a:hover { color: #fff !important; }
.ticket-summary a { color: #94a3b8 !important; text-decoration: none !important; }
.ticket-summary a:hover { color: #c4b5fd !important; }

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 10px;
    font-weight: 700;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(129,140,248,0.1)) !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    color: #00d4ff !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { border-color: #00d4ff !important; background: rgba(0,212,255,0.15) !important; }

/* Slack button */
.slack-btn > button {
    background: linear-gradient(135deg, rgba(74,21,75,0.3), rgba(74,21,75,0.2)) !important;
    border: 1px solid rgba(224,30,90,0.4) !important;
    color: #ff6eb4 !important;
}

/* Divider */
hr { border-color: rgba(0,212,255,0.08) !important; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg, #00d4ff, #818cf8) !important; border-radius: 99px !important; }

/* Loading animation */
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}
.skeleton {
    background: linear-gradient(90deg, rgba(30,45,71,0.5) 25%, rgba(0,212,255,0.05) 50%, rgba(30,45,71,0.5) 75%);
    background-size: 1000px 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
    height: 20px;
    margin-bottom: 8px;
}
.live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulse 2s infinite;
    margin-right: 6px;
}
</style>
""", unsafe_allow_html=True)


# ─── PIN PROTECTION ───────────────────────────────────────
def check_pin():
    if not DASHBOARD_PIN:
        return True
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    st.markdown("""
    <div style="max-width:340px;margin:80px auto;text-align:center;">
        <div style="font-size:48px;margin-bottom:16px;">🔐</div>
        <h2 style="color:#00d4ff;font-family:'DM Sans',sans-serif;margin-bottom:8px;">Jules Dashboard</h2>
        <p style="color:#475569;font-size:13px;margin-bottom:24px;">Enter PIN to access</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN", type="password", placeholder="Enter PIN...", label_visibility="collapsed")
        if st.button("→ Enter", use_container_width=True):
            if pin == DASHBOARD_PIN:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect PIN")
    return False


# ─── JIRA FETCH ───────────────────────────────────────────
def clean_title(summary: str) -> str:
    summary = re.sub(r'^(AAWU,?\s*|AAD,?\s*)', '', summary, flags=re.IGNORECASE)
    return summary.lstrip(',').strip()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_jira_tickets():
    """Fetch live sprint tickets from Jira REST API. Cached for 5 minutes."""
    url = f"{JIRA_BASE}/rest/api/3/search"
    headers = {"Accept": "application/json"}
    auth = (JIRA_EMAIL, JIRA_TOKEN)
    params = {
        "jql": f"project = {PROJECT} AND sprint in openSprints() ORDER BY created DESC",
        "maxResults": 100,
        "fields": "summary,status,assignee,customfield_10024,issuetype,priority",
    }
    resp = requests.get(url, headers=headers, auth=auth, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    tickets = []
    for issue in data.get("issues", []):
        f = issue.get("fields", {})
        tickets.append({
            "key":      issue["key"],
            "summary":  clean_title(f.get("summary", "")),
            "raw":      f.get("summary", ""),
            "status":   f.get("status", {}).get("name", "Unknown"),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "sp":       f.get("customfield_10024"),
            "type":     f.get("issuetype", {}).get("name", ""),
        })
    return tickets


# ─── METRICS ──────────────────────────────────────────────
def build_metrics(tickets):
    total = len(tickets)
    done_tickets    = [t for t in tickets if t["status"] in DONE_STATUSES]
    blocked_tickets = [t for t in tickets if t["status"] in BLOCKED_STATUSES]

    status_counts = {}
    for t in tickets:
        status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1

    dev_map = {}
    for t in tickets:
        d = t["assignee"]
        if d not in dev_map:
            dev_map[d] = {"total":0,"done":0,"active":0,"blocked":0,"todo":0,"totalSP":0,"doneSP":0,"blockedSP":0}
        m = dev_map[d]
        sp = t["sp"] or 0
        m["total"] += 1; m["totalSP"] += sp
        if t["status"] in DONE_STATUSES:    m["done"] += 1;    m["doneSP"] += sp
        elif t["status"] in BLOCKED_STATUSES: m["blocked"] += 1; m["blockedSP"] += sp
        elif t["status"] in ACTIVE_STATUSES:  m["active"] += 1
        else:                                 m["todo"] += 1

    total_sp   = sum(t["sp"] or 0 for t in tickets)
    done_sp    = sum(t["sp"] or 0 for t in done_tickets)
    blocked_sp = sum(t["sp"] or 0 for t in blocked_tickets)
    missing_sp = sum(1 for t in tickets if not t["sp"])

    today = date.today()
    current_day = max(1, min((today - SPRINT_START).days + 1, SPRINT_DAYS))
    ideal_today = max(0, round(total - (total / SPRINT_DAYS) * (current_day - 1)))
    actual_today = total - len(done_tickets)
    gap = actual_today - ideal_today
    sprint_status = "on-track" if gap <= 0 else "slight-risk" if gap <= 5 else "behind"

    return {
        "total": total, "done_tickets": done_tickets, "blocked_tickets": blocked_tickets,
        "status_counts": status_counts, "dev_map": dev_map,
        "total_sp": total_sp, "done_sp": done_sp, "blocked_sp": blocked_sp, "missing_sp": missing_sp,
        "current_day": current_day, "ideal_today": ideal_today, "actual_today": actual_today,
        "gap": gap, "sprint_status": sprint_status, "tickets": tickets,
    }


# ─── SLACK ────────────────────────────────────────────────
def post_to_slack(blocked_tickets, m):
    if not SLACK_WEBHOOK:
        return False, "No Slack webhook configured"

    lines = [f"• `{t['key']}` — {t['summary'][:60]}... _(_{t['assignee'].split()[0]}_)_"
             if len(t['summary']) > 60
             else f"• `{t['key']}` — {t['summary']} _({t['assignee'].split()[0]})_"
             for t in blocked_tickets]

    status_emoji = "🎯" if m["sprint_status"] == "on-track" else "⚠️" if m["sprint_status"] == "slight-risk" else "🚨"
    pct = round((len(m["done_tickets"]) / m["total"]) * 100) if m["total"] else 0

    payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"🚀 Jules Sprint Update — Day {m['current_day']}/{SPRINT_DAYS}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Sprint Health*\n{status_emoji} {'On Track' if m['sprint_status']=='on-track' else 'Slight Risk' if m['sprint_status']=='slight-risk' else 'Behind'}"},
                {"type": "mrkdwn", "text": f"*Progress*\n✅ {len(m['done_tickets'])}/{m['total']} tickets ({pct}%)"},
                {"type": "mrkdwn", "text": f"*Story Points*\n💎 {m['done_sp']}/{m['total_sp']} SP done"},
                {"type": "mrkdwn", "text": f"*Days Left*\n📅 {SPRINT_DAYS - m['current_day']} days remaining"},
            ]},
            {"type": "divider"},
        ]
    }

    if blocked_tickets:
        payload["blocks"].append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"🚫 *{len(blocked_tickets)} Blocked Tickets*\n" + "\n".join(lines)}
        })
        payload["blocks"].append({
            "type": "actions",
            "elements": [{"type": "button", "text": {"type": "plain_text", "text": "📊 Open Dashboard"},
                          "url": "https://your-app.streamlit.app", "style": "primary"}]
        })

    resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
    return resp.status_code == 200, resp.text


# ─── ANIMATED LOADING ─────────────────────────────────────
def show_loading_animation():
    loading_html = """
    <div id="loading-overlay" style="
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: radial-gradient(ellipse at 20% 10%, #0d1b3e 0%, #080c1a 55%, #050710 100%);
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        z-index: 9999; font-family: 'DM Sans', sans-serif;
    ">
        <div style="text-align: center;">
            <div style="font-size: 56px; margin-bottom: 20px; animation: bounce 1s infinite alternate;">🚀</div>
            <h2 style="
                background: linear-gradient(90deg, #00d4ff, #818cf8, #f472b6);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                font-size: 28px; font-weight: 900; margin-bottom: 8px;
            ">Jules Sprint Dashboard</h2>
            <p style="color: #475569; font-size: 13px; margin-bottom: 32px;">Fetching live data from Jira...</p>
            <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 28px;">
                <div style="width: 10px; height: 10px; border-radius: 50%; background: #00d4ff;
                     animation: pulse 0.8s ease-in-out infinite;"></div>
                <div style="width: 10px; height: 10px; border-radius: 50%; background: #818cf8;
                     animation: pulse 0.8s ease-in-out 0.2s infinite;"></div>
                <div style="width: 10px; height: 10px; border-radius: 50%; background: #f472b6;
                     animation: pulse 0.8s ease-in-out 0.4s infinite;"></div>
            </div>
            <div style="width: 280px; height: 4px; background: rgba(255,255,255,0.05); border-radius: 99px; overflow: hidden;">
                <div style="
                    height: 100%; width: 60%; border-radius: 99px;
                    background: linear-gradient(90deg, #00d4ff, #818cf8);
                    animation: progress 1.5s ease-in-out infinite;
                "></div>
            </div>
        </div>
        <style>
            @keyframes bounce { from { transform: translateY(0); } to { transform: translateY(-12px); } }
            @keyframes pulse { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } }
            @keyframes progress { 0% { transform: translateX(-100%); } 100% { transform: translateX(500%); } }
        </style>
    </div>
    """
    return st.markdown(loading_html, unsafe_allow_html=True)


# ─── KPI CARD ─────────────────────────────────────────────
def kpi_card(icon, label, value, color="#00d4ff", sub=None):
    sub_html = f'<div style="font-size:10px;color:{color}99;margin-top:2px;">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(15,22,41,0.95),rgba(20,30,55,0.9));
         border:1px solid {color}40;border-radius:14px;padding:14px 16px;text-align:left;height:100%;">
        <div style="font-size:20px;margin-bottom:4px;">{icon}</div>
        <div style="font-size:26px;font-weight:900;color:{color};font-family:'Space Mono',monospace;line-height:1;">{value}</div>
        <div style="font-size:9px;color:#64748b;margin-top:5px;text-transform:uppercase;letter-spacing:1.2px;">{label}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


# ─── HEADER ───────────────────────────────────────────────
def render_header(m, fetched_at):
    today = date.today()
    days_left = SPRINT_DAYS - m["current_day"]
    pct = round((len(m["done_tickets"]) / m["total"]) * 100) if m["total"] else 0
    status_color = "#10b981" if m["sprint_status"] == "on-track" else "#fbbf24" if m["sprint_status"] == "slight-risk" else "#f87171"
    status_label = "On Track 🎯" if m["sprint_status"] == "on-track" else "Slight Risk ⚠️" if m["sprint_status"] == "slight-risk" else "Behind 🚨"

    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
        <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span class="live-dot"></span>
                <span style="font-size:10px;color:#10b981;text-transform:uppercase;letter-spacing:2px;font-weight:600;">
                    Live · Jira · Refreshes every 5 min
                </span>
            </div>
            <h1 style="font-size:26px;font-weight:900;margin:0;
                background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                Jules Sprint Dashboard
            </h1>
            <div style="font-size:12px;color:#334155;margin-top:4px;">
                {SPRINT_NAME} · Feb 24 – Apr 12, 2026 · Fetched {fetched_at}
            </div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <div style="background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.18);
                 border-radius:10px;padding:10px 16px;font-size:12px;color:#7dd3fc;text-align:center;">
                📅 Day <strong>{m["current_day"]}</strong> / {SPRINT_DAYS}<br>
                <span style="color:#475569;font-size:10px;">{days_left} days left</span>
            </div>
            <div style="background:{status_color}12;border:1px solid {status_color}35;
                 border-radius:10px;padding:10px 16px;font-size:12px;color:{status_color};text-align:center;">
                {status_label}<br>
                <span style="color:#475569;font-size:10px;">{pct}% done</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── OVERVIEW TAB ─────────────────────────────────────────
def render_overview(m):
    total = m["total"]
    done_ct = len(m["done_tickets"])
    blocked_ct = len(m["blocked_tickets"])

    # KPI row
    cols = st.columns(7)
    with cols[0]: kpi_card("🎯", "Total Tickets", total, "#00d4ff")
    with cols[1]: kpi_card("✅", "Done", done_ct, "#10b981", "Jules definition")
    with cols[2]: kpi_card("⏳", "Remaining", total - done_ct, "#818cf8")
    with cols[3]: kpi_card("🚫", "Blocked", blocked_ct, "#f87171")
    with cols[4]: kpi_card("💎", "Total SP", m["total_sp"], "#fb923c")
    with cols[5]: kpi_card("✨", "SP Done", m["done_sp"], "#34d399", f"{round((m['done_sp']/m['total_sp'])*100) if m['total_sp'] else 0}%")
    with cols[6]:
        pct = round((done_ct / total) * 100) if total else 0
        kpi_card("📊", "Sprint Done", f"{pct}%", "#00d4ff")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown("**🍩 Status Distribution**")
        status_data = [(s, m["status_counts"].get(s, 0)) for s in STATUS_ORDER if m["status_counts"].get(s, 0) > 0]
        fig = go.Figure(go.Pie(
            labels=[s[0] for s in status_data],
            values=[s[1] for s in status_data],
            hole=0.55,
            marker=dict(colors=[STATUS_COLORS.get(s[0], "#475569") for s in status_data]),
            textinfo="label+value",
            textfont=dict(size=10, color="#e2e8f0"),
            hovertemplate="<b>%{label}</b><br>%{value} tickets<extra></extra>",
        ))
        fig.update_layout(
            showlegend=False, height=280, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", color="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown("**📋 Group Summary**")
        groups = [
            ("✅ Done (Jules def.)",     done_ct,     "#10b981"),
            ("👀 In Review",              (m["status_counts"].get("PO review",0) + m["status_counts"].get("Tech review",0)), "#818cf8"),
            ("🧪 QA / Test run",          m["status_counts"].get("PO/QA Test run",0),  "#6ee7b7"),
            ("⚡ Active",                 (m["status_counts"].get("In Progress",0) + m["status_counts"].get("AIM OF THE DAY",0)), "#38bdf8"),
            ("📅 Aim of Week",            m["status_counts"].get("Aim Of The week",0), "#bae6fd"),
            ("📋 To Do",                  m["status_counts"].get("To Do",0),            "#64748b"),
            ("🚫 Blocked",               blocked_ct,   "#f87171"),
        ]
        for label, val, color in groups:
            pct = (val / total * 100) if total else 0
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:3px;">
                    <span>{label}</span>
                    <span style="color:{color};font-family:'Space Mono',monospace;font-weight:700;">{val}<span style="color:#334155">/{total}</span></span>
                </div>
                <div style="background:#1e2d47;border-radius:999px;height:5px;">
                    <div style="width:{pct}%;height:100%;border-radius:999px;background:{color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Team workload
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown("**👥 Team Workload**")
    dev_cols = st.columns(4)
    devs = [(n, d) for n, d in m["dev_map"].items() if n != "Unassigned"]
    devs.sort(key=lambda x: x[1]["total"], reverse=True)
    for i, (name, d) in enumerate(devs):
        color = DEV_COLORS.get(name, "#64748b")
        pct = round((d["done"] / d["total"]) * 100) if d["total"] else 0
        initials = "".join(p[0] for p in name.split()[:2])
        with dev_cols[i % 4]:
            st.markdown(f"""
            <div style="background:{color}08;border:1px solid {color}25;border-radius:12px;padding:14px;">
                {"<div style='font-size:9px;color:#f87171;font-weight:700;margin-bottom:5px;'>⚠️ "+str(d['blocked'])+" BLOCKED</div>" if d['blocked'] >= 2 else ""}
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,{color},{color}70);
                         display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#0a0e1a;">{initials}</div>
                    <div>
                        <div style="font-weight:700;font-size:12px;">{name.split()[0]} {name.split()[1][0]}.</div>
                        <div style="font-size:9px;color:#475569;">{d['total']} tickets · {d['totalSP']} SP</div>
                    </div>
                    <div style="margin-left:auto;font-size:18px;font-weight:900;color:{color};font-family:'Space Mono',monospace;">{pct}%</div>
                </div>
                <div style="background:#1e2d47;border-radius:999px;height:4px;margin-bottom:8px;">
                    <div style="width:{pct}%;height:100%;border-radius:999px;background:{color};"></div>
                </div>
                <div style="display:flex;gap:4px;flex-wrap:wrap;">
                    <span style="background:#10b98110;border:1px solid #10b98122;border-radius:4px;padding:2px 6px;font-size:8px;color:#10b981;font-weight:700;">✅ {d['done']}</span>
                    <span style="background:#38bdf810;border:1px solid #38bdf822;border-radius:4px;padding:2px 6px;font-size:8px;color:#38bdf8;font-weight:700;">⚡ {d['active']}</span>
                    <span style="background:#f8717110;border:1px solid #f8717122;border-radius:4px;padding:2px 6px;font-size:8px;color:#f87171;font-weight:700;">🚫 {d['blocked']}</span>
                    <span style="background:#64748b10;border:1px solid #64748b22;border-radius:4px;padding:2px 6px;font-size:8px;color:#64748b;font-weight:700;">📋 {d['todo']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ─── BURNDOWN TAB ─────────────────────────────────────────
def render_burndown(m):
    total = m["total"]
    current_day = m["current_day"]

    key_days = sorted(set([1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 48, current_day]))
    burndown_data = []
    for d in key_days:
        dt = SPRINT_START + pd.Timedelta(days=d-1)
        ideal = max(0, round(total - (total / SPRINT_DAYS) * (d - 1)))
        actual = None
        if d <= current_day:
            actual = total if d == 1 else (total - len(m["done_tickets"]) if d == current_day else None)
        label = f"Today ★ {dt.strftime('%d %b')}" if d == current_day else dt.strftime('%d %b')
        burndown_data.append({"day": d, "label": label, "ideal": ideal, "actual": actual})

    df = pd.DataFrame(burndown_data)

    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown(f"**🔥 Sprint Burndown** — Feb 24 to Apr 12, 2026 · Day {current_day}/{SPRINT_DAYS}")

    # Mini KPIs
    gap = m["gap"]
    gap_color = "#10b981" if gap <= 0 else "#fbbf24" if gap <= 5 else "#f87171"
    gap_label = "On Track 🎯" if gap <= 0 else f"+{gap} Behind" if gap > 0 else f"{abs(gap)} Ahead"
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, (label, val, color) in zip([c1,c2,c3,c4,c5], [
        ("Sprint Day", f"{current_day}/{SPRINT_DAYS}", "#00d4ff"),
        ("Days Left", SPRINT_DAYS - current_day, "#818cf8"),
        ("Ideal Remaining", m["ideal_today"], "#f87171"),
        ("Actual Remaining", m["actual_today"], "#00d4ff"),
        ("Gap", gap_label, gap_color),
    ]):
        col.markdown(f"""
        <div style="background:rgba(15,22,41,0.8);border:1px solid {color}25;border-radius:10px;padding:10px;text-align:center;">
            <div style="font-size:16px;font-weight:900;color:{color};font-family:'Space Mono',monospace;">{val}</div>
            <div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:1px;margin-top:3px;">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["label"], y=df["ideal"],
        name="Ideal Remaining", mode="lines+markers",
        line=dict(color="#f87171", width=2, dash="dash"),
        marker=dict(color="#f87171", size=6),
        fill="tozeroy", fillcolor="rgba(248,113,113,0.05)",
        hovertemplate="<b>%{x}</b><br>Ideal: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["label"], y=df["actual"],
        name="Actual Remaining", mode="lines+markers",
        line=dict(color="#00d4ff", width=3),
        marker=dict(color="#00d4ff", size=8),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
        connectgaps=True,
        hovertemplate="<b>%{x}</b><br>Actual: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#64748b"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8")),
        xaxis=dict(gridcolor="#1e2d47", tickfont=dict(size=10), tickangle=-20),
        yaxis=dict(gridcolor="#1e2d47", tickfont=dict(size=10), range=[0, total + 3]),
        margin=dict(l=0, r=0, t=10, b=40),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Progress bar
    elapsed_pct = round(((current_day - 1) / (SPRINT_DAYS - 1)) * 100)
    st.progress(elapsed_pct / 100, text=f"Sprint {elapsed_pct}% elapsed · {SPRINT_DAYS - current_day} days remaining")
    st.markdown('</div>', unsafe_allow_html=True)


# ─── VELOCITY TAB ─────────────────────────────────────────
def render_velocity(m):
    devs = [(n, d) for n, d in m["dev_map"].items() if n != "Unassigned"]
    devs.sort(key=lambda x: x[1]["total"], reverse=True)

    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown("**⚡ Developer Velocity**")

    names = [n.split()[0] for n, _ in devs]
    fig = go.Figure()
    for label, key, color in [("✅ Done","done","#10b981"),("⚡ Active","active","#38bdf8"),("🚫 Blocked","blocked","#f87171"),("📋 Todo","todo","#334155")]:
        fig.add_trace(go.Bar(
            name=label, x=names, y=[d[key] for _, d in devs],
            marker_color=color, hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y}}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#64748b"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"), orientation="h", y=-0.15),
        xaxis=dict(gridcolor="#1e2d47"), yaxis=dict(gridcolor="#1e2d47"),
        margin=dict(l=0, r=0, t=10, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    dev_cols = st.columns(len(devs))
    for i, (name, d) in enumerate(devs):
        color = DEV_COLORS.get(name, "#64748b")
        pct = round((d["done"] / d["total"]) * 100) if d["total"] else 0
        initials = "".join(p[0] for p in name.split()[:2])
        with dev_cols[i]:
            st.markdown(f"""
            <div style="background:rgba(15,22,41,0.9);border:1px solid {color}28;border-radius:14px;padding:14px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,{color},{color}70);
                         display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#0a0e1a;">{initials}</div>
                    <div style="flex:1;">
                        <div style="font-weight:700;font-size:12px;">{name}</div>
                        <div style="font-size:9px;color:#475569;">{d['total']} tickets · {d['totalSP']} SP</div>
                    </div>
                    <div style="font-size:18px;font-weight:900;color:{color};font-family:'Space Mono',monospace;">{pct}%</div>
                </div>
                <div style="background:#1e2d47;border-radius:999px;height:5px;margin-bottom:8px;overflow:hidden;display:flex;">
                    <div style="width:{round(d['done']/d['total']*100) if d['total'] else 0}%;background:#10b981;"></div>
                    <div style="width:{round(d['active']/d['total']*100) if d['total'] else 0}%;background:#38bdf8;"></div>
                    <div style="width:{round(d['blocked']/d['total']*100) if d['total'] else 0}%;background:#f87171;"></div>
                </div>
                <div style="display:flex;gap:4px;flex-wrap:wrap;">
                    <span style="background:#10b98110;border-radius:4px;padding:2px 6px;font-size:8px;color:#10b981;font-weight:700;">✅ {d['done']}</span>
                    <span style="background:#818cf810;border-radius:4px;padding:2px 6px;font-size:8px;color:#818cf8;font-weight:700;">⚡ {d['active']}</span>
                    <span style="background:#f8717110;border-radius:4px;padding:2px 6px;font-size:8px;color:#f87171;font-weight:700;">🚫 {d['blocked']}</span>
                    <span style="background:#fb923c10;border-radius:4px;padding:2px 6px;font-size:8px;color:#fb923c;font-weight:700;">💎 {d['doneSP']}/{d['totalSP']}</span>
                </div>
            </div>""", unsafe_allow_html=True)


# ─── POINTS TAB ───────────────────────────────────────────
def render_points(m):
    cols = st.columns(5)
    with cols[0]: kpi_card("💎", "Total Sprint SP", m["total_sp"], "#00d4ff")
    with cols[1]: kpi_card("✅", "SP Completed", m["done_sp"], "#10b981", f"{round((m['done_sp']/m['total_sp'])*100) if m['total_sp'] else 0}% done")
    with cols[2]: kpi_card("⏳", "SP Remaining", m["total_sp"] - m["done_sp"], "#818cf8")
    with cols[3]: kpi_card("🚫", "SP Blocked", m["blocked_sp"], "#f87171")
    with cols[4]: kpi_card("⚠️", "No SP Set", m["missing_sp"], "#fbbf24", "needs estimating")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown("**📊 Story Points per Developer**")

    devs = [(n, d) for n, d in m["dev_map"].items() if n != "Unassigned"]
    devs.sort(key=lambda x: x[1]["total"], reverse=True)
    names = [n.split()[0] for n, _ in devs]
    fig = go.Figure()
    for label, key, color in [("✅ Done SP","doneSP","#10b981"),("🚫 Blocked SP","blockedSP","#f87171"),("📋 Rest SP",None,"#334155")]:
        vals = []
        for _, d in devs:
            if key:
                vals.append(d.get(key, 0))
            else:
                vals.append(max(0, d["totalSP"] - d.get("doneSP",0) - d.get("blockedSP",0)))
        fig.add_trace(go.Bar(name=label, x=names, y=vals, marker_color=color,
                             hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y}}<extra></extra>"))
    fig.update_layout(
        barmode="stack", height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#64748b"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"), orientation="h", y=-0.2),
        xaxis=dict(gridcolor="#1e2d47"), yaxis=dict(gridcolor="#1e2d47"),
        margin=dict(l=0, r=0, t=10, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ─── ALL TICKETS TAB ──────────────────────────────────────
def render_tickets(m):
    tickets = m["tickets"]
    total = len(tickets)

    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
        <div>
            <span style="font-size:16px;font-weight:700;">🎫 All Sprint Tickets ({total})</span>
            <span style="font-size:11px;color:#475569;margin-left:10px;">Full titles · AAWU/AAD stripped · Click to open in Jira</span>
        </div>
        <span style="font-size:9px;color:#34d399;background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);padding:4px 10px;border-radius:6px;">
            🔗 Clickable tickets
        </span>
    </div>
    """, unsafe_allow_html=True)

    for status in STATUS_ORDER:
        group = [t for t in tickets if t["status"] == status]
        if not group:
            continue
        sc = STATUS_COLORS.get(status, "#64748b")
        rows_html = ""
        for t in group:
            color = DEV_COLORS.get(t["assignee"], "#64748b")
            initials = "".join(p[0] for p in t["assignee"].split()[:2])
            sp_badge = f'<span style="font-size:9px;color:#fb923c;font-weight:800;font-family:Space Mono,monospace;background:rgba(251,146,60,0.1);padding:2px 5px;border-radius:3px;">{int(t["sp"])}sp</span>' if t["sp"] else ""
            row_cls = "ticket-row blocked" if status == "Blocked" else "ticket-row"
            rows_html += f"""
            <div class="{row_cls}">
                <span class="ticket-key" style="min-width:70px;flex-shrink:0;">
                    <a href="{JIRA_BASE}/browse/{t['key']}" target="_blank">{t['key']}</a>
                </span>
                <span style="font-size:9px;color:#7dd3fc;background:rgba(129,140,248,0.1);border-radius:3px;
                     padding:2px 5px;min-width:44px;text-align:center;flex-shrink:0;">{t['type'][:7] if t['type'] else ''}</span>
                <span class="ticket-summary" style="flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">
                    <a href="{JIRA_BASE}/browse/{t['key']}" target="_blank">{t['summary']}</a>
                </span>
                <span style="font-size:9px;color:{color};font-weight:700;background:{color}12;
                     padding:2px 7px;border-radius:3px;white-space:nowrap;flex-shrink:0;">{initials} {t['assignee'].split()[0]}</span>
                {sp_badge}
            </div>"""

        st.markdown(f"""
        <div style="margin-bottom:14px;">
            <div style="font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
                 margin-bottom:5px;color:{sc};display:flex;align-items:center;gap:5px;">
                <div style="width:5px;height:5px;border-radius:2px;background:{sc};"></div>
                {status} <span style="color:#334155;">({len(group)})</span>
            </div>
            {rows_html}
        </div>
        """, unsafe_allow_html=True)


# ─── MAIN APP ─────────────────────────────────────────────
def main():
    if not check_pin():
        return

    # Sidebar controls
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.markdown("**Slack Notifications**")
        auto_slack = st.toggle("Auto-post on load", value=False)
        st.markdown("---")
        st.markdown(f"**Sprint:** {SPRINT_NAME}")
        st.markdown(f"**Project:** {PROJECT}")
        st.markdown(f"**Jira:** [minehub.atlassian.net]({JIRA_BASE})")

    # Fetch data with animated loading
    with st.spinner(""):
        loading_placeholder = st.empty()
        loading_placeholder.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:52px;margin-bottom:16px;">🚀</div>
            <h2 style="background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                font-size:24px;font-weight:900;margin-bottom:8px;">Fetching Sprint Data</h2>
            <p style="color:#475569;font-size:13px;margin-bottom:28px;">Connecting to Jira...</p>
            <div style="display:flex;gap:10px;justify-content:center;">
                <div style="width:10px;height:10px;border-radius:50%;background:#00d4ff;animation:pulse 0.8s ease-in-out infinite;"></div>
                <div style="width:10px;height:10px;border-radius:50%;background:#818cf8;animation:pulse 0.8s ease-in-out 0.2s infinite;"></div>
                <div style="width:10px;height:10px;border-radius:50%;background:#f472b6;animation:pulse 0.8s ease-in-out 0.4s infinite;"></div>
            </div>
            <style>@keyframes pulse{0%,100%{opacity:.3;transform:scale(.8)}50%{opacity:1;transform:scale(1.2)}}</style>
        </div>
        """, unsafe_allow_html=True)

        try:
            tickets = fetch_jira_tickets()
            fetched_at = datetime.now().strftime("%d %b %Y, %H:%M")
        except Exception as e:
            loading_placeholder.empty()
            st.error(f"❌ Failed to fetch Jira data: {e}")
            st.info("Check your JIRA_EMAIL and JIRA_API_TOKEN in the .env file or Streamlit secrets.")
            return

        loading_placeholder.empty()

    m = build_metrics(tickets)

    # Auto-post to Slack if enabled
    if auto_slack and SLACK_WEBHOOK and m["blocked_tickets"]:
        ok, _ = post_to_slack(m["blocked_tickets"], m)
        if ok:
            st.toast("✅ Posted to Slack!", icon="📣")

    # Header
    render_header(m, fetched_at)

    # Slack post button (top right area)
    if SLACK_WEBHOOK:
        col1, col2, col3 = st.columns([6, 1, 1])
        with col2:
            if st.button("📣 Post to Slack"):
                ok, msg = post_to_slack(m["blocked_tickets"], m)
                if ok:
                    st.toast("✅ Posted to Slack!", icon="📣")
                else:
                    st.toast(f"❌ Slack error: {msg}", icon="⚠️")
        with col3:
            if st.button("🔄 Refresh"):
                st.cache_data.clear()
                st.rerun()
    else:
        col1, col2 = st.columns([7, 1])
        with col2:
            if st.button("🔄 Refresh"):
                st.cache_data.clear()
                st.rerun()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "🔥 Burndown", "⚡ Velocity", "💎 Story Points", "🎫 All Tickets"
    ])
    with tab1: render_overview(m)
    with tab2: render_burndown(m)
    with tab3: render_velocity(m)
    with tab4: render_points(m)
    with tab5: render_tickets(m)

    st.markdown(f"""
    <div style="text-align:center;font-size:9px;color:#1e2d47;border-top:1px solid #0d1528;padding-top:12px;margin-top:20px;">
        Jules Product · MineHub · {SPRINT_NAME} · {m['total']} tickets · {m['total_sp']} SP · {fetched_at}
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
