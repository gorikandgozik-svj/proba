import Link from 'next/link';
import { requireUser } from '@/lib/session';
import { Shell } from '@/components/shell';
import { People } from '@/components/people';
import { topics } from '@/lib/ranking.mjs';
export default async function Explore({searchParams}:{searchParams:Promise<{q?:string}>}){
 const {db,user}=await requireUser();const params=await searchParams;const q=(params.q??'').replace(/[^a-zA-Z0-9_]/g,'').slice(0,24);let query=db.from('profiles').select('*').neq('id',user.id).order('username').limit(30);if(q)query=query.ilike('username',`%${q}%`);
 const [people,following]=await Promise.all([query,db.from('follows').select('following_id').eq('follower_id',user.id)]);if(people.error||following.error)throw new Error('Discovery unavailable');
 return <Shell section="Explore" signedIn><section className="intro"><p className="eyebrow">FOLLOW YOUR CURIOSITY</p><h1>A wider world.<br/><em>A closer connection.</em></h1></section><form className="row" action="/explore"><input name="q" aria-label="Search people" placeholder="Search by username" defaultValue={q}/><button>Find people</button></form><h2>Find your interests</h2><div className="chips">{topics.map(t=><Link href={'/communities?topic='+t} key={t}>{t} ↗</Link>)}</div><h2>People to discover</h2><People people={people.data??[]} following={following.data?.map(f=>f.following_id)??[]}/>{people.data?.length===0&&<p className="card muted">No matching people yet.</p>}</Shell>
}
