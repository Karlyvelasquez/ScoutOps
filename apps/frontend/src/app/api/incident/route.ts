import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

    const formData = await request.formData();

    const response = await fetch(`${backendUrl}/incident`, {
      method: 'POST',
      body: formData,
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({ error: 'Backend error', details: errorText }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: 'Internal Server Error', message: error.message }, { status: 500 });
  }
}
