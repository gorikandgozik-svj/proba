import Link from 'next/link';
import { redirect } from 'next/navigation';
import { database, configured } from '@/lib/supabase';
import { saveProfile } from '../actions';
export default async function Profile() {
  if (!configured()) redirect('/');
  const db = await database(); const { data: { user } } = await db.auth.getUser();
  if (!user) redirect('/?notice=Please+sign+in.');
  const { data, error } = await db.from('profiles').select('*').eq('id', user.id).maybeSingle();
  if (error) throw new Error('Profile could not be loaded. Check the database setup.');
  return <main className="account"><Link href="/" className="brand">✳ NEXUS</Link><p className="eyebrow">YOUR SPACE</p><h1>Make yourself known.</h1><p>Your profile connects everything you share.</p><form action={saveProfile} className="card stack"><label>Username<input name="username" defaultValue={data?.username} required pattern="[a-z0-9_]{3,24}" maxLength={24}/></label><label>Display name<input name="display_name" defaultValue={data?.display_name} required maxLength={60}/></label><label>Bio<textarea name="bio" defaultValue={data?.bio} maxLength={280}/></label><button className="primary">Save profile</button></form><Link href="/">← Back to your feed</Link></main>;
}
