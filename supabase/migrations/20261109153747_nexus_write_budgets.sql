begin;
revoke update on public.follows,public.reactions from authenticated;
drop policy reactions_read on public.reactions;
create policy reactions_read on public.reactions for select to authenticated using(not private.blocked(user_id,(select auth.uid())) and exists(select 1 from public.posts p where p.id=post_id));
-- Durable per-account budgets apply equally to the UI and direct Data API clients.
create table private.write_budgets(user_id uuid not null references auth.users(id) on delete cascade,action text not null,window_start timestamptz not null,used integer not null,primary key(user_id,action));
revoke all on private.write_budgets from public,anon,authenticated;
create function private.consume_budget(action_name text,maximum integer) returns boolean language plpgsql security definer set search_path='' as $$
declare used_count integer; actor uuid=auth.uid();
begin
 if actor is null then raise exception 'Authentication required'; end if;
 insert into private.write_budgets(user_id,action,window_start,used) values(actor,action_name,date_trunc('minute',now()),1)
 on conflict(user_id,action) do update set window_start=excluded.window_start,used=case when private.write_budgets.window_start=excluded.window_start then private.write_budgets.used+1 else 1 end returning used into used_count;
 if used_count>maximum then raise exception 'Rate limit reached. Please wait a minute.'; end if;
 return true;
end; $$;
revoke execute on function private.consume_budget(text,integer) from public,anon;
grant execute on function private.consume_budget(text,integer) to authenticated;
create function private.limit_writes() returns trigger language plpgsql security definer set search_path='' as $$
begin
 perform private.consume_budget(tg_table_name,case tg_table_name when 'communities' then 3 when 'conversations' then 5 when 'media' then 5 when 'reports' then 5 when 'blocks' then 10 when 'profiles' then 10 else 30 end);return new;
end; $$;
revoke execute on function private.limit_writes() from public,anon,authenticated;
create trigger profiles_budget before insert or update on public.profiles for each row execute function private.limit_writes();
create trigger communities_budget before insert on public.communities for each row execute function private.limit_writes();
create trigger conversations_budget before insert on public.conversations for each row execute function private.limit_writes();
create trigger media_budget before insert on public.media for each row execute function private.limit_writes();
create trigger reports_budget before insert on public.reports for each row execute function private.limit_writes();
create trigger blocks_budget before insert on public.blocks for each row execute function private.limit_writes();
create trigger reactions_budget before insert on public.reactions for each row execute function private.limit_writes();
create trigger follows_budget before insert on public.follows for each row execute function private.limit_writes();
create trigger memberships_budget before insert on public.memberships for each row execute function private.limit_writes();
create trigger bookmarks_budget before insert on public.bookmarks for each row execute function private.limit_writes();
create trigger hidden_budget before insert on public.hidden_posts for each row execute function private.limit_writes();
drop policy nexus_upload on storage.objects;
create policy nexus_upload on storage.objects for insert to authenticated with check(bucket_id='nexus-media' and (storage.foldername(name))[1]=(select auth.uid())::text and private.consume_budget('storage_upload',5));
commit;
