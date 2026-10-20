// POST /api/passkey/delete {id} — 로그인한 계정의 패스키 하나를 지웁니다.
// 규칙: ① 로그인한 계정의 패스키만 지울 수 있음(남의 것은 "없다"고 답함) ② 계정의 마지막 하나는 지울 수 없음
//   (마지막을 지우면 아무도 그 계정에 들어갈 수 없게 되고, 주인 없는 계정이 되어 아무나 먼저 등록할 수 있게 되기 때문)
import { sendJson, methodNotAllowed, readJson } from "../_lib/http.js";
import { listCredentials, deleteCredential } from "../_lib/db.js";
import { getSessionAccount } from "../_lib/session.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, "POST");
  try {
    const s = await getSessionAccount(req);
    if (!s) return sendJson(res, 401, { error: "unauthorized", message: "패스키로 로그인해야 지울 수 있습니다." });
    let body;
    try {
      body = await readJson(req);
    } catch (e) {
      return sendJson(res, e.status ?? 400, { error: e.message });
    }
    if (typeof body.id !== "string" || !/^[0-9a-f-]{36}$/i.test(body.id)) return sendJson(res, 400, { error: "bad_request", message: "지울 패스키를 알려 주세요." });

    const mine = await listCredentials(s.id);
    const target = mine.find((c) => c.id === body.id);
    // 남의 패스키이거나 없는 값이면 똑같이 404: 다른 계정에 그런 패스키가 있는지도 알려 주지 않습니다.
    if (!target) return sendJson(res, 404, { error: "not_found", message: "이 계정에는 그런 패스키가 없습니다." });
    if (mine.length <= 1) {
      return sendJson(res, 409, { error: "last_passkey", message: "계정의 마지막 패스키는 지울 수 없습니다. 먼저 다른 패스키를 하나 더 만들어 주세요." });
    }
    const gone = await deleteCredential(s.id, target.id); // 지울 때도 계정 조건을 한 번 더 겁니다
    if (!gone) return sendJson(res, 404, { error: "not_found", message: "이 계정에는 그런 패스키가 없습니다." });
    return sendJson(res, 200, { ok: true, deleted: { name: target.name }, remaining: mine.length - 1 });
  } catch (err) {
    console.error("delete failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
