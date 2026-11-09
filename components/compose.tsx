'use client';
import {useState} from 'react';
import { publish } from '@/app/actions';
import { topics } from '@/lib/ranking.mjs';
import { Submit } from './submit';
export function Compose({communities}:{communities:{id:string;name:string}[]}) {
 const [attachment,setAttachment]=useState(''),[uploading,setUploading]=useState(false),[error,setError]=useState('');
 async function upload(file?:File){setAttachment('');setError('');if(!file)return;setUploading(true);try{const data=new FormData();data.set('file',file);const response=await fetch('/api/media',{method:'POST',body:data});const result=await response.json();if(!response.ok)throw new Error(result.error??'Upload failed.');setAttachment(result.id);}catch(e){setError(e instanceof Error?e.message:'Upload failed.');}finally{setUploading(false);}}
 return <form action={publish} className="card composer stack"><label htmlFor="post">What’s on your mind?</label><textarea id="post" name="body" placeholder="An idea, a question, a new perspective…" required maxLength={2000}/><div className="form-grid"><label>Topic<select name="topic">{topics.map(t=><option key={t}>{t}</option>)}</select></label><label>Audience<select name="community_id"><option value="">Your profile</option>{communities.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select></label></div><input type="hidden" name="media_id" value={attachment}/><label className="upload">Attach a photo or video<input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" disabled={uploading} onChange={event=>void upload(event.target.files?.[0])}/></label><small role="status">{uploading?'Uploading…':attachment?'Attachment ready ✓':'Images up to 8 MB · video up to 25 MB · one attachment'}</small>{error&&<p role="alert" className="notice">{error}</p>}<div className="actions"><small>Up to 2,000 characters</small><Submit className="primary" disabled={uploading||Boolean(error)}>Publish ↗</Submit></div></form>;
}
