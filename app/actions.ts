'use server';
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { database } from '@/lib/supabase';
import { credentials, profileInput, postInput, commentInput, identifier } from '@/lib/validation.mjs';
function message(text: string): never { redirect('/?notice=' + encodeURIComponent(text)); }
async function session() {
  const db = await database();
  const { data, error } = await db.auth.getUser();
  if (error || !data.user) message('Please sign in to continue.');
  return { db, user: data.user };
}
export async function authenticate(form: FormData) {
  const parsed = credentials.safeParse(Object.fromEntries(form));
  if (!parsed.success) message('Enter a valid email and a password of at least 12 characters.');
  const db = await database();
  const signup = form.get('intent') === 'signup';
  const { error } = signup ? await db.auth.signUp(parsed.data) : await db.auth.signInWithPassword(parsed.data);
  if (error) message('Authentication failed. Check your details or try again later.');
  if (signup) message('Account created. Check your email to confirm, then sign in and create your profile.');
  redirect('/profile');
}
export async function signout() { const { db } = await session(); const { error } = await db.auth.signOut(); if (error) message('Sign out failed. Please retry.'); redirect('/'); }
export async function saveProfile(form: FormData) {
  const { db, user } = await session();
  const parsed = profileInput.safeParse(Object.fromEntries(form));
  if (!parsed.success) message('Use a 3–24 character lowercase username, a name and a bio under 280 characters.');
  const { error } = await db.from('profiles').upsert({ id: user.id, ...parsed.data });
  if (error) message('Profile could not be saved. The username may already be taken.');
  revalidatePath('/'); message('Profile saved.');
}
export async function publish(form: FormData) {
  const { db, user } = await session();
  const parsed = postInput.safeParse(form.get('body'));
  if (!parsed.success) message('Write between 1 and 2,000 characters.');
  const { error } = await db.from('posts').insert({ author_id: user.id, body: parsed.data });
  if (error) message('Post was not published. Complete your profile first, or wait a moment before retrying.');
  revalidatePath('/'); message('Your post is live.');
}
export async function react(form: FormData) {
  const { db, user } = await session(); const id = identifier.safeParse(form.get('post_id'));
  if (!id.success) message('Invalid post.');
  const query = form.get('remove') === 'yes' ? db.from('reactions').delete().eq('post_id', id.data).eq('user_id', user.id) : db.from('reactions').upsert({ post_id: id.data, user_id: user.id });
  const { error } = await query; if (error) message('Could not update your like.'); revalidatePath('/');
}
export async function comment(form: FormData) {
  const { db, user } = await session(); const id = identifier.safeParse(form.get('post_id')); const body = commentInput.safeParse(form.get('body'));
  if (!id.success || !body.success) message('Comments must contain 1–500 characters.');
  const { error } = await db.from('comments').insert({ post_id: id.data, author_id: user.id, body: body.data });
  if (error) message('Comment was not saved. Complete your profile or try again later.'); revalidatePath('/');
}
export async function follow(form: FormData) {
  const { db, user } = await session(); const id = identifier.safeParse(form.get('profile_id'));
  if (!id.success || id.data === user.id) message('Invalid account.');
  const { error } = await (form.get('remove') === 'yes' ? db.from('follows').delete().eq('follower_id', user.id).eq('following_id', id.data) : db.from('follows').upsert({ follower_id: user.id, following_id: id.data }));
  if (error) message('Could not update your follow.'); revalidatePath('/');
}
