-- Supabase schema for AI Interview Simulator
-- Execute this in Supabase SQL editor once.

-- Users (custom username/password auth; NOT Supabase Auth)
create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    username text unique not null,
    password_hash text not null,
    created_at timestamptz not null default now()
);

-- Saved answers per user per (topic, question index)
create table if not exists public.user_answers (
    id bigserial primary key,
    user_id uuid not null references public.users(id) on delete cascade,
    topic text not null,
    q_index integer not null,
    answer text not null default '',
    evaluation jsonb,
    updated_at timestamptz not null default now(),
    unique (user_id, topic, q_index)
);

-- Current question index per user per topic
create table if not exists public.user_progress (
    user_id uuid not null references public.users(id) on delete cascade,
    topic text not null,
    current_idx integer not null default 0,
    updated_at timestamptz not null default now(),
    primary key (user_id, topic)
);

-- Helpful indexes
create index if not exists idx_user_answers_user_topic
    on public.user_answers (user_id, topic);

-- NOTE: Row Level Security is NOT enabled because we access this DB with the
-- service_role key from the Streamlit backend and do our own auth checks.
-- If you later switch to the anon key + Supabase Auth, enable RLS and add
-- policies restricting access to auth.uid() = user_id.
