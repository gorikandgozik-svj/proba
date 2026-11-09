import { NextRequest, NextResponse } from 'next/server';
import { database } from '@/lib/supabase';
export async function GET(request: NextRequest) {
  const token_hash = request.nextUrl.searchParams.get('token_hash');
  if (token_hash) {
    const db = await database();
    const { error } = await db.auth.verifyOtp({ token_hash, type: 'email' });
    if (!error) return NextResponse.redirect(new URL('/profile', request.url));
  }
  return NextResponse.redirect(new URL('/?notice=Confirmation+failed.+Request+a+new+email.', request.url));
}
