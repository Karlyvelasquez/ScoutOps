import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
    const response = await fetch(`${backendUrl}/incident/${params.id}`, { cache: 'no-store' });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
      }
      return NextResponse.json({ error: 'Backend error', status: response.status }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: 'Internal Server Error', message: error.message }, { status: 500 });
  }
}
