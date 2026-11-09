import { redirect } from 'next/navigation';
import { database, configured } from './supabase';
export async function requireUser() {
  if (!configured()) redirect('/');
  const db = await database();
  const { data: { user }, error } = await db.auth.getUser();
  if (error || !user) redirect('/?notice=Please+sign+in+to+continue.');
  return { db, user };
}
export function destination(form: FormData) {
  const value = String(form.get('returnTo') ?? '/');
  return /^\/(?:communities|preferences|notifications|messages|profile)?(?:\?[a-zA-Z0-9_=&%-]*)?$/.test(value) ? value : '/';
}
