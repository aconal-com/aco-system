import { NextResponse } from 'next/server';
import { getStories, createStory } from '@/lib/db';

export async function GET() {
  const stories = await getStories();
  return NextResponse.json(stories);
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const story = await createStory(body);
    return NextResponse.json(story, { status: 201 });
  } catch (e) {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
