// POST /api/passkey/register-verify  — 패스키 등록 2단계: 기기가 질문에 답해 돌려준 값을 확인하고 '공개키만' 저장합니다.
import { sendJson, methodNotAllowed, readJson } from "../_lib/http.js";
import { getAccount, listCredentials, insertCredential, consumeChallenge } from "../_lib/db.js";
import { challengeFromClientData, relyingParty, verifyRegistration } from "../_lib/webauthn.js";
import { getSessionAccount } from "../_lib/session.js";
import { NAME_RULE } from "../_lib/rules.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, "POST");
  try {
    const rp = relyingParty(req);
    if (!rp) return sendJson(res, 400, { error: "host_not_allowed", message: "허용된 주소에서만 등록할 수 있습니다." });

    let body;
    try {
      body = await readJson(req);
    } catch (e) {
      return sendJson(res, e.status ?? 400, { error: e.message });
    }
    const resp = body?.credential?.response;
    if (!resp || typeof resp.clientDataJSON !== "string" || typeof resp.attestationObject !== "string") {
      return sendJson(res, 400, { error: "bad_request", message: "등록 값이 올바르지 않습니다." });
    }
    if (!NAME_RULE(body.name)) return sendJson(res, 400, { error: "bad_name", message: "패스키 이름을 1~40자로 적어 주세요." });

    // 돌아온 값 속 질문을 서버가 보관한 것과 대조하고, 그 순간 '사용됨'으로 바꿉니다. (이미 썼거나 기한이 지났으면 여기서 거절)
    const asked = challengeFromClientData(resp.clientDataJSON);
    const row = asked ? await consumeChallenge(asked, "register") : null;
    if (!row) {
      return sendJson(res, 400, { error: "challenge_invalid_or_used", message: "이 질문은 이미 썼거나 기한이 지났거나, 서버가 낸 적이 없는 값입니다." });
    }

    // 계정은 '서버가 그 질문을 낼 때 정한 계정'만 씁니다. 요청 본문의 계정 값은 보지 않습니다.
    const account = await getAccount(row.account_id);
    const session = await getSessionAccount(req);
    const existing = await listCredentials(row.account_id);
    if (!account || (existing.length > 0 && (!session || session.id !== row.account_id))) {
      return sendJson(res, 403, { error: "account_already_claimed", message: "이미 패스키가 있는 계정입니다. 로그인한 뒤에 추가해야 합니다." });
    }

    let info;
    try {
      info = verifyRegistration({ response: resp, expectedChallenge: row.challenge, expectedOrigin: rp.origin, expectedRpID: rp.rpID });
    } catch (e) {
      return sendJson(res, 400, { error: "verification_failed", message: `패스키를 확인하지 못했습니다: ${e.message}` });
    }
    if (body.credential.id && body.credential.id !== info.credentialId) {
      return sendJson(res, 400, { error: "verification_failed", message: "패스키 식별값이 맞지 않습니다." });
    }
    if (existing.some((c) => c.credential_id === info.credentialId)) {
      return sendJson(res, 409, { error: "already_registered", message: "이미 등록된 패스키입니다." });
    }

    const transports = Array.isArray(resp.transports) ? resp.transports.filter((t) => typeof t === "string").slice(0, 6) : null;
    const saved = await insertCredential({
      account_id: account.id,
      credential_id: info.credentialId,
      public_key: info.publicKey,
      counter: info.counter,
      transports,
      name: body.name.trim(),
    });

    // 응답에는 '서버에 저장된 값'만 담습니다. 이것이 공개키이며 비밀번호도 개인키도 아닙니다.
    return sendJson(res, 201, {
      ok: true,
      account: { id: account.id, label: account.label },
      stored: {
        name: saved.name,
        created_at: saved.created_at,
        credential_id: saved.credential_id,
        public_key: saved.public_key,
        algorithm: info.algorithm,
        counter: saved.counter,
      },
      note: "서버에는 위 공개키만 저장됩니다. 개인키는 이 기기 안에 남고 서버로 오지 않습니다.",
    });
  } catch (err) {
    console.error("register-verify failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
