"""
Jules Sprint Daily Notifier — scheduler.py
Fires at 9:00 AM IST every weekday via GitHub Actions
"""

import os, re, requests, threading
from datetime import date, datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

JIRA_EMAIL    = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN    = os.getenv("JIRA_API_TOKEN", "").replace("\n","").replace("\r","").replace(" ","").strip()
JIRA_BASE     = os.getenv("JIRA_BASE_URL", "https://minehub.atlassian.net")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://julesdashboard.streamlit.app")

IST          = ZoneInfo("Asia/Kolkata")
PROJECT      = "JENG"
SPRINT_NAME  = "Release Sprint 3"
SPRINT_START = date(2026, 2, 24)
SPRINT_END   = date(2026, 4, 12)
SPRINT_DAYS  = 48

DONE_STATUSES    = {"Done","PO/QA VALID","In demo","In production","CS reviewed","Demo","In Production","CS Reviewed"}
BLOCKED_STATUSES = {"Blocked"}
ACTIVE_STATUSES  = {"In Progress","AIM OF THE DAY","Tech review","PO review","PO/QA Test run","Aim Of The week","PO not valid","Tech strategy"}

# Consistent color theme per developer
DEV_CONFIG = {
    "Nikita Vaidya": {"dot": "🟪", "bar": "🟪", "initial": "NV"},  # purple
    "Satadru Roy":   {"dot": "🟥", "bar": "🟥", "initial": "SR"},  # red
    "Rizky Ario":    {"dot": "🟨", "bar": "🟨", "initial": "RA"},  # yellow
    "Jay Pitroda":   {"dot": "🟦", "bar": "🟦", "initial": "JP"},  # blue
}

DAILY_TIPS = [
    "Blocked >2 days? Speak up — silence won't unblock it. 🔊",
    "A ticket in review is NOT done. Push it over the line! 🏁",
    "Small PRs merge faster. Big PRs sit forever. 🐢",
    "Update your ticket status before standup — not during! ⚡",
    "Done = merged + deployed + verified. All three. 🚀",
    "The best code is the code you don't write. ✂️",
    "Sprint health = team health. Look out for each other. 🤝",
    "Every blocker resolved = smoother sprint review. 📊",
    "Write the test first, thank yourself later. 🧪",
    "If it's unclear, clarify it now — not on the last day. 💬",
]

GREETINGS = [
    "Let's make today count! 💪",
    "Another day, another ticket shipped! 🚀",
    "Stay focused, stay unblocked! 🎯",
    "Great work so far — keep the momentum! ⚡",
    "Sprint strong, team Jules! 🏃",
]


def clean_title(s):
    s = re.sub(r'^(AAWU,?\s*|AAD,?\s*)', '', s, flags=re.IGNORECASE)
    return s.lstrip(',').strip()[:58]


def fetch_sprint_data():
    url    = f"{JIRA_BASE}/rest/api/3/search/jql"
    auth   = (JIRA_EMAIL, JIRA_TOKEN)
    params = {
        "jql":        f"project = {PROJECT} AND sprint in openSprints() ORDER BY created DESC",
        "maxResults": 200,
        "fields":     "summary,status,assignee,customfield_10024,issuetype",
    }
    resp = requests.get(url, headers={"Accept": "application/json"}, auth=auth, params=params, timeout=20)
    resp.raise_for_status()
    tickets = []
    for issue in resp.json().get("issues", []):
        f = issue.get("fields", {})
        tickets.append({
            "key":      issue["key"],
            "summary":  clean_title(f.get("summary", "")),
            "status":   f.get("status", {}).get("name", "Unknown"),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "sp":       int(f["customfield_10024"]) if f.get("customfield_10024") else None,
        })
    return tickets


