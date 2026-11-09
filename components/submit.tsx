'use client';
import { useFormStatus } from 'react-dom';
export function Submit({children,className,name,value,disabled=false}:{children:React.ReactNode;className?:string;name?:string;value?:string;disabled?:boolean}) {
  const {pending}=useFormStatus();
  return <button className={className} name={name} value={value} disabled={pending||disabled} aria-busy={pending}>{pending?'Saving…':children}</button>;
}
