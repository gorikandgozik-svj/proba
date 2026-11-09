-- Reject unauthorized callers before privileged checks, avoiding activity side channels.
create or replace function private.check_message() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.sender_id is distinct from auth.uid() or not private.is_participant(new.conversation_id) then raise insufficient_privilege using message='Conversation unavailable'; end if;
 perform pg_advisory_xact_lock(hashtextextended(new.sender_id::text,2));
 if exists(select 1 from public.conversation_participants p where p.conversation_id=new.conversation_id and private.blocked(p.user_id,new.sender_id)) then raise exception 'Contact is blocked'; end if;
 if exists(select 1 from public.messages where sender_id=new.sender_id and created_at>now()-interval '1 second') then raise exception 'Please wait before sending again'; end if;
 new.created_at=now();return new;
end; $$;
create or replace function private.limit_participants() returns trigger language plpgsql security definer set search_path='' as $$
declare maximum integer; actual integer;
begin
 if not exists(select 1 from public.conversations where id=new.conversation_id and owner_id=auth.uid()) then raise insufficient_privilege using message='Conversation unavailable'; end if;
 perform pg_advisory_xact_lock(hashtextextended(new.conversation_id::text,1));
 select case when kind='direct' then 2 else 10 end into maximum from public.conversations where id=new.conversation_id;
 select count(*) into actual from public.conversation_participants where conversation_id=new.conversation_id;
 if actual>=maximum then raise exception 'Conversation is full'; end if;
 return new;
end; $$;
