// 요청을 보낸 사람이 누구인지 알아내는 자리입니다. (카드 3)
//
// 로그인에 성공하면 서버가 무작위 토큰을 만들어 쿠키로 줍니다. 서버에는 토큰의 '해시'만 저장합니다.
// 이후 요청의 쿠키 토큰을 해시해서 DB에서 찾으면 그것이 '로그인한 계정'입니다.
//
// 중요: 계정은 오직 여기(세션)에서만 정합니다. 주소나 요청 본문에 적힌 계정 이름은 읽지 않습니다.
import crypto from "node:crypto";
import { insertSession, findSession, deleteSession, deleteExpiredSessions, getAccount } from "./db.js";

export const COOKIE = "aleph_session";
export const SESSION_TTL_MS = 8 * 3600 * 1000;

const hash = (token) => crypto.createHash("sha256").update(token).digest("hex");

export function tokenFromRequest(req) {
  const raw = String(req.headers.cookie || "");
  for (const part of raw.split(";")) {
    const i = part.indexOf("=");
    if (i > 0 && part.slice(0, i).trim() === COOKIE) {
      const v = part.slice(i + 1).trim();
      return /^[A-Za-z0-9_-]{20,100}$/.test(v) ? v : null;
    }
  }
  return null;
}

// 화면·기록에 보일 때는 앞 4글자만 보여 줍니다. (토큰 전체는 어디에도 출력하지 않음)
export const maskToken = (token) => (token ? token.slice(0, 4) + "…(" + token.length + "자)" : null);

export async function getSessionAccount(req) {
  const token = tokenFromRequest(req);
  if (!token) return null;
  const s = await findSession(hash(token));
  if (!s) return null;
  const account = await getAccount(s.account_id);
  if (!account) return null;
  return { id: account.id, label: account.label, token, session: s };
}

export async function startSession(accountId) {
  const token = crypto.randomBytes(32).toString("base64url");
  await deleteExpiredSessions();
  await insertSession({ token_hash: hash(token), account_id: accountId, expires_at: new Date(Date.now() + SESSION_TTL_MS).toISOString() });
  return token;
}

export async function endSession(token) {
  if (token) await deleteSession(hash(token));
}

// HttpOnly: 화면의 스크립트는 토큰을 읽을 수 없음 / SameSite=Strict: 다른 사이트가 시킨 요청에는 실리지 않음
export function cookieHeader(token, { secure }) {
  const age = token ? Math.floor(SESSION_TTL_MS / 1000) : 0;
  return `${COOKIE}=${token ?? ""}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${age}${secure ? "; Secure" : ""}`;
}
