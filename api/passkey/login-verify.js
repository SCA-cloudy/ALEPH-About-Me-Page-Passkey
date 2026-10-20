// POST /api/passkey/login-verify — 로그인 2단계: 기기의 서명을 저장된 공개키로 확인하고, 맞으면 세션을 시작합니다.
import { sendJson, methodNotAllowed, readJson } from "../_lib/http.js";
import { getAccount, getCredentialById, consumeChallenge, updateCounter } from "../_lib/db.js";
import { challengeFromClientData, relyingParty, verifyAuthentication } from "../_lib/webauthn.js";
import { startSession, cookieHeader, maskToken } from "../_lib/session.js";
import { b64uDecode } from "../_lib/b64.js";

const fail = (res, message) => sendJson(res, 401, { error: "login_failed", message });

export default async function handler(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, "POST");
  try {
    const rp = relyingParty(req);
    if (!rp) return sendJson(res, 400, { error: "host_not_allowed", message: "허용된 주소에서만 로그인할 수 있습니다." });

    let body;
    try {
      body = await readJson(req);
    } catch (e) {
      return sendJson(res, e.status ?? 400, { error: e.message });
    }
    const c = body?.credential;
    const r = c?.response;
    if (!r || typeof c.id !== "string" || ["clientDataJSON", "authenticatorData", "signature"].some((k) => typeof r[k] !== "string")) {
      return sendJson(res, 400, { error: "bad_request", message: "로그인 값이 올바르지 않습니다." });
    }

    // 1) 돌아온 값 속 질문이 서버가 낸 것이고 아직 안 쓴 것인지: 확인과 동시에 '사용됨'으로 바꿉니다. (같은 값을 다시 보내면 여기서 거절)
    const asked = challengeFromClientData(r.clientDataJSON);
    const row = asked ? await consumeChallenge(asked, "login") : null;
    if (!row) return fail(res, "이 질문은 이미 썼거나 기한이 지났거나, 서버가 낸 적이 없는 값입니다.");

    // 2) 이 패스키가 서버에 등록돼 있는지 (삭제된 패스키는 여기서 거절)
    const cred = await getCredentialById(c.id);
    if (!cred) return fail(res, "등록되어 있지 않은(또는 삭제된) 패스키입니다.");
    const account = await getAccount(cred.account_id);
    if (!account) return fail(res, "계정을 찾지 못했습니다.");

    // 3) 기기가 알려 준 사용자 값이 있으면 이 패스키의 계정과 같아야 합니다.
    if (typeof r.userHandle === "string" && r.userHandle !== "" && b64uDecode(r.userHandle).toString("utf8") !== cred.account_id) {
      return fail(res, "패스키의 계정 정보가 맞지 않습니다.");
    }

    // 4) 서명 확인
    let result;
    try {
      result = verifyAuthentication({ response: r, expectedChallenge: row.challenge, expectedOrigin: rp.origin, expectedRpID: rp.rpID, publicKey: cred.public_key, storedCounter: Number(cred.counter) });
    } catch (e) {
      return fail(res, `서명을 확인하지 못했습니다: ${e.message}`);
    }
    await updateCounter(cred.id, result.counter);

    // 5) 세션 시작: 토큰은 쿠키로만 주고, 응답 본문에는 앞 4글자만 보여 줍니다.
    const token = await startSession(account.id);
    res.setHeader("Set-Cookie", cookieHeader(token, { secure: rp.origin.startsWith("https:") }));
    return sendJson(res, 200, {
      ok: true,
      account: { id: account.id, label: account.label },
      passkey: { name: cred.name },
      session: { token_preview: maskToken(token), expires_in_hours: 8, where: "HttpOnly 쿠키(화면 스크립트는 읽을 수 없음), 서버에는 해시만 저장" },
      counter: result.counter,
    });
  } catch (err) {
    console.error("login-verify failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
