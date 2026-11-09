drop policy media_read on public.media;
create policy media_read on public.media for select to authenticated using(owner_id=(select auth.uid()) or exists(select 1 from public.posts p where p.media_id=public.media.id));
alter table private.write_budgets enable row level security;
