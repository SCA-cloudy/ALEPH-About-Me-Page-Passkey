// GET /api/private/items — 로그인한 사람의 비공개 자료를 돌려줍니다.
// 로그인하지 않았으면 자료를 한 글자도 보내지 않고 401로 거절합니다.
import { getSessionAccount } from "../_lib/session.js";
import { itemsFor } from "../_lib/private-data.js";

function sendJson(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store"); // 비공개 응답이 중간에 저장되지 않게
  res.end(JSON.stringify(body));
}

export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return sendJson(res, 405, { error: "method_not_allowed" });
  }

  const account = getSessionAccount(req); // 누구인지는 세션으로만 정한다
  if (!account) {
    return sendJson(res, 401, { error: "unauthorized", message: "패스키로 로그인해야 볼 수 있습니다." });
  }

  return sendJson(res, 200, { items: itemsFor(account.id) });
}
