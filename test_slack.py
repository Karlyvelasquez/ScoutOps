from integrations.slack import notify_team

result = notify_team(
    {
        "incident_type": "checkout_failure",
        "severity": "P1",
        "affected_plugin": "api-plugin-payments-stripe",
        "assigned_team": "payments-team",
        "summary": "Users cannot complete checkout.",
    },
    "https://github.com/tu-usuario/sre-agent-tickets/issues/1",
)

print(result)
