"""
Jules Sprint Daily Notifier — scheduler.py
Fires at 9:00 AM London time every weekday via background thread
"""

import os, re, requests, threading
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

JIRA_EMAIL    = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN    = os.getenv("JIRA_API_TOKEN", "").replace("\n","").replace("\r","").replace(" ","").strip()
JIRA_BASE     = os.getenv("JIRA_BASE_URL", "https://minehub.atlassian.net")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://julesdashboard.streamlit.app")

PROJECT      = "JENG"
SPRINT_NAME  = "Release Sprint 3"
SPRINT_START = date(2026, 2, 24)
SPRINT_END   = date(2026, 4, 12)
SPRINT_DAYS  = 48

DONE_STATUSES    = {"Done","PO/QA VALID","In demo","In production","CS reviewed","Demo","In Production","CS Reviewed"}
BLOCKED_STATUSES = {"Blocked"}
ACTIVE_STATUSES  = {"In Progress","AIM OF THE DAY","Tech review","PO review","PO/QA Test run","Aim Of The week","PO not valid","Tech strategy"}

DEV_EMOJIS = {
    "Nikita Vaidya": "🟣",
    "Satadru Roy":   "🩷",
    "Rizky Ario":    "🟠",
    "Jay Pitroda":   "🟢",
}

DAILY_TIPS = [
    "Blocked >2 days? Speak up — silence won't unblock it. 🔊",
    "A ticket in review is NOT done. Push it over the line! 🏁",
    "Small PRs merge faster. Big PRs sit forever. 🐢",
    "Update your ticket status before standup — not during! ⚡",
    "Done = merged + deployed + verified. All three. 🚀",
    "The best code is the code you don't write. ✂️",
    "Sprint health = team health. Look out for each other. 🤝",
    "Every blocker resolved today = smoother sprint review. 📊",
    "Write the test first, thank yourself later. 🧪",
    "If it's unclear, clarify it now — not on the last day. 💬",
]

MOTIVATIONAL = [
    "Let's crush it today! 💪",
    "Another day, another ticket shipped! 🚀",
    "Stay focused, stay unblocked! 🎯",
    "Great work so far — keep pushing! ⚡",
    "Sprint strong, team! 🏃",
]


def clean_title(s):
    s = re.sub(r'^(AAWU,?\s*|AAD,?\s*)', '', s, flags=re.IGNORECASE)
    return s.lstrip(',').strip()[:60]


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
    total     = len(tickets)
    done      = [t for t in tickets if t["status"] in DONE_STATUSES]
    blocked   = [t for t in tickets if t["status"] in BLOCKED_STATUSES]
    total_sp  = sum(t["sp"] or 0 for t in tickets)
    done_sp   = sum(t["sp"] or 0 for t in done)
    today     = date.today()
    cur_day   = max(1, min((today - SPRINT_START).days + 1, SPRINT_DAYS))
    days_left = SPRINT_DAYS - cur_day
    pct_done  = round(len(done) / total * 100) if total else 0
    pct_time  = round((cur_day - 1) / (SPRINT_DAYS - 1) * 100)
    gap_pct   = pct_done - pct_time
    health    = "on-track" if gap_pct >= -5 else "at-risk" if gap_pct >= -15 else "behind"
    return dict(
        total=total, done=done, blocked=blocked, total_sp=total_sp, done_sp=done_sp,
        cur_day=cur_day, days_left=days_left, pct_done=pct_done, pct_time=pct_time,
        gap_pct=gap_pct, health=health,
    )


def progress_bar(pct, width=20):
    """Emoji-based progress bar"""
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def sprint_countdown(cur_day, total=48, width=24):
    """Mini sprint timeline bar"""
    done_blocks  = round(cur_day / total * width)
    left_blocks  = width - done_blocks
    return "▓" * done_blocks + "░" * left_blocks


def get_daily_tip():
    return DAILY_TIPS[date.today().timetuple().tm_yday % len(DAILY_TIPS)]


def get_motivation():
    return MOTIVATIONAL[date.today().timetuple().tm_yday % len(MOTIVATIONAL)]


