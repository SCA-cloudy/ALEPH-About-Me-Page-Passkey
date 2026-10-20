// POST /api/passkey/login-options — 로그인 1단계: 서버가 "일회용 질문"을 새로 만들어 줍니다. (요청마다 새 값)
// 계정 이름이나 비밀번호는 받지 않습니다. 기기가 가진 패스키가 스스로 어느 계정인지 알려 줍니다.
import { sendJson, methodNotAllowed } from "../_lib/http.js";
import { insertChallenge, deleteOldChallenges } from "../_lib/db.js";
import { newChallenge, relyingParty, CHALLENGE_TTL_MS } from "../_lib/webauthn.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, "POST");
  try {
    const rp = relyingParty(req);
    if (!rp) return sendJson(res, 400, { error: "host_not_allowed", message: "허용된 주소에서만 로그인할 수 있습니다." });
    const challenge = newChallenge();
    await deleteOldChallenges();
    await insertChallenge({ challenge, purpose: "login", account_id: null, expires_at: new Date(Date.now() + CHALLENGE_TTL_MS).toISOString() });
    return sendJson(res, 200, { challenge, rpId: rp.rpID, timeout: 60000, userVerification: "preferred", allowCredentials: [] });
  } catch (err) {
    console.error("login-options failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
