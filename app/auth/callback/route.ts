import { NextRequest,NextResponse } from 'next/server';
import { database } from '@/lib/supabase';
export async function GET(request:NextRequest){const code=request.nextUrl.searchParams.get('code');if(code){const db=await database();const {error}=await db.auth.exchangeCodeForSession(code);if(!error)return NextResponse.redirect(new URL('/profile',request.url));}return NextResponse.redirect(new URL('/?notice=Confirmation+failed.+Sign+in+or+request+a+new+email.',request.url));}
