import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { agent } = await request.json();
    // Placeholder: in real system, trigger agent via subprocess/API
    return NextResponse.json({ success: true, agent, message: `Triggered ${agent} agent` });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
