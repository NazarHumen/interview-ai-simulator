-- Supabase schema for AI Interview Simulator
-- Execute this in Supabase SQL editor once.

-- Users (custom username/password auth; NOT Supabase Auth)
create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    username text unique not null,
    password_hash text not null,
    is_admin boolean not null default false,
    created_at timestamptz not null default now()
);

-- In case public.users already exists without is_admin:
alter table public.users add column if not exists is_admin boolean not null default false;

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

-- User stats & daily streak
create table if not exists public.user_stats (
    user_id uuid primary key references public.users(id) on delete cascade,
    streak integer not null default 0,
    last_activity_date date,
    frozen_streak integer not null default 0,
    recovery_progress integer not null default 0,
    xp integer not null default 0,
    level integer not null default 1,
    badges jsonb not null default '[]'::jsonb,
    updated_at timestamptz not null default now()
);

-- Helpful indexes
create index if not exists idx_user_answers_user_topic
    on public.user_answers (user_id, topic);

-- NOTE: Row Level Security is NOT enabled because we access this DB with the
-- service_role key from the Streamlit backend and do our own auth checks.
-- If you later switch to the anon key + Supabase Auth, enable RLS and add
-- policies restricting access to auth.uid() = user_id.
