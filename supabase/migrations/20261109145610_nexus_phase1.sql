begin;
create table public.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 username text not null unique check (username ~ '^[a-z0-9_]{3,24}$'),
 display_name text not null check (char_length(display_name) between 1 and 60),
 bio text not null default '' check (char_length(bio) <= 280)
);
create table public.posts (
 id uuid primary key default gen_random_uuid(),
 author_id uuid not null references public.profiles(id) on delete cascade,
 body text not null check (char_length(trim(body)) between 1 and 2000),
 created_at timestamptz not null default now()
);
create index posts_feed_idx on public.posts(created_at desc);
create index posts_author_idx on public.posts(author_id,created_at desc);
create table public.comments (
 id uuid primary key default gen_random_uuid(),
 post_id uuid not null references public.posts(id) on delete cascade,
 author_id uuid not null references public.profiles(id) on delete cascade,
 body text not null check (char_length(trim(body)) between 1 and 500),
 created_at timestamptz not null default now()
);
create index comments_post_idx on public.comments(post_id,created_at);
create index comments_author_idx on public.comments(author_id);
create table public.reactions (
 post_id uuid not null references public.posts(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 primary key(post_id,user_id)
);
create index reactions_user_idx on public.reactions(user_id);
create table public.follows (
 follower_id uuid not null references auth.users(id) on delete cascade,
 following_id uuid not null references public.profiles(id) on delete cascade,
 primary key(follower_id,following_id), check(follower_id <> following_id)
);
create index follows_target_idx on public.follows(following_id);
alter table public.profiles enable row level security;
alter table public.posts enable row level security;
alter table public.comments enable row level security;
alter table public.reactions enable row level security;
alter table public.follows enable row level security;
revoke all on public.profiles, public.posts, public.comments, public.reactions, public.follows from anon;
grant select,insert,update on public.profiles to authenticated;
grant select,insert on public.posts,public.comments to authenticated;
grant select,insert,update,delete on public.reactions,public.follows to authenticated;
create policy profiles_read on public.profiles for select to authenticated using(true);
create policy profiles_insert on public.profiles for insert to authenticated with check(id=(select auth.uid()));
create policy profiles_update on public.profiles for update to authenticated using(id=(select auth.uid())) with check(id=(select auth.uid()));
create policy posts_read on public.posts for select to authenticated using(true);
create policy posts_insert on public.posts for insert to authenticated with check(author_id=(select auth.uid()));
create policy comments_read on public.comments for select to authenticated using(true);
create policy comments_insert on public.comments for insert to authenticated with check(author_id=(select auth.uid()));
create policy reactions_read on public.reactions for select to authenticated using(true);
create policy reactions_insert on public.reactions for insert to authenticated with check(user_id=(select auth.uid()));
create policy reactions_update on public.reactions for update to authenticated using(user_id=(select auth.uid())) with check(user_id=(select auth.uid()));
create policy reactions_delete on public.reactions for delete to authenticated using(user_id=(select auth.uid()));
create policy follows_read on public.follows for select to authenticated using(follower_id=(select auth.uid()));
create policy follows_insert on public.follows for insert to authenticated with check(follower_id=(select auth.uid()));
create policy follows_update on public.follows for update to authenticated using(follower_id=(select auth.uid())) with check(follower_id=(select auth.uid()));
create policy follows_delete on public.follows for delete to authenticated using(follower_id=(select auth.uid()));
-- Enforce the same cooldown for API clients and server actions. Serialize per author.
create function public.check_publish_cooldown() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 perform pg_advisory_xact_lock(hashtextextended(new.author_id::text,0));
 if tg_table_name='posts' then
   if exists(select 1 from public.posts where author_id=new.author_id and created_at>now()-interval '10 seconds') then raise exception 'Please wait before publishing again'; end if;
 else
   if exists(select 1 from public.comments where author_id=new.author_id and created_at>now()-interval '5 seconds') then raise exception 'Please wait before commenting again'; end if;
 end if;
 new.created_at=now(); return new;
end; $$;
revoke execute on function public.check_publish_cooldown() from public,anon,authenticated;
create trigger posts_cooldown before insert on public.posts for each row execute function public.check_publish_cooldown();
create trigger comments_cooldown before insert on public.comments for each row execute function public.check_publish_cooldown();
commit;
