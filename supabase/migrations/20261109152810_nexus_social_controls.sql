begin;
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;
create table public.blocks (
 user_id uuid not null references auth.users(id) on delete cascade,
 blocked_id uuid not null references auth.users(id) on delete cascade,
 primary key(user_id,blocked_id), check(user_id<>blocked_id)
);
alter table public.blocks enable row level security;
revoke all on public.blocks from anon,authenticated;
grant select,insert,delete on public.blocks to authenticated;
create policy blocks_read on public.blocks for select to authenticated using(user_id=(select auth.uid()));
create policy blocks_insert on public.blocks for insert to authenticated with check(user_id=(select auth.uid()));
create policy blocks_delete on public.blocks for delete to authenticated using(user_id=(select auth.uid()));
create index blocks_target_idx on public.blocks(blocked_id);
create function private.blocked(a uuid,b uuid) returns boolean language sql stable security definer set search_path='' as $$ select exists(select 1 from public.blocks where (user_id=a and blocked_id=b) or (user_id=b and blocked_id=a)); $$;
revoke execute on function private.blocked(uuid,uuid) from public,anon;
grant execute on function private.blocked(uuid,uuid) to authenticated;
create table public.communities (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references public.profiles(id) on delete cascade,
 name text not null unique check(char_length(name) between 3 and 50),
 description text not null check(char_length(description) between 1 and 500),
 topic text not null check(topic in ('technology','art','science','culture','life')),
 created_at timestamptz not null default now()
);
create index communities_owner_idx on public.communities(owner_id);
create table public.memberships (
 user_id uuid not null references auth.users(id) on delete cascade,
 community_id uuid not null references public.communities(id) on delete cascade,
 primary key(user_id,community_id)
);
create index memberships_community_idx on public.memberships(community_id);
alter table public.communities enable row level security;
alter table public.memberships enable row level security;
revoke all on public.communities,public.memberships from anon,authenticated;
grant select,insert on public.communities to authenticated;
grant select,insert,delete on public.memberships to authenticated;
create policy communities_read on public.communities for select to authenticated using(not private.blocked(owner_id,(select auth.uid())));
create policy communities_insert on public.communities for insert to authenticated with check(owner_id=(select auth.uid()));
create policy memberships_read on public.memberships for select to authenticated using(user_id=(select auth.uid()));
create policy memberships_insert on public.memberships for insert to authenticated with check(user_id=(select auth.uid()) and exists(select 1 from public.communities c where c.id=community_id));
create policy memberships_delete on public.memberships for delete to authenticated using(user_id=(select auth.uid()));
alter table public.posts add column community_id uuid references public.communities(id) on delete cascade;
alter table public.posts add column topic text not null default 'life' check(topic in ('technology','art','science','culture','life'));
create index posts_community_idx on public.posts(community_id,created_at desc);
create table public.bookmarks (user_id uuid not null references auth.users(id) on delete cascade,post_id uuid not null references public.posts(id) on delete cascade,primary key(user_id,post_id));
create table public.hidden_posts (user_id uuid not null references auth.users(id) on delete cascade,post_id uuid not null references public.posts(id) on delete cascade,primary key(user_id,post_id));
create index bookmarks_post_idx on public.bookmarks(post_id);
create index hidden_posts_post_idx on public.hidden_posts(post_id);
alter table public.bookmarks enable row level security;
alter table public.hidden_posts enable row level security;
revoke all on public.bookmarks,public.hidden_posts from anon,authenticated;
grant select,insert,delete on public.bookmarks,public.hidden_posts to authenticated;
create policy bookmarks_read on public.bookmarks for select to authenticated using(user_id=(select auth.uid()));
create policy bookmarks_insert on public.bookmarks for insert to authenticated with check(user_id=(select auth.uid()));
create policy bookmarks_delete on public.bookmarks for delete to authenticated using(user_id=(select auth.uid()));
create policy hidden_read on public.hidden_posts for select to authenticated using(user_id=(select auth.uid()));
create policy hidden_insert on public.hidden_posts for insert to authenticated with check(user_id=(select auth.uid()));
create policy hidden_delete on public.hidden_posts for delete to authenticated using(user_id=(select auth.uid()));
drop policy profiles_read on public.profiles;
create policy profiles_read on public.profiles for select to authenticated using(not private.blocked(id,(select auth.uid())));
drop policy posts_read on public.posts;
create policy posts_read on public.posts for select to authenticated using(not private.blocked(author_id,(select auth.uid())) and not exists(select 1 from public.hidden_posts h where h.post_id=id and h.user_id=(select auth.uid())));
drop policy posts_insert on public.posts;
create policy posts_insert on public.posts for insert to authenticated with check(author_id=(select auth.uid()) and (community_id is null or exists(select 1 from public.memberships m where m.community_id=posts.community_id and m.user_id=(select auth.uid()))));
drop policy comments_read on public.comments;
create policy comments_read on public.comments for select to authenticated using(not private.blocked(author_id,(select auth.uid())) and exists(select 1 from public.posts p where p.id=post_id));
drop policy comments_insert on public.comments;
create policy comments_insert on public.comments for insert to authenticated with check(author_id=(select auth.uid()) and exists(select 1 from public.posts p where p.id=post_id));
drop policy reactions_insert on public.reactions;
create policy reactions_insert on public.reactions for insert to authenticated with check(user_id=(select auth.uid()) and exists(select 1 from public.posts p where p.id=post_id));
drop policy follows_insert on public.follows;
create policy follows_insert on public.follows for insert to authenticated with check(follower_id=(select auth.uid()) and not private.blocked(following_id,(select auth.uid())));
create table public.preferences (
 user_id uuid primary key references auth.users(id) on delete cascade,
 interests text[] not null default '{}' check(interests <@ array['technology','art','science','culture','life']::text[] and cardinality(interests)<=5)
);
alter table public.preferences enable row level security;
revoke all on public.preferences from anon,authenticated;
grant select,insert,update on public.preferences to authenticated;
create policy preferences_read on public.preferences for select to authenticated using(user_id=(select auth.uid()));
create policy preferences_insert on public.preferences for insert to authenticated with check(user_id=(select auth.uid()));
create policy preferences_update on public.preferences for update to authenticated using(user_id=(select auth.uid())) with check(user_id=(select auth.uid()));
create table public.reports (
 id uuid primary key default gen_random_uuid(),
 reporter_id uuid not null references auth.users(id) on delete cascade,
 post_id uuid not null references public.posts(id) on delete cascade,
 reason text not null check(char_length(trim(reason)) between 5 and 500),
 created_at timestamptz not null default now(), unique(reporter_id,post_id)
);
create index reports_post_idx on public.reports(post_id);
alter table public.reports enable row level security;
revoke all on public.reports from anon,authenticated;
grant select,insert on public.reports to authenticated;
create policy reports_read on public.reports for select to authenticated using(reporter_id=(select auth.uid()));
create policy reports_insert on public.reports for insert to authenticated with check(reporter_id=(select auth.uid()) and exists(select 1 from public.posts p where p.id=post_id));
create table public.notifications (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 actor_id uuid not null references public.profiles(id) on delete cascade,
 kind text not null check(kind in ('like','comment','follow')),
 post_id uuid references public.posts(id) on delete cascade,
 created_at timestamptz not null default now(),read_at timestamptz
);
create index notifications_user_idx on public.notifications(user_id,created_at desc);
create index notifications_actor_idx on public.notifications(actor_id);
create index notifications_post_idx on public.notifications(post_id);
alter table public.notifications enable row level security;
revoke all on public.notifications from anon,authenticated;
grant select on public.notifications to authenticated;
grant update(read_at) on public.notifications to authenticated;
create policy notifications_read on public.notifications for select to authenticated using(user_id=(select auth.uid()) and not private.blocked(actor_id,(select auth.uid())));
create policy notifications_update on public.notifications for update to authenticated using(user_id=(select auth.uid())) with check(user_id=(select auth.uid()));
create function private.notify_social_event() returns trigger language plpgsql security definer set search_path='' as $$
declare receiver uuid; actor uuid; target uuid; event text;
begin
 if tg_table_name='follows' then receiver=new.following_id; actor=new.follower_id; event='follow';
 elsif tg_table_name='comments' then select author_id into receiver from public.posts where id=new.post_id; actor=new.author_id; target=new.post_id; event='comment';
 else select author_id into receiver from public.posts where id=new.post_id; actor=new.user_id; target=new.post_id; event='like'; end if;
 if receiver<>actor and not private.blocked(receiver,actor) then insert into public.notifications(user_id,actor_id,kind,post_id) values(receiver,actor,event,target); end if;
 return new;
end; $$;
revoke execute on function private.notify_social_event() from public,anon,authenticated;
create trigger follows_notify after insert on public.follows for each row execute function private.notify_social_event();
create trigger comments_notify after insert on public.comments for each row execute function private.notify_social_event();
create trigger reactions_notify after insert on public.reactions for each row execute function private.notify_social_event();
commit;
