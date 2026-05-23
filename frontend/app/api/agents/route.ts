import { NextResponse } from 'next/server';
import { getAgents, updateAgent } from '@/lib/db';

export async function GET() {
  const agents = await getAgents();
  return NextResponse.json(agents);
}

export async function PATCH(request: Request) {
  try {
    const { id, ...updates } = await request.json();
    const agent = await updateAgent(id, updates);
    if (!agent) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(agent);
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
