import { requireUser } from '@/lib/session';
import { topics } from '@/lib/ranking.mjs';
import { Shell } from '@/components/shell';
import {Appearance} from '@/components/appearance';
import { Submit } from '@/components/submit';
import { savePreferences,restoreHidden,blockAccount } from '../social-actions';
export default async function Preferences({searchParams}:{searchParams:Promise<{notice?:string}>}) {
  const {db,user}=await requireUser();const params=await searchParams;
  const [prefs,blocks]=await Promise.all([db.from('preferences').select('interests').eq('user_id',user.id).maybeSingle(),db.from('blocks').select('blocked_id').eq('user_id',user.id)]);
  if(prefs.error||blocks.error) throw new Error('Preferences could not be loaded');
  return <Shell section="Preferences" signedIn><section className="intro"><p className="eyebrow">YOU ARE IN CONTROL</p><h1>Make room for<br/><em>what matters.</em></h1><p>Mixed feed ranks each page using freshness and your selected interests. No hidden engagement score.</p></section>{params.notice&&<p role="status" className="notice">{params.notice}</p>}<Appearance/><form className="card stack" action={savePreferences}><input type="hidden" name="returnTo" value="/preferences"/><h2>Your interests</h2>{topics.map(t=><label className="check" key={t}><input type="checkbox" name="interests" value={t} defaultChecked={prefs.data?.interests.includes(t)}/>{t}</label>)}<small>Freshness: up to 48 points, decreasing 1 per hour. A selected topic adds 12 points. Following and Video stay chronological.</small><Submit className="primary">Save interests</Submit></form><form action={restoreHidden} className="card stack"><input type="hidden" name="returnTo" value="/preferences"/><h2>A fresh look</h2><p>Restore all posts you previously hid.</p><Submit>Restore hidden posts</Submit></form><section className="card"><h2>Blocked accounts</h2>{blocks.data?.length===0&&<p className="muted">No blocked accounts.</p>}{blocks.data?.map(b=><form className="row" action={blockAccount} key={b.blocked_id}><input type="hidden" name="profile_id" value={b.blocked_id}/><input type="hidden" name="remove" value="yes"/><input type="hidden" name="returnTo" value="/preferences"/><code>{b.blocked_id.slice(0,8)}…</code><Submit>Unblock</Submit></form>)}</section></Shell>;
}
