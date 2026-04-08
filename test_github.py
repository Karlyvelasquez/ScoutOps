from integrations.github import create_ticket

result = create_ticket(
    {
        "incident_type": "checkout_failure",
        "severity": "P1",
        "affected_plugin": "api-plugin-payments-stripe",
        "layer": "GraphQL resolver -> placeOrder",
        "assigned_team": "payments-team",
        "summary": "Users cannot complete checkout.",
        "suggested_actions": ["Check Stripe API status"],
        "reporter_email": "test@test.com",
        "original_description": "I cannot pay",
    }
)

print(result)
