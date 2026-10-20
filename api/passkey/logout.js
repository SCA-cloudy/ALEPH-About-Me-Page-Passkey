// POST /api/passkey/logout — 서버에서 세션을 지웁니다. (쿠키만 지우는 것이 아니라 서버 쪽 기록을 지워서, 옛 토큰을 다시 내밀어도 거절됩니다.)
import { sendJson, methodNotAllowed } from "../_lib/http.js";
import { tokenFromRequest, endSession, cookieHeader } from "../_lib/session.js";
import { relyingParty } from "../_lib/webauthn.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, "POST");
  try {
    await endSession(tokenFromRequest(req));
    const rp = relyingParty(req);
    res.setHeader("Set-Cookie", cookieHeader(null, { secure: !!rp && rp.origin.startsWith("https:") }));
    return sendJson(res, 200, { ok: true, message: "로그아웃했습니다. 서버에서 세션을 지웠습니다." });
  } catch (err) {
    console.error("logout failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
