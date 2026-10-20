// GET /api/passkey/list — 로그인한 계정의 패스키 목록(이름·등록 날짜). 다른 계정의 것은 보이지 않습니다.
import { sendJson, methodNotAllowed } from "../_lib/http.js";
import { listCredentials } from "../_lib/db.js";
import { getSessionAccount } from "../_lib/session.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, "GET");
  try {
    const s = await getSessionAccount(req); // 계정은 세션으로만 정함
    if (!s) return sendJson(res, 401, { error: "unauthorized", message: "패스키로 로그인해야 볼 수 있습니다." });
    const rows = await listCredentials(s.id);
    return sendJson(res, 200, {
      account: { id: s.id, label: s.label },
      passkeys: rows.map((c) => ({ id: c.id, name: c.name, created_at: c.created_at, credential_id: c.credential_id })),
    });
  } catch (err) {
    console.error("list failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
