import Link from 'next/link';
import { redirect } from 'next/navigation';
import { configured,database } from '@/lib/supabase';
import { identifier } from '@/lib/validation.mjs';
import { rankFeed } from '@/lib/ranking.mjs';
import { Shell } from '@/components/shell';
import { AuthForm } from '@/components/auth';
import { Compose } from '@/components/compose';
import { PostCard,type Post } from '@/components/post';
import { People } from '@/components/people';
type Query={notice?:string;q?:string;mode?:string;community?:string;post?:string;author?:string;page?:string;code?:string;published?:string};
export default async function Home({searchParams}:{searchParams:Promise<Query>}) {
 const params=await searchParams;
 if(params.code) redirect('/auth/callback?code='+encodeURIComponent(params.code));
 const db=configured()?await database():null;const user=db?(await db.auth.getUser()).data.user:null;
 const mode=['following','video','discussions','saved'].includes(params.mode??'')?params.mode:'mixed';
 const page=Math.min(100,Math.max(0,Number.parseInt(params.page??'0')||0));
 const search=(params.q??'').replace(/[^\p{L}\p{N}_ ]/gu,'').slice(0,60);
 let posts:Post[]=[];let people=[] as {id:string;username:string;display_name:string;bio:string}[];let following:string[]=[];let communities:{id:string;name:string}[]=[];let problem='';
 if(db&&user){
  const [follows,prefs,members,directory]=await Promise.all([db.from('follows').select('following_id').eq('follower_id',user.id),db.from('preferences').select('interests').eq('user_id',user.id).maybeSingle(),db.from('memberships').select('community_id').eq('user_id',user.id),search?db.from('profiles').select('*').ilike('username',`%${search}%`).neq('id',user.id).limit(8):Promise.resolve({data:[],error:null})]);
  following=follows.data?.map(r=>r.following_id)??[];people=directory.data??[];
  const ids=members.data?.map(m=>m.community_id)??[];
  if(ids.length){const result=await db.from('communities').select('id,name').in('id',ids);communities=result.data??[];if(result.error)problem='Could not load your communities.';}
  let query=db.from('posts').select('*,profiles!posts_author_id_fkey(*),communities(name),media(path),reactions(user_id),reaction_count:reactions(count),comments(id,body,profiles!comments_author_id_fkey(*)),comment_count:comments(count),bookmarks(user_id)').eq('reactions.user_id',user.id).order('created_at',{ascending:false}).order('created_at',{referencedTable:'comments',ascending:false}).limit(10,{referencedTable:'comments'}).range(page*20,page*20+19);
  if(search)query=query.ilike('body',`%${search}%`);
  if(mode==='following')query=query.in('author_id',[...following,user.id]);
  if(mode==='discussions')query=query.not('community_id','is',null);
  if(mode==='video')query=query.eq('media_kind','video');
  for(const [key,column] of [['community','community_id'],['post','id'],['author','author_id']] as const){const id=identifier.safeParse(params[key]);if(id.success)query=query.eq(column,id.data);}
  if(mode==='saved'){const saved=await db.from('bookmarks').select('post_id').eq('user_id',user.id);query=query.in('id',saved.data?.map(b=>b.post_id)??[]);if(saved.error)problem='Could not load saved posts.';}
  const result=await query;const rows=(result.data??[]) as unknown as (Post&{media:{path:string}|null})[];
  posts=await Promise.all(rows.map(async post=>{if(!post.media)return post;const signed=await db.storage.from('nexus-media').createSignedUrl(post.media.path,300);return {...post,media_url:signed.data?.signedUrl??null};}));
  if(mode==='mixed')posts=rankFeed(posts,prefs.data?.interests??[]);
  if(result.error||follows.error||prefs.error||members.error||directory.error)problem='Could not load your feed. Check the backend connection and retry.';
 }
 const pageLink=(next:number)=>{const query=new URLSearchParams();for(const [key,value]of Object.entries(params))if(value&&key!=='page'&&key!=='notice'&&key!=='code')query.set(key,value);query.set('page',String(next));return '/?'+query.toString();};
 return <Shell section={mode==='video'?'Watch':'Home'} signedIn={Boolean(user)}><section className="intro"><p className="eyebrow">ONE WORLD. MANY PERSPECTIVES.</p><h1>Find your people.<br/><em>Follow your curiosity.</em></h1><p>Ideas, conversations and the people behind them.<br/>All connected, in one place.</p></section><div className="heading"><h2>{search?'Search results':'Your orbit'}</h2><Link href="/preferences"><small>Shape your feed ↗</small></Link></div><div className="tabs">{[['Mixed','mixed'],['Following','following'],['Video','video'],['Discussions','discussions'],['Saved','saved']].map(([label,value])=>{const q=new URLSearchParams();if(value!=='mixed')q.set('mode',value);if(params.community)q.set('community',params.community);if(search)q.set('q',search);return <Link key={value} href={'/?'+q.toString()} aria-current={mode===value?'page':undefined}>{label}</Link>})}</div>{params.notice&&<p className="notice" role="status">{params.notice}</p>}{problem&&<p className="notice" role="alert">{problem}</p>}
 {!db?<section className="card empty"><span className="symbol">✳</span><h2>Your world starts here.</h2><p>Add the Supabase environment variables to connect your live backend. See README.md.</p></section>:!user?<AuthForm/>:<><Compose key={params.published??"composer"} communities={communities}/>{search&&<People people={people} following={following}/>}<p className="feed-explanation">{mode==='mixed'?'Ranked within this page by freshness + your chosen interests.':'Newest first. Your connections and preferences stay with you.'}</p>{posts.length===0&&!problem&&<section className="card empty"><h2>{search?'No matching conversations.':'Room for a new perspective.'}</h2><p>Share something or explore a community that interests you.</p><Link href="/explore">Find your people ↗</Link></section>}{posts.map(post=><PostCard key={post.id} post={post} userId={user.id} returnTo={pageLink(page)}/>)}<div className="actions pagination">{page>0&&<Link href={pageLink(page-1)}>← Newer posts</Link>}{posts.length===20&&<Link href={pageLink(page+1)}>Older posts →</Link>}</div></>}
 </Shell>
}
