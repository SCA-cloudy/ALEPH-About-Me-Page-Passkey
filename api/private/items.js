// GET /api/private/items — 로그인한 사람의 비공개 자료를 돌려줍니다.
// 로그인하지 않았으면 자료를 한 글자도 보내지 않고 401로 거절합니다.
import { getSessionAccount } from "../_lib/session.js";
import { itemsFor } from "../_lib/private-data.js";
import { sendJson, methodNotAllowed } from "../_lib/http.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, "GET");
  try {
    const account = await getSessionAccount(req); // 누구인지는 세션(쿠키)으로만 정한다. 주소·본문의 계정 값은 읽지 않는다.
    if (!account) return sendJson(res, 401, { error: "unauthorized", message: "패스키로 로그인해야 볼 수 있습니다." });
    return sendJson(res, 200, { items: itemsFor(account.id) });
  } catch (err) {
    console.error("items failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
