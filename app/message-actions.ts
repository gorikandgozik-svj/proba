'use server';
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { requireUser } from '@/lib/session';
import { identifier,postInput } from '@/lib/validation.mjs';
function notice(text:string):never{redirect('/messages?notice='+encodeURIComponent(text));}
export async function startConversation(form:FormData){
 const {db,user}=await requireUser();const names=String(form.get('recipients')??'').split(',').map(s=>s.trim()).filter(Boolean);
 const parsed=z.array(z.string().regex(/^[a-z0-9_]{3,24}$/)).min(1).max(9).safeParse([...new Set(names)]);const title=z.string().trim().min(1).max(80).safeParse(form.get('title'));
 if(!parsed.success||!title.success)notice('Enter a title and 1–9 usernames separated by commas.');
 const people=await db.from('profiles').select('id,username').in('username',parsed.data).neq('id',user.id);if(people.error||people.data?.length!==parsed.data.length)notice('Some accounts are unavailable. Check usernames and block settings.');
 const {data,error}=await db.rpc('start_conversation',{conversation_title:title.data,recipients:people.data.map(p=>p.id)});if(error)notice('Conversation could not be created. Complete your profile and check block settings.');
 revalidatePath('/messages');redirect('/messages?conversation='+data);
}
export async function sendMessage(form:FormData){
 const {db,user}=await requireUser();const id=identifier.safeParse(form.get('conversation_id'));const body=postInput.safeParse(form.get('body'));if(!id.success||!body.success)notice('Messages must contain 1–2,000 characters.');
 const {error}=await db.from('messages').insert({conversation_id:id.data,sender_id:user.id,body:body.data});if(error)redirect('/messages?conversation='+id.data+'&notice='+encodeURIComponent('Message was not sent. Check membership or blocks, and wait a moment before retrying.'));
 revalidatePath('/messages');redirect('/messages?conversation='+id.data);
}