def build_metrics(tickets):
    today     = datetime.now(IST).date()
    total     = len(tickets)
    done      = [t for t in tickets if t["status"] in DONE_STATUSES]
    blocked   = [t for t in tickets if t["status"] in BLOCKED_STATUSES]
    total_sp  = sum(t["sp"] or 0 for t in tickets)
    done_sp   = sum(t["sp"] or 0 for t in done)
    cur_day   = max(1, min((today - SPRINT_START).days + 1, SPRINT_DAYS))
    days_left = SPRINT_DAYS - cur_day
    pct_done  = round(len(done) / total * 100) if total else 0
    pct_time  = round((cur_day - 1) / (SPRINT_DAYS - 1) * 100)
    gap       = pct_done - pct_time
    health    = "on-track" if gap >= -5 else "at-risk" if gap >= -15 else "behind"
    velocity  = round((total - len(done)) / days_left) if days_left > 0 else 0
    return dict(
        total=total, done=done, blocked=blocked,
        total_sp=total_sp, done_sp=done_sp,
        cur_day=cur_day, days_left=days_left,
        pct_done=pct_done, pct_time=pct_time,
        gap=gap, health=health, velocity=velocity,
    )


def make_bar(pct, width=12, color="🟩"):  # default green
    """Colored emoji progress bar"""
    filled = round(pct / 100 * width)
    return color * filled + "⬜" * (width - filled)


def get_tip():
    return DAILY_TIPS[date.today().timetuple().tm_yday % len(DAILY_TIPS)]


def get_greeting():
    return GREETINGS[date.today().timetuple().tm_yday % len(GREETINGS)]


