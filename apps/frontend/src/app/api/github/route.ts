import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { title, body, incident_id } = await request.json();

    const token = process.env.GITHUB_TOKEN;
    const repo = process.env.GITHUB_REPO || 'Sacr1013/sre-incidents';

    if (!token) {
      return NextResponse.json({ error: 'GitHub token not configured' }, { status: 500 });
    }

    // 1. Create Github Issue
    const ghResponse = await fetch(`https://api.github.com/repos/${repo}/issues`, {
      method: 'POST',
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': `token ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title,
        body,
        labels: ['incident', 'triage']
      }),
    });

    if (!ghResponse.ok) {
      const errorText = await ghResponse.text();
      return NextResponse.json({ error: 'Failed to create GitHub issue', details: errorText }, { status: ghResponse.status });
    }

    const issueData = await ghResponse.json();

    // 2. Report Issue Creation to Backend Webhook
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
    try {
      await fetch(`${backendUrl}/webhook/ticket-update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          incident_id,
          ticket_id: issueData.html_url,
          ticket_status: 'open',
          resolution_notes: ''
        }),
      });
    } catch (webhookError) {
      console.error('Failed to notify backend via webhook', webhookError);
      // We don't fail the request if webhook fails, as the issue was created
    }

    return NextResponse.json(issueData);
  } catch (error: any) {
    return NextResponse.json({ error: 'Internal Server Error', message: error.message }, { status: 500 });
  }
}
