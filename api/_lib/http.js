// 요청·응답을 다루는 작은 도우미들입니다.

export function sendJson(res, status, obj) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store"); // 로그인·등록 응답은 어디에도 저장되지 않게
  res.end(JSON.stringify(obj));
}

export function methodNotAllowed(res, allow) {
  res.setHeader("Allow", allow);
  sendJson(res, 405, { error: "method_not_allowed", message: `${allow} 요청만 받습니다.` });
}

// JSON 본문을 읽습니다. (Vercel은 req.body에 미리 풀어 주고, 개발용 서버에서는 직접 읽습니다. 20KB 제한)
export async function readJson(req) {
  if (req.body && typeof req.body === "object" && !Buffer.isBuffer(req.body)) return req.body;
  const chunks = [];
  let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > 20_000) throw Object.assign(new Error("too_large"), { status: 413 });
    chunks.push(c);
  }
  const text = Buffer.concat(chunks).toString("utf8");
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    throw Object.assign(new Error("bad_json"), { status: 400 });
  }
}
