create function public.create_community(community_name text,community_description text,community_topic text) returns uuid language plpgsql security invoker set search_path='' as $$
declare created uuid;
begin
 insert into public.communities(owner_id,name,description,topic) values(auth.uid(),community_name,community_description,community_topic) returning id into created;
 insert into public.memberships(user_id,community_id) values(auth.uid(),created);
 return created;
end; $$;
revoke execute on function public.create_community(text,text,text) from public,anon;
grant execute on function public.create_community(text,text,text) to authenticated;
