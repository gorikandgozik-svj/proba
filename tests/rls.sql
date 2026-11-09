-- Run in the Supabase SQL editor. All synthetic users and data are rolled back.
begin;
insert into auth.users(id,email) values ('11111111-1111-4111-8111-111111111111','nexus-test-a@example.invalid'),('22222222-2222-4222-8222-222222222222','nexus-test-b@example.invalid');
set local role authenticated;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
insert into public.profiles values ('11111111-1111-4111-8111-111111111111','test_a','Test A','');
insert into public.posts(id,author_id,body) values('33333333-3333-4333-8333-333333333333','11111111-1111-4111-8111-111111111111','Persistent test post');
select set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
insert into public.profiles values ('22222222-2222-4222-8222-222222222222','test_b','Test B','');
insert into public.reactions values('33333333-3333-4333-8333-333333333333','22222222-2222-4222-8222-222222222222');
insert into public.comments(post_id,author_id,body) values('33333333-3333-4333-8333-333333333333','22222222-2222-4222-8222-222222222222','A real comment');
insert into public.follows values('22222222-2222-4222-8222-222222222222','11111111-1111-4111-8111-111111111111');
do $$ begin
 if (select count(*) from public.posts)<>1 or (select count(*) from public.comments)<>1 or (select count(*) from public.reactions)<>1 or (select count(*) from public.follows)<>1 then raise exception 'Social flow failed'; end if;
 update public.profiles set display_name='Hacked' where id='11111111-1111-4111-8111-111111111111';
 if found then raise exception 'Profile RLS failed'; end if;
end $$;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
do $$ begin
 begin
  insert into public.posts(author_id,body) values('22222222-2222-4222-8222-222222222222','Spoof');
  raise exception 'Spoof accepted';
 exception when insufficient_privilege then null;
 end;
 begin
  insert into public.posts(author_id,body) values('11111111-1111-4111-8111-111111111111','Too fast');
  raise exception 'Cooldown not enforced';
 exception when raise_exception then if sqlerrm <> 'Please wait before publishing again' then raise; end if;
 end;
end $$;
reset role;
set local role anon;
do $$ begin
 begin perform * from public.posts; raise exception 'Anonymous data leak'; exception when insufficient_privilege then null; end;
end $$;
rollback;
