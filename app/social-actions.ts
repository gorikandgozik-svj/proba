'use server';
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { requireUser, destination } from '@/lib/session';
import { identifier } from '@/lib/validation.mjs';
async function done(form: FormData, notice?: string) {
  revalidatePath('/', 'layout');
  const path = destination(form);
  redirect(path + (notice ? (path.includes('?') ? '&' : '?') + 'notice=' + encodeURIComponent(notice) : ''));
}
export async function controlPost(form: FormData) {
  const { db, user } = await requireUser(); const id = identifier.safeParse(form.get('post_id'));
  const type = form.get('control');
  if (!id.success || !['bookmark','hide'].includes(String(type))) return done(form,'Invalid request.');
  const table = type === 'hide' ? 'hidden_posts' : 'bookmarks';
  const { error } = await (form.get('remove') === 'yes' ? db.from(table).delete().eq('user_id',user.id).eq('post_id',id.data) : db.from(table).upsert({user_id:user.id,post_id:id.data},{ignoreDuplicates:true}));
  return done(form,error ? 'Your change could not be saved.' : type === 'hide' ? 'Post hidden. Restore hidden posts in Preferences.' : undefined);
}
export async function createCommunity(form: FormData) {
  const { db } = await requireUser();
  const input = z.object({name:z.string().trim().min(3).max(50),description:z.string().trim().min(1).max(500),topic:z.enum(['technology','art','science','culture','life'])}).safeParse(Object.fromEntries(form));
  if (!input.success) return done(form,'Check the community name, description and topic.');
  const { error } = await db.rpc('create_community',{community_name:input.data.name,community_description:input.data.description,community_topic:input.data.topic});
  return done(form,error ? 'Community could not be created. Its name may be taken.' : 'Community created. You are its first member.');
}
export async function membership(form: FormData) {
  const { db,user }=await requireUser(); const id=identifier.safeParse(form.get('community_id'));
  if (!id.success) return done(form,'Invalid community.');
  const {error}=await(form.get('remove')==='yes' ? db.from('memberships').delete().eq('user_id',user.id).eq('community_id',id.data):db.from('memberships').upsert({user_id:user.id,community_id:id.data},{ignoreDuplicates:true}));
  return done(form,error?'Could not change your membership.':undefined);
}
export async function savePreferences(form: FormData) {
  const {db,user}=await requireUser(); const interests=z.array(z.enum(['technology','art','science','culture','life'])).max(5).safeParse(form.getAll('interests'));
  if(!interests.success) return done(form,'Select up to five interests.');
  const {error}=await db.from('preferences').upsert({user_id:user.id,interests:interests.data});
  return done(form,error?'Could not save preferences.':'Preferences saved.');
}
export async function restoreHidden(form: FormData) {
  const {db,user}=await requireUser(); const {error}=await db.from('hidden_posts').delete().eq('user_id',user.id);
  return done(form,error?'Could not restore posts.':'Hidden posts restored.');
}
export async function blockAccount(form: FormData) {
  const {db,user}=await requireUser(); const id=identifier.safeParse(form.get('profile_id'));
  if(!id.success||id.data===user.id) return done(form,'Invalid account.');
  const {error}=await(form.get('remove')==='yes'?db.from('blocks').delete().eq('user_id',user.id).eq('blocked_id',id.data):db.from('blocks').upsert({user_id:user.id,blocked_id:id.data},{ignoreDuplicates:true}));
  return done(form,error?'Could not change this block.':'Block settings updated.');
}
export async function reportPost(form: FormData) {
  const {db,user}=await requireUser(); const id=identifier.safeParse(form.get('post_id')); const reason=z.string().trim().min(5).max(500).safeParse(form.get('reason'));
  if(!id.success||!reason.success) return done(form,'Describe the issue in 5–500 characters.');
  const {error}=await db.from('reports').insert({reporter_id:user.id,post_id:id.data,reason:reason.data});
  return done(form,error?'Report could not be submitted, or has already been received.':'Report received for review.');
}
export async function readNotifications(form: FormData) {
  const {db,user}=await requireUser(); const {error}=await db.from('notifications').update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null);
  return done(form,error?'Could not mark notifications read.':undefined);
}
