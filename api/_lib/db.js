// 서버가 기억해야 하는 것(계정·패스키 공개키·일회용 질문)을 저장하는 곳입니다.
// 배포(Vercel)에서는 Supabase에 저장하고, 환경 변수가 없는 개발 환경에서만 메모리에 임시로 둡니다.
// (Vercel 서버 함수는 요청마다 기억을 잃어서 메모리 저장은 배포에서 쓸 수 없습니다.)
import crypto from "node:crypto";

const URL_ = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_SECRET_KEY; // 서버에만 있는 비밀 키: 로그·응답·화면에 절대 내보내지 않습니다
export const usingMemory = !URL_ || !KEY;

const enc = encodeURIComponent;
const nowIso = () => new Date().toISOString();

async function rest(method, path, { body, prefer } = {}) {
  const res = await fetch(`${URL_}/rest/v1/${path}`, {
    method,
    headers: { apikey: KEY, "Content-Type": "application/json", ...(prefer ? { Prefer: prefer } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`db ${method} ${path.split("?")[0]} -> ${res.status}`);
  return text ? JSON.parse(text) : null;
}

// ---- 메모리 (개발·점검용) ----
const mem = {
  accounts: [
    { id: "account-a", label: "계정 A (보안·네트워크)" },
    { id: "account-b", label: "계정 B (커피)" },
  ],
  credentials: [],
  challenges: [],
  sessions: [],
};

export async function getAccount(id) {
  if (usingMemory) return mem.accounts.find((a) => a.id === id) ?? null;
  const rows = await rest("GET", `passkey_accounts?id=eq.${enc(id)}&select=id,label`);
  return rows[0] ?? null;
}

export async function listCredentials(accountId) {
  if (usingMemory) return mem.credentials.filter((c) => c.account_id === accountId).sort((a, b) => a.created_at.localeCompare(b.created_at));
  return rest("GET", `passkey_credentials?account_id=eq.${enc(accountId)}&select=id,credential_id,public_key,counter,transports,name,created_at&order=created_at.asc`);
}

export async function insertCredential(row) {
  if (usingMemory) {
    const r = { id: crypto.randomUUID(), created_at: nowIso(), ...row };
    mem.credentials.push(r);
    return r;
  }
  const rows = await rest("POST", "passkey_credentials", { body: row, prefer: "return=representation" });
  return rows[0];
}

export async function insertChallenge(row) {
  if (usingMemory) {
    mem.challenges.push({ id: crypto.randomUUID(), created_at: nowIso(), used_at: null, ...row });
    return;
  }
  await rest("POST", "passkey_challenges", { body: row });
}

// 일회용 질문 소모: "아직 안 쓴 것, 기한 안, 같은 용도"일 때만 성공하고 그 순간 '사용됨'으로 바꿉니다.
// 한 번의 갱신 명령으로 처리해서, 같은 질문으로 두 번 들어와도 한 번만 통과합니다.
export async function consumeChallenge(challenge, purpose) {
  const now = nowIso();
  if (usingMemory) {
    const c = mem.challenges.find((x) => x.challenge === challenge && x.purpose === purpose && !x.used_at && x.expires_at > now);
    if (!c) return null;
    c.used_at = now;
    return c;
  }
  const rows = await rest(
    "PATCH",
    `passkey_challenges?challenge=eq.${enc(challenge)}&purpose=eq.${enc(purpose)}&used_at=is.null&expires_at=gt.${enc(now)}`,
    { body: { used_at: now }, prefer: "return=representation" }
  );
  return rows[0] ?? null;
}

// 하루 넘은 질문 기록은 지웁니다 (질문 보관 시간이 길어지지 않게)
export async function deleteOldChallenges() {
  const cutoff = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  if (usingMemory) {
    mem.challenges = mem.challenges.filter((c) => c.created_at > cutoff);
    return;
  }
  await rest("DELETE", `passkey_challenges?created_at=lt.${enc(cutoff)}`);
}
