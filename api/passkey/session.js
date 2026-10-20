// GET /api/passkey/session — 지금 로그인 상태인지 알려 줍니다. (토큰은 앞 4글자만)
import { sendJson, methodNotAllowed } from "../_lib/http.js";
import { getSessionAccount, maskToken } from "../_lib/session.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, "GET");
  try {
    const s = await getSessionAccount(req);
    if (!s) return sendJson(res, 200, { loggedIn: false });
    return sendJson(res, 200, { loggedIn: true, account: { id: s.id, label: s.label }, token_preview: maskToken(s.token), expires_at: s.session.expires_at });
  } catch (err) {
    console.error("session failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
