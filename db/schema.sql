-- 과제 8 패스키용 표(테이블). Supabase SQL Editor에서 한 번 실행합니다.
-- 이 표들은 서버(Vercel)만 읽고 씁니다. 브라우저에서 직접 읽는 길은 열지 않습니다(접근 제한 RLS를 켜고, 허용 규칙은 만들지 않음).

-- 1) 계정: 비공개 자리를 가진 사람. 두 개(A, B)를 미리 만들어 둡니다.
create table if not exists public.passkey_accounts (
  id          text primary key,              -- 'account-a', 'account-b' (api/_lib/private-data.js 의 계정 키와 같음)
  label       text not null,
  created_at  timestamptz not null default now()
);

-- 2) 패스키: 서버에는 '공개키'만 저장합니다. 개인키는 기기 밖으로 나가지 않으므로 여기에 없습니다.
create table if not exists public.passkey_credentials (
  id             uuid primary key default gen_random_uuid(),
  account_id     text not null references public.passkey_accounts(id) on delete cascade,
  credential_id  text not null unique,       -- 패스키 식별값(공개 정보)
  public_key     text not null,              -- 공개키 (base64url)
  counter        bigint not null default 0,  -- 서명 횟수 (복제된 패스키 감지용)
  transports     text[],
  name           text not null,              -- 사람이 알아볼 수 있는 이름
  created_at     timestamptz not null default now()
);

-- 3) 일회용 질문(challenge): 등록·로그인 때마다 새로 만들고, 한 번 쓰면 다시 못 씁니다.
create table if not exists public.passkey_challenges (
  id          uuid primary key default gen_random_uuid(),
  challenge   text not null unique,
  purpose     text not null check (purpose in ('register', 'login')),
  account_id  text references public.passkey_accounts(id) on delete cascade,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null,
  used_at     timestamptz
);

-- 4) 로그인 세션: 원문 토큰은 저장하지 않고 해시만 저장합니다.
create table if not exists public.passkey_sessions (
  token_hash  text primary key,
  account_id  text not null references public.passkey_accounts(id) on delete cascade,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null
);

-- 접근 제한(RLS)을 켭니다. 허용 규칙(policy)을 만들지 않으므로 브라우저용 키로는 읽고 쓸 수 없고,
-- 서버가 쓰는 비밀 키(secret / service_role)만 통과합니다.
alter table public.passkey_accounts    enable row level security;
alter table public.passkey_credentials enable row level security;
alter table public.passkey_challenges  enable row level security;
alter table public.passkey_sessions    enable row level security;

-- 계정 두 개를 미리 만들어 둡니다.
insert into public.passkey_accounts (id, label) values
  ('account-a', '계정 A (보안·네트워크)'),
  ('account-b', '계정 B (커피)')
on conflict (id) do nothing;

-- 서버 키(service_role)에게만 표 사용 권한을 줍니다.
-- 프로젝트 생성 때 "Automatically expose new tables"를 껐으므로 권한이 자동으로 주어지지 않습니다.
-- 브라우저용 역할(anon, authenticated)에는 주지 않습니다. → 브라우저에서는 이 표를 읽거나 쓸 수 없습니다.
grant usage on schema public to service_role;
grant select, insert, update, delete on
  public.passkey_accounts,
  public.passkey_credentials,
  public.passkey_challenges,
  public.passkey_sessions
to service_role;
