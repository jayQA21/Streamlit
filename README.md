# Jules Sprint Dashboard — Streamlit

Live Jira sprint dashboard for MineHub Jules team. Free hosting on Streamlit Community Cloud.

## Setup

### 1. Get Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token

### 2. Local Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
streamlit run app.py
```

### 3. Deploy to Streamlit Community Cloud (FREE)
1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Click "New app" → connect your GitHub repo
4. Set the main file as `app.py`
5. Go to "Advanced settings" → "Secrets" and add:

```toml
JIRA_EMAIL = "jay.ladva@julesai.com"
JIRA_API_TOKEN = "your_token_here"
JIRA_BASE_URL = "https://minehub.atlassian.net"
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
DASHBOARD_PIN = "1234"
```

### 4. Get Slack Webhook URL (optional)
1. Go to https://api.slack.com/apps
2. Create new app → "Incoming Webhooks"
3. Add webhook to your #jules-dev channel
4. Copy the webhook URL

## Features
- Live Jira data (5 min cache, no AI cost)
- Animated loading screen
- 5 tabs: Overview, Burndown, Velocity, Points, All Tickets
- Clickable ticket links → open in Jira
- Post blocked tickets to Slack (button or auto)
- PIN protection
- Dark theme matching existing dashboard
- Force refresh button

## Cost
- Streamlit hosting: FREE
- Jira API calls: FREE
- Slack webhooks: FREE
- Total: $0/month