def build_slack_message(m, tickets):
    today    = datetime.now(IST).date()
    weekday  = today.strftime("%A")
    date_str = today.strftime("%d %b %Y")

    # ── Health config — clean and consistent ──
    health_map = {
        "on-track": {"icon": "🟢", "label": "On Track",        "note": "Sprint is progressing well"},
        "at-risk":  {"icon": "🟠", "label": "Slightly At Risk", "note": "Pick up the pace"},
        "behind":   {"icon": "🔴", "label": "Behind Schedule",  "note": "Needs immediate attention"},
    }
    hc = health_map[m["health"]]

    # ── Progress bars ──
    done_bar = make_bar(m["pct_done"], color="🟩")   # green  = work done
    time_bar = make_bar(m["pct_time"], color="🟧")   # orange = time elapsed

    # ── Per-dev stats — clean format ──
    dev_rows = []
    for name, cfg in DEV_CONFIG.items():
        dev_tix  = [t for t in tickets if t["assignee"] == name]
        if not dev_tix:
            continue
        d_done    = sum(1 for t in dev_tix if t["status"] in DONE_STATUSES)
        d_blocked = sum(1 for t in dev_tix if t["status"] in BLOCKED_STATUSES)
        d_sp_done = sum(t["sp"] or 0 for t in dev_tix if t["status"] in DONE_STATUSES)
        d_sp_tot  = sum(t["sp"] or 0 for t in dev_tix)
        pct       = round(d_done / len(dev_tix) * 100) if dev_tix else 0
        bar       = make_bar(pct, width=10, color=cfg["bar"])
        fname     = name.split()[0]

        # Consistent status indicator — always show exact count
        if d_blocked >= 2:
            status_tag = f"  ⛔ {d_blocked} Blocked"
        elif d_blocked == 1:
            status_tag = "  ⚠️ 1 Blocked"
        else:
            status_tag = "  ✅ Clear"

        sp_info = f"  ·  {d_sp_done}/{d_sp_tot} SP" if d_sp_tot else ""
        dev_rows.append(
            f"{cfg['dot']}  *{fname}*   `{bar}`   *{pct}%*   {d_done}/{len(dev_tix)} tickets{sp_info}{status_tag}"
        )

    # ── Blocked tickets — clean consistent format ──
    blocker_rows = []
    for t in m["blocked"][:5]:
        cfg   = DEV_CONFIG.get(t["assignee"], {"dot": "⚪", "initial": "?"})
        fname = t["assignee"].split()[0] if t["assignee"] != "Unassigned" else "Unassigned"
        blocker_rows.append(
            f"{cfg['dot']}  `{t['key']}`  →  {t['summary']}  —  *{fname}*"
        )
    if len(m["blocked"]) > 5:
        blocker_rows.append(f"_...and {len(m['blocked']) - 5} more blocked tickets_")

    no_blockers = not blocker_rows

    tip      = get_tip()
    greeting = get_greeting()

    # ════════════════════════════════════════════
    # SLACK BLOCK KIT MESSAGE
    # ════════════════════════════════════════════
    blocks = [

        # ── 1. HERO HEADER ──────────────────────
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚀  Jules Daily Standup  —  {weekday}, {date_str}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"*{SPRINT_NAME}*   ·   Day *{m['cur_day']}* of *{SPRINT_DAYS}*   ·   {greeting}"
            }]
        },
        {"type": "divider"},

        # ── 2. BURNDOWN SECTION ─────────────────
        {
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "text",
                    "text": "📉  Sprint Burndown",
                    "style": {"bold": True}
                }]
            }]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"```\n"
                    f" Time elapsed   {time_bar}  {m['pct_time']}%\n"
                    f" Work done      {done_bar}  {m['pct_done']}%\n"
                    f"```\n"
                    f"{hc['icon']}  *{hc['label']}*  —  _{hc['note']}_\n"
                    f"Need *~{m['velocity']} tickets/day* to finish   ·   *{m['days_left']} days* left"
                )
            }
        },
        {"type": "divider"},

        # ── 3. SPRINT STATS ─────────────────────
        {
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "text",
                    "text": "📊  Sprint Snapshot",
                    "style": {"bold": True}
                }]
            }]
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"✅  *Done*\n*{len(m['done'])}* / {m['total']} tickets"},
                {"type": "mrkdwn", "text": f"💎  *Story Points*\n*{m['done_sp']}* / {m['total_sp']} SP"},
                {"type": "mrkdwn", "text": f"⛔  *Blocked*\n*{len(m['blocked'])}* tickets"},
                {"type": "mrkdwn", "text": f"📅  *Days Left*\n*{m['days_left']}* of {SPRINT_DAYS} days"},
            ]
        },
        {"type": "divider"},

        # ── 4. TEAM VELOCITY ────────────────────
        {
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "text",
                    "text": "👥  Team Velocity",
                    "style": {"bold": True}
                }]
            }]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(dev_rows)
            }
        },
        {"type": "divider"},

        # ── 5. BLOCKERS ─────────────────────────
        {
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "text",
                    "text": f"⛔  Active Blockers  ({len(m['blocked'])})",
                    "style": {"bold": True}
                }]
            }]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "✨  *No blockers today — great work everyone!*"
                    if no_blockers else
                    "\n".join(blocker_rows)
                )
            }
        },
        {"type": "divider"},

        # ── 6. TIP + BUTTONS ────────────────────
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"💡  *Tip of the Day*  —  {tip}"
            }]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊  Live Dashboard", "emoji": True},
                    "url":   DASHBOARD_URL,
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🗂  Jira Board", "emoji": True},
                    "url":  f"{JIRA_BASE}/jira/software/c/projects/{PROJECT}/boards"
                },
            ]
        },
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"_Jules Sprint Bot  ·  Auto-generated at 9:00 AM IST  ·  {SPRINT_NAME}_"
            }]
        },

    ]

    return {
        "username":   "Jules Sprint Bot",
        "icon_emoji": ":rocket:",
        "blocks":     blocks,
    }


def send_daily_notification():
    if not SLACK_WEBHOOK:
        print("[Scheduler] No SLACK_WEBHOOK_URL — skipping")
        return
    try:
        print(f"[Scheduler] Sending — {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
        tickets = fetch_sprint_data()
        m       = build_metrics(tickets)
        payload = build_slack_message(m, tickets)
        resp    = requests.post(SLACK_WEBHOOK, json=payload, timeout=15)
        if resp.status_code == 200:
            print("[Scheduler] ✅ Sent successfully!")
        else:
            print(f"[Scheduler] ❌ Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Scheduler] ❌ {e}")


def start_scheduler():
    import schedule, time
    schedule.every().monday.at("09:00").do(send_daily_notification)
    schedule.every().tuesday.at("09:00").do(send_daily_notification)
    schedule.every().wednesday.at("09:00").do(send_daily_notification)
    schedule.every().thursday.at("09:00").do(send_daily_notification)
    schedule.every().friday.at("09:00").do(send_daily_notification)
    print("[Scheduler] Started — Mon–Fri at 09:00 IST")

    def _run():
        while True:
            schedule.run_pending()
            time.sleep(30)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    send_daily_notification()
