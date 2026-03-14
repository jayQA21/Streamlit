import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import re
import os
from datetime import datetime, date
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
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; background-color: #080c1a !important; color: #e2e8f0 !important; }
.stApp { background: radial-gradient(ellipse at 20% 10%, #0d1b3e 0%, #080c1a 55%, #050710 100%) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }
[data-baseweb="tab-list"] { background: rgba(15,22,41,0.8) !important; border-radius: 12px !important; padding: 4px !important; }
[data-baseweb="tab"] { background: transparent !important; color: #475569 !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 0.75rem !important; }
[aria-selected="true"] { background: rgba(0,212,255,0.1) !important; color: #00d4ff !important; border-bottom: 2px solid #00d4ff !important; }
.stButton > button { background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(129,140,248,0.1)) !important; border: 1px solid rgba(0,212,255,0.3) !important; color: #00d4ff !important; border-radius: 10px !important; font-weight: 700 !important; }
.stProgress > div > div { background: linear-gradient(90deg, #00d4ff, #818cf8) !important; border-radius: 99px !important; }
div[data-testid="stMetric"] { background: linear-gradient(135deg, rgba(15,22,41,0.95), rgba(20,30,55,0.9)); border: 1px solid rgba(0,212,255,0.2); border-radius: 14px; padding: 12px 14px; }
div[data-testid="stMetricValue"] { color: #00d4ff !important; font-family: 'Space Mono', monospace !important; }
div[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.7rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.live-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite; margin-right: 6px; }
.ticket-key a { color: #00d4ff !important; font-family: 'Space Mono', monospace !important; font-size: 11px !important; text-decoration: none !important; border-bottom: 1px dotted rgba(0,212,255,0.4); }
.ticket-summary a { color: #94a3b8 !important; text-decoration: none !important; }
.ticket-summary a:hover { color: #c4b5fd !important; }
</style>
""", unsafe_allow_html=True)


# ─── PIN PROTECTION ───────────────────────────────────────
def check_pin():
    if not DASHBOARD_PIN:
        return True
    if st.session_state.get("authenticated"):
        return True
    st.markdown("<div style='max-width:340px;margin:80px auto;text-align:center;'><div style='font-size:48px;margin-bottom:16px;'>🔐</div><h2 style='color:#00d4ff;'>Jules Dashboard</h2><p style='color:#475569;font-size:13px;margin-bottom:24px;'>Enter PIN to access</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pin = st.text_input("PIN", type="password", placeholder="Enter PIN...", label_visibility="collapsed")
        if st.button("→ Enter", use_container_width=True):
            if pin == DASHBOARD_PIN:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect PIN")
    return False


# ─── JIRA FETCH ───────────────────────────────────────────
def clean_title(s):
    s = re.sub(r'^(AAWU,?\s*|AAD,?\s*)', '', s, flags=re.IGNORECASE)
    return s.lstrip(',').strip()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_jira_tickets():
    url = f"{JIRA_BASE}/rest/api/3/search/jql"
    auth = (JIRA_EMAIL, JIRA_TOKEN)
    headers = {"Accept": "application/json"}
    tickets = []
    next_page_token = None

    while True:
        params = {
            "jql": f"project = {PROJECT} AND sprint in openSprints() ORDER BY created DESC",
            "maxResults": 100,
            "fields": "summary,status,assignee,customfield_10024,issuetype",
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        resp = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for issue in data.get("issues", []):
            f = issue.get("fields", {})
            raw_sp = f.get("customfield_10024")
            tickets.append({
                "key":      issue["key"],
                "summary":  clean_title(f.get("summary", "")),
                "status":   f.get("status", {}).get("name", "Unknown"),
                "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
                "sp":       int(raw_sp) if raw_sp is not None else None,
                "type":     f.get("issuetype", {}).get("name", ""),
            })

        if data.get("isLast", True):
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return tickets


# ─── METRICS ──────────────────────────────────────────────
def build_metrics(tickets):
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
    current_day = max(1, min((today - SPRINT_START).days + 1, SPRINT_DAYS))
    ideal = max(0, round(total - (total / SPRINT_DAYS) * (current_day - 1)))
    actual = total - len(done)
    gap = actual - ideal
    return dict(total=total, done=done, blocked=blocked, sc=sc, dev_map=dev_map,
                total_sp=total_sp, done_sp=done_sp, blocked_sp=blocked_sp,
                missing_sp=sum(1 for t in tickets if not t["sp"]),
                current_day=current_day, ideal=ideal, actual=actual, gap=gap,
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
def render_overview(m):
    total = m["total"]; done_ct = len(m["done"]); blocked_ct = len(m["blocked"])

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

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🍩 Status Distribution**")
        status_data = [(s, m["sc"].get(s,0)) for s in STATUS_ORDER if m["sc"].get(s,0)>0]
        fig = go.Figure(go.Pie(
            labels=[s[0] for s in status_data], values=[s[1] for s in status_data], hole=0.55,
            marker=dict(colors=[STATUS_COLORS.get(s[0],"#475569") for s in status_data]),
            textinfo="label+value", textfont=dict(size=10),
            hovertemplate="<b>%{label}</b><br>%{value} tickets<extra></extra>"))
        fig.update_layout(showlegend=False, height=260, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans", color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📋 Group Summary**")
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
<div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:3px;">
<span>{label}</span><span style="color:{color};font-weight:700;">{val}/{total}</span>
</div>
<div style="background:#1e2d47;border-radius:999px;height:5px;">
<div style="width:{pct_bar:.1f}%;height:100%;border-radius:999px;background:{color};"></div>
</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Team Workload — using native st.columns + st.markdown per card ──
    st.markdown("**👥 Team Workload**")
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
    total = m["total"]; cd = m["current_day"]
    key_days = sorted(set([1,5,10,15,20,25,30,35,40,45,48,cd]))
    rows = []
    for d in key_days:
        dt = SPRINT_START + pd.Timedelta(days=d-1)
        ideal = max(0, round(total-(total/SPRINT_DAYS)*(d-1)))
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
    st.markdown("**⚡ Developer Velocity**")
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
    st.markdown("**📊 Story Points per Developer**")
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
def render_tickets(m):
    tickets = m["tickets"]
    st.markdown(f"**🎫 All Sprint Tickets ({len(tickets)})** · Full titles · AAWU/AAD stripped · Click to open in Jira")
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
            border = "rgba(248,113,113,0.15)" if status=="Blocked" else "rgba(255,255,255,0.05)"
            rows += f'<div style="display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:7px;margin-bottom:3px;background:{bg};border:1px solid {border};">'
            rows += f'<span class="ticket-key" style="min-width:70px;flex-shrink:0;"><a href="{JIRA_BASE}/browse/{t["key"]}" target="_blank">{t["key"]}</a></span>'
            rows += f'<span style="font-size:9px;color:#7dd3fc;background:rgba(129,140,248,0.1);border-radius:3px;padding:2px 5px;min-width:44px;text-align:center;flex-shrink:0;">{t["type"][:7]}</span>'
            rows += f'<span class="ticket-summary" style="flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;"><a href="{JIRA_BASE}/browse/{t["key"]}" target="_blank">{t["summary"]}</a></span>'
            rows += f'<span style="font-size:9px;color:{color};font-weight:700;background:{color}20;padding:2px 7px;border-radius:3px;white-space:nowrap;flex-shrink:0;">{initials} {fname}</span>'
            rows += sp_badge + "</div>"
        st.markdown(f'<div style="margin-bottom:14px;"><div style="font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:5px;color:{sc};">{status} ({len(group)})</div>{rows}</div>', unsafe_allow_html=True)


# ─── MAIN ─────────────────────────────────────────────────
def main():
    if not check_pin():
        return

    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown("---")
        auto_slack = st.toggle("Auto-post blocked to Slack", value=False)
        st.markdown("---")
        st.markdown(f"**Sprint:** {SPRINT_NAME}")
        st.markdown(f"**Project:** {PROJECT}")
        st.markdown(f"**Jira:** [minehub.atlassian.net]({JIRA_BASE})")

    # Loading screen
    placeholder = st.empty()
    placeholder.markdown("""<div style="text-align:center;padding:60px 20px;">
<div style="font-size:52px;margin-bottom:16px;">🚀</div>
<h2 style="background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:24px;font-weight:900;">Fetching Sprint Data</h2>
<p style="color:#475569;font-size:13px;margin-top:8px;">Connecting to Jira...</p>
<style>@keyframes pulse{0%,100%{opacity:.3;transform:scale(.8)}50%{opacity:1;transform:scale(1.2)}}</style>
<div style="display:flex;gap:10px;justify-content:center;margin-top:24px;">
<div style="width:10px;height:10px;border-radius:50%;background:#00d4ff;animation:pulse 0.8s ease-in-out infinite;"></div>
<div style="width:10px;height:10px;border-radius:50%;background:#818cf8;animation:pulse 0.8s ease-in-out 0.2s infinite;"></div>
<div style="width:10px;height:10px;border-radius:50%;background:#f472b6;animation:pulse 0.8s ease-in-out 0.4s infinite;"></div>
</div></div>""", unsafe_allow_html=True)

    try:
        tickets = fetch_jira_tickets()
        fetched_at = datetime.now().strftime("%d %b %Y, %H:%M")
    except Exception as e:
        placeholder.empty()
        st.error(f"❌ Failed to fetch Jira data: {e}")
        st.info("Check JIRA_EMAIL and JIRA_API_TOKEN in Streamlit secrets.")
        return
    placeholder.empty()

    m = build_metrics(tickets)

    if auto_slack and SLACK_WEBHOOK and m["blocked"]:
        ok, _ = post_to_slack(m["blocked"], m)
        if ok: st.toast("✅ Posted to Slack!", icon="📣")

    # Header
    days_left = SPRINT_DAYS - m["current_day"]
    pct = round(len(m["done"])/m["total"]*100) if m["total"] else 0
    sc = "#10b981" if m["status"]=="on-track" else "#fbbf24" if m["status"]=="slight-risk" else "#f87171"
    sl = "On Track 🎯" if m["status"]=="on-track" else "Slight Risk ⚠️" if m["status"]=="slight-risk" else "Behind 🚨"
    st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
<div><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span class="live-dot"></span><span style="font-size:10px;color:#10b981;text-transform:uppercase;letter-spacing:2px;font-weight:600;">Live · Jira · 5 min cache</span></div>
<h1 style="font-size:26px;font-weight:900;margin:0;background:linear-gradient(90deg,#00d4ff,#818cf8,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Jules Sprint Dashboard</h1>
<div style="font-size:12px;color:#475569;margin-top:4px;">{SPRINT_NAME} · Feb 24 – Apr 12, 2026 · {fetched_at}</div></div>
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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview","🔥 Burndown","⚡ Velocity","💎 Story Points","🎫 All Tickets"])
    with tab1: render_overview(m)
    with tab2: render_burndown(m)
    with tab3: render_velocity(m)
    with tab4: render_points(m)
    with tab5: render_tickets(m)

    st.markdown(f"<div style='text-align:center;font-size:9px;color:#1e2d47;border-top:1px solid #0d1528;padding-top:12px;margin-top:20px;'>Jules Product · MineHub · {SPRINT_NAME} · {m['total']} tickets · {m['total_sp']} SP · {fetched_at}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
