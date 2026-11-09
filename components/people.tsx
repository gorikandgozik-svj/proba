import Link from 'next/link';
import { follow } from '@/app/actions';
import { blockAccount } from '@/app/social-actions';
import { Submit } from './submit';
export type Person={id:string;username:string;display_name:string;bio:string};
export function People({people,following}:{people:Person[];following:string[]}) {
  return <>{people.map(person=><div className="card person" key={person.id}><span className="avatar">{person.display_name.slice(0,1)}</span><div className="person-info"><Link href={'/people/'+person.username}><strong>{person.display_name}</strong></Link><small>@{person.username}</small><p>{person.bio}</p></div><form action={follow}><input type="hidden" name="profile_id" value={person.id}/><input type="hidden" name="remove" value={following.includes(person.id)?'yes':'no'}/><Submit>{following.includes(person.id)?'Unfollow':'Follow'}</Submit></form><details><summary aria-label={'More options for '+person.username}>···</summary><form action={blockAccount}><input type="hidden" name="profile_id" value={person.id}/><Submit>Block account</Submit></form></details></div>)}</>;
}