def build_slack_message(m, tickets):
    today    = date.today()
    weekday  = today.strftime("%A")
    date_str = today.strftime("%d %b %Y")

    # ── Health config ──
    hcfg = {
        "on-track": {"icon": "🟢", "label": "ON  TRACK ✅",  "bar_char": "🟩"},
        "at-risk":  {"icon": "🟡", "label": "AT  RISK  ⚠️", "bar_char": "🟨"},
        "behind":   {"icon": "🔴", "label": "BEHIND   🚨",   "bar_char": "🟥"},
    }
    hc = hcfg[m["health"]]

    # ── Visual bars ──
    done_bar  = progress_bar(m["pct_done"])
    time_bar  = progress_bar(m["pct_time"])
    countdown = sprint_countdown(m["cur_day"])

    # ── Sprint velocity ──
    avg_daily_needed = round((m["total"] - len(m["done"])) / m["days_left"]) if m["days_left"] > 0 else 0

    # ── Per-dev summary ──
    dev_lines = []
    for name, emoji in DEV_EMOJIS.items():
        dev_tix     = [t for t in tickets if t["assignee"] == name]
        if not dev_tix: continue
        dev_done    = sum(1 for t in dev_tix if t["status"] in DONE_STATUSES)
        dev_blocked = sum(1 for t in dev_tix if t["status"] in BLOCKED_STATUSES)
        dev_sp_done = sum(t["sp"] or 0 for t in dev_tix if t["status"] in DONE_STATUSES)
        dev_sp_tot  = sum(t["sp"] or 0 for t in dev_tix)
        pct         = round(dev_done / len(dev_tix) * 100) if dev_tix else 0
        mini_bar    = progress_bar(pct, width=8)
        flag        = "  🚨 BLOCKED" if dev_blocked >= 2 else "  ⚠️" if dev_blocked == 1 else ""
        sp_txt      = f"  `{dev_sp_done}/{dev_sp_tot} SP`" if dev_sp_tot else ""
        dev_lines.append(
            f"{emoji} *{name.split()[0]}*  `{mini_bar}`  {pct}%  `{dev_done}/{len(dev_tix)}`{sp_txt}{flag}"
        )

    # ── Blockers ──
    blocked_lines = []
    for t in m["blocked"][:6]:
        emoji = DEV_EMOJIS.get(t["assignee"], "⚪")
        name  = t["assignee"].split()[0] if t["assignee"] != "Unassigned" else "—"
        blocked_lines.append(
            f"{emoji}  *<{JIRA_BASE}/browse/{t['key']}|{t['key']}>*  ›  _{t['summary']}_  `{name}`"
        )
    if len(m["blocked"]) > 6:
        blocked_lines.append(f"_+ {len(m['blocked'])-6} more blocked tickets_")

    blocked_section = "\n".join(blocked_lines) if blocked_lines else "✨  *No blockers today — keep it up!*"

    tip        = get_daily_tip()
    motivation = get_motivation()

    blocks = [

        # ══════════════════════════════════════════
        # BLOCK 1 — HERO HEADER
        # ══════════════════════════════════════════
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚀  Good Morning, Jules Team!  ·  {weekday}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📅  *{date_str}*  ·  {SPRINT_NAME}  ·  {motivation}"}]
        },

        {"type": "divider"},

        # ══════════════════════════════════════════
        # BLOCK 2 — BURNDOWN VISUAL
        # ══════════════════════════════════════════
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*📉  Sprint Burndown  ·  Day {m['cur_day']} of {SPRINT_DAYS}*\n\n"
                    f"```\n"
                    f"  TIMELINE  ┣{time_bar}┫  {m['pct_time']}% elapsed\n"
                    f"  DONE      ┣{done_bar}┫  {m['pct_done']}% complete\n"
                    f"  SPRINT    ┣{countdown}┫\n"
                    f"```\n"
                    f"{hc['icon']}  *Status:* {hc['label']}   ·   "
                    f"🎯  Need ~*{avg_daily_needed} tickets/day* to finish on time   ·   "
                    f"📅  *{m['days_left']} days* remaining"
                )
            }
        },

        {"type": "divider"},

        # ══════════════════════════════════════════
        # BLOCK 3 — SPRINT STATS GRID
        # ══════════════════════════════════════════
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📊  Sprint Snapshot*"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"✅  *Tickets Done*\n`{len(m['done'])} / {m['total']}`"},
                {"type": "mrkdwn", "text": f"💎  *Story Points*\n`{m['done_sp']} / {m['total_sp']} SP`"},
                {"type": "mrkdwn", "text": f"🚫  *Blocked*\n`{len(m['blocked'])} tickets`"},
                {"type": "mrkdwn", "text": f"📅  *Days Left*\n`{m['days_left']} of {SPRINT_DAYS}`"},
            ]
        },

        {"type": "divider"},

        # ══════════════════════════════════════════
        # BLOCK 4 — TEAM VELOCITY
        # ══════════════════════════════════════════
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*👥  Team Velocity*\n\n" + "\n".join(dev_lines)
            }
        },

        {"type": "divider"},

        # ══════════════════════════════════════════
        # BLOCK 5 — BLOCKERS ALERT
        # ══════════════════════════════════════════
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*🚨  Active Blockers  ({len(m['blocked'])})*\n"
                    f"{'━' * 36}\n"
                    f"{blocked_section}"
                )
            }
        },

        {"type": "divider"},

        # ══════════════════════════════════════════
        # BLOCK 6 — TIP + CTA
        # ══════════════════════════════════════════
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"💡  *Daily Tip:*  _{tip}_"}
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊  Live Dashboard", "emoji": True},
                    "url": DASHBOARD_URL,
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔗  Jira Board", "emoji": True},
                    "url": f"{JIRA_BASE}/jira/software/c/projects/{PROJECT}/boards"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📋  All Blockers", "emoji": True},
                    "url": f"{JIRA_BASE}/jira/software/c/projects/{PROJECT}/boards?assignee=unassigned&label=blocked"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_Jules Sprint Bot  ·  Auto-sent at 9:00 AM  ·  {SPRINT_NAME}_"}
            ]
        }
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
        print(f"[Scheduler] Sending daily notification — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        tickets = fetch_sprint_data()
        m       = build_metrics(tickets)
        payload = build_slack_message(m, tickets)
        resp    = requests.post(SLACK_WEBHOOK, json=payload, timeout=15)
        if resp.status_code == 200:
            print("[Scheduler] ✅ Sent!")
        else:
            print(f"[Scheduler] ❌ Slack error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Scheduler] ❌ {e}")


def start_scheduler():
    import schedule, time

    schedule.every().monday.at("09:00").do(send_daily_notification)
    schedule.every().tuesday.at("09:00").do(send_daily_notification)
    schedule.every().wednesday.at("09:00").do(send_daily_notification)
    schedule.every().thursday.at("09:00").do(send_daily_notification)
    schedule.every().friday.at("09:00").do(send_daily_notification)

    print("[Scheduler] 🕘 Scheduler started — fires Mon–Fri at 09:00")

    def _run():
        while True:
            schedule.run_pending()
            time.sleep(30)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    # Test immediately — run this locally to preview the message
    send_daily_notification()
