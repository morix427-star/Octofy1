-- Octofy direct-chat RPC. Run after supabase/schema.sql.
create or replace function public.create_direct_conversation(target_username text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_id uuid;
  current_id uuid := auth.uid();
  new_conversation_id uuid;
begin
  if current_id is null then
    raise exception 'Authentication required';
  end if;

  select p.id into target_id
  from public.profiles p
  where lower(p.username) = lower(target_username)
  limit 1;

  if target_id is null then
    raise exception 'User not found';
  end if;

  if target_id = current_id then
    raise exception 'Cannot start a chat with yourself';
  end if;

  select mine.conversation_id into new_conversation_id
  from public.conversation_members mine
  join public.conversation_members theirs
    on theirs.conversation_id = mine.conversation_id
  join public.conversations c
    on c.id = mine.conversation_id
  where mine.user_id = current_id
    and theirs.user_id = target_id
    and (
      select count(*) from public.conversation_members all_members
      where all_members.conversation_id = mine.conversation_id
    ) = 2
  order by c.created_at desc
  limit 1;

  if new_conversation_id is not null then
    return new_conversation_id;
  end if;

  insert into public.conversations default values
  returning id into new_conversation_id;

  insert into public.conversation_members (conversation_id, user_id)
  values (new_conversation_id, current_id), (new_conversation_id, target_id);

  return new_conversation_id;
end;
$$;

revoke all on function public.create_direct_conversation(text) from public;
grant execute on function public.create_direct_conversation(text) to authenticated;
