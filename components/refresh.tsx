'use client';
import {useEffect} from 'react';
import {useRouter} from 'next/navigation';
export function Refresh(){const router=useRouter();useEffect(()=>{const timer=setInterval(()=>{if(document.visibilityState==='visible')router.refresh();},15000);return()=>clearInterval(timer);},[router]);return <button onClick={()=>router.refresh()} title="Refreshes every 15 seconds while visible">Refresh conversations</button>}
