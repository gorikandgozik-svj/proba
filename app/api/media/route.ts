import { NextRequest,NextResponse } from 'next/server';
import { database,configured } from '@/lib/supabase';
import { inspectMedia } from '@/lib/media.mjs';
export const runtime='nodejs';
export async function POST(request:NextRequest){
 if(!configured())return NextResponse.json({error:'Backend not configured.'},{status:503});
 const origin=request.headers.get('origin');let trusted=false;
 try{const incoming=new URL(origin??'');trusted=process.env.NEXT_PUBLIC_APP_URL?incoming.origin===new URL(process.env.NEXT_PUBLIC_APP_URL).origin:incoming.host===request.headers.get('host');}catch{/* Reject malformed origins. */}
 if(!trusted)return NextResponse.json({error:'Invalid request origin.'},{status:403});
 const db=await database();const {data:{user}}=await db.auth.getUser();if(!user)return NextResponse.json({error:'Please sign in.'},{status:401});
 try{
  const maximum=26*1024*1024;if(Number(request.headers.get('content-length'))>maximum)return NextResponse.json({error:'File is too large.'},{status:413});
  const reader=request.body?.getReader();if(!reader)return NextResponse.json({error:'No file received.'},{status:400});const chunks:Uint8Array[]=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>maximum){await reader.cancel();return NextResponse.json({error:'File is too large.'},{status:413});}chunks.push(value);}
  const body=new Uint8Array(size);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.length;}
  const form=await new Response(body,{headers:{'content-type':request.headers.get('content-type')??''}}).formData();const file=form.get('file');if(!(file instanceof File))return NextResponse.json({error:'Select a file.'},{status:400});
  const bytes=new Uint8Array(await file.arrayBuffer());const inspected=inspectMedia(bytes,file.type,file.size);const path=`${user.id}/${crypto.randomUUID()}.${inspected.extension}`;
  const {error:uploadError}=await db.storage.from('nexus-media').upload(path,bytes,{contentType:file.type,upsert:false});if(uploadError)return NextResponse.json({error:'Upload failed. Check your connection or try a smaller file.'},{status:400});
  const {data,error}=await db.from('media').insert({owner_id:user.id,path,kind:inspected.kind,mime:file.type,size:file.size}).select('id,kind').single();
  if(error){await db.storage.from('nexus-media').remove([path]);return NextResponse.json({error:'Attachment could not be saved.'},{status:400});}
  return NextResponse.json(data);
 }catch(error){return NextResponse.json({error:error instanceof Error&&error.message.startsWith('Choose a valid')?error.message:'File could not be processed. Try a supported file.'},{status:400});}
}
