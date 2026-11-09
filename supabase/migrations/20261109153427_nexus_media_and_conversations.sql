begin;
create table public.media (
 id uuid primary key default gen_random_uuid(),owner_id uuid not null references auth.users(id) on delete cascade,
 path text not null unique,kind text not null check(kind in ('image','video')),
 mime text not null check(mime in ('image/jpeg','image/png','image/webp','video/mp4','video/webm')),
 size integer not null check(size between 1 and 26214400),created_at timestamptz not null default now(),
 check(split_part(path,'/',1)=owner_id::text)
);
create index media_owner_idx on public.media(owner_id,created_at desc);
alter table public.posts add column media_id uuid unique references public.media(id);
alter table public.posts add column media_kind text check(media_kind in ('image','video'));
alter table public.posts add constraint posts_media_pair check((media_id is null)=(media_kind is null));
alter table public.media enable row level security;
revoke all on public.media from anon,authenticated;
grant select,insert on public.media to authenticated;
create policy media_read on public.media for select to authenticated using(owner_id=(select auth.uid()) or exists(select 1 from public.posts p where p.media_id=id));
create policy media_insert on public.media for insert to authenticated with check(owner_id=(select auth.uid()));
create function private.verify_post_media() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if new.media_id is not null and not exists(select 1 from public.media m where m.id=new.media_id and m.owner_id=new.author_id and m.kind=new.media_kind) then raise exception 'Invalid attachment'; end if;
 return new;
end; $$;
revoke execute on function private.verify_post_media() from public,anon,authenticated;
create trigger posts_media_check before insert on public.posts for each row execute function private.verify_post_media();
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('nexus-media','nexus-media',false,26214400,array['image/jpeg','image/png','image/webp','video/mp4','video/webm']);
create policy nexus_upload on storage.objects for insert to authenticated with check(bucket_id='nexus-media' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy nexus_media_read on storage.objects for select to authenticated using(bucket_id='nexus-media' and ((storage.foldername(name))[1]=(select auth.uid())::text or exists(select 1 from public.media m where m.path=name)));
create policy nexus_remove_orphan on storage.objects for delete to authenticated using(bucket_id='nexus-media' and (storage.foldername(name))[1]=(select auth.uid())::text and not exists(select 1 from public.media m where m.path=name));
create table public.conversations (
 id uuid primary key default gen_random_uuid(),owner_id uuid not null references auth.users(id) on delete cascade,
 title text not null check(char_length(trim(title)) between 1 and 80),kind text not null check(kind in ('direct','group')),created_at timestamptz not null default now()
);
create index conversations_owner_idx on public.conversations(owner_id);
create table public.conversation_participants (
 conversation_id uuid not null references public.conversations(id) on delete cascade,
 user_id uuid not null references public.profiles(id) on delete cascade, primary key(conversation_id,user_id)
);
create index conversation_participants_user_idx on public.conversation_participants(user_id);
create function private.is_participant(cid uuid) returns boolean language sql stable security definer set search_path='' as $$ select exists(select 1 from public.conversation_participants where conversation_id=cid and user_id=(select auth.uid())); $$;
revoke execute on function private.is_participant(uuid) from public,anon;
grant execute on function private.is_participant(uuid) to authenticated;
alter table public.conversations enable row level security;
alter table public.conversation_participants enable row level security;
revoke all on public.conversations,public.conversation_participants from anon,authenticated;
grant select,insert on public.conversations,public.conversation_participants to authenticated;
create policy conversations_read on public.conversations for select to authenticated using(owner_id=(select auth.uid()) or private.is_participant(id));
create policy conversations_insert on public.conversations for insert to authenticated with check(owner_id=(select auth.uid()));
create policy participants_read on public.conversation_participants for select to authenticated using(private.is_participant(conversation_id) or exists(select 1 from public.conversations c where c.id=conversation_id and c.owner_id=(select auth.uid())));
create policy participants_insert on public.conversation_participants for insert to authenticated with check(exists(select 1 from public.conversations c where c.id=conversation_id and c.owner_id=(select auth.uid())) and not private.blocked(user_id,(select auth.uid())));
create function private.limit_participants() returns trigger language plpgsql security definer set search_path='' as $$
declare maximum integer; actual integer;
begin
 perform pg_advisory_xact_lock(hashtextextended(new.conversation_id::text,1));
 select case when kind='direct' then 2 else 10 end into maximum from public.conversations where id=new.conversation_id;
 select count(*) into actual from public.conversation_participants where conversation_id=new.conversation_id;
 if actual>=maximum then raise exception 'Conversation is full'; end if;
 return new;
end; $$;
revoke execute on function private.limit_participants() from public,anon,authenticated;
create trigger conversation_limit before insert on public.conversation_participants for each row execute function private.limit_participants();
create table public.messages (
 id uuid primary key default gen_random_uuid(),conversation_id uuid not null references public.conversations(id) on delete cascade,
 sender_id uuid not null references public.profiles(id) on delete cascade,body text not null check(char_length(trim(body)) between 1 and 2000),created_at timestamptz not null default now()
);
create index messages_conversation_idx on public.messages(conversation_id,created_at desc);
create index messages_sender_idx on public.messages(sender_id,created_at desc);
alter table public.messages enable row level security;
revoke all on public.messages from anon,authenticated;
grant select,insert on public.messages to authenticated;
create policy messages_read on public.messages for select to authenticated using(private.is_participant(conversation_id) and not private.blocked(sender_id,(select auth.uid())));
create policy messages_insert on public.messages for insert to authenticated with check(sender_id=(select auth.uid()) and private.is_participant(conversation_id));
create function private.check_message() returns trigger language plpgsql security definer set search_path='' as $$
begin
 perform pg_advisory_xact_lock(hashtextextended(new.sender_id::text,2));
 if exists(select 1 from public.conversation_participants p where p.conversation_id=new.conversation_id and private.blocked(p.user_id,new.sender_id)) then raise exception 'Contact is blocked'; end if;
 if exists(select 1 from public.messages where sender_id=new.sender_id and created_at>now()-interval '1 second') then raise exception 'Please wait before sending again'; end if;
 new.created_at=now();return new;
end; $$;
revoke execute on function private.check_message() from public,anon,authenticated;
create trigger message_check before insert on public.messages for each row execute function private.check_message();
create function public.start_conversation(conversation_title text,recipients uuid[]) returns uuid language plpgsql security invoker set search_path='' as $$
declare cid uuid; recipient uuid;
begin
 if cardinality(recipients) not between 1 and 9 or auth.uid()=any(recipients) then raise exception 'Choose 1–9 other people'; end if;
 insert into public.conversations(owner_id,title,kind) values(auth.uid(),conversation_title,case when cardinality(recipients)=1 then 'direct' else 'group' end) returning id into cid;
 insert into public.conversation_participants(conversation_id,user_id) values(cid,auth.uid());
 foreach recipient in array recipients loop insert into public.conversation_participants(conversation_id,user_id) values(cid,recipient);end loop;
 return cid;
end; $$;
revoke execute on function public.start_conversation(text,uuid[]) from public,anon;
grant execute on function public.start_conversation(text,uuid[]) to authenticated;
commit;
