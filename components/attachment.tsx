'use client';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import Image from 'next/image';
export function Attachment({url,kind,caption}:{url:string|null;kind:string;caption:string}){
 const [failed,setFailed]=useState(false);const router=useRouter();
 if(failed||!url)return <div className="notice" role="status">Attachment could not load, or its private link expired. <button onClick={()=>{setFailed(false);router.refresh();}}>Refresh attachment</button></div>;
 return kind==='video'?<video className="post-media" src={url} controls playsInline preload="metadata" onError={()=>setFailed(true)}/>:<a href={url} target="_blank" rel="noreferrer"><Image unoptimized width={900} height={700} className="post-media" src={url} alt={caption.slice(0,200)||'Image attached to this post'} loading="lazy" onError={()=>setFailed(true)}/></a>;
}
