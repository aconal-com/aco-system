import { NextResponse } from 'next/server';
import { getFeed } from '@/lib/db';

export async function GET() {
  const feed = await getFeed();
  return NextResponse.json(feed);
}
