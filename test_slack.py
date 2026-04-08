from integrations.slack import notify_team
import os
from dotenv import load_dotenv

load_dotenv()

repo = os.getenv("GITHUB_REPO")
if not repo:
    raise RuntimeError("GITHUB_REPO is not set in environment")

ticket_url = f"https://github.com/{repo}/issues/1"
print(f"Sending Slack Open Ticket URL: {ticket_url}")

result = notify_team(
    {
        "incident_type": "checkout_failure",
        "severity": "P1",
        "affected_plugin": "api-plugin-payments-stripe",
        "assigned_team": "payments-team",
        "summary": "Users cannot complete checkout.",
    },
    ticket_url,
)

print(result)
