// POST /api/passkey/register-options  — 패스키 등록 1단계: 서버가 "일회용 질문"을 만들어 브라우저에 줍니다.
// 서버는 이 질문을 DB에 보관해 두었다가, 2단계(register-verify)에서 돌아온 값과 맞는지 확인합니다.
import { sendJson, methodNotAllowed, readJson } from "../_lib/http.js";
import { getAccount, listCredentials, insertChallenge, deleteOldChallenges } from "../_lib/db.js";
import { newChallenge, relyingParty, CHALLENGE_TTL_MS } from "../_lib/webauthn.js";
import { getSessionAccount } from "../_lib/session.js";
import crypto from "node:crypto";
import { b64uEncode } from "../_lib/b64.js";
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
    if (!NAME_RULE(body.name)) return sendJson(res, 400, { error: "bad_name", message: "패스키 이름을 1~40자로 적어 주세요." });

    // 어느 계정에 붙이는지: 로그인 상태라면 '로그인한 계정'만 씁니다. 요청 본문의 값은 로그인 상태일 때 무시합니다.
    const session = await getSessionAccount(req);
    const accountId = session ? session.id : body.accountId;
    const account = typeof accountId === "string" ? await getAccount(accountId) : null;
    if (!account) return sendJson(res, 400, { error: "unknown_account", message: "없는 계정입니다." });

    // 이미 패스키가 있는 계정에는, 그 계정으로 로그인한 사람만 패스키를 더할 수 있습니다.
    const existing = await listCredentials(account.id);
    if (existing.length > 0 && !session) {
      return sendJson(res, 403, { error: "account_already_claimed", message: "이미 패스키가 있는 계정입니다. 로그인한 뒤에 추가해야 합니다." });
    }

    const challenge = newChallenge();
    await deleteOldChallenges();
    await insertChallenge({
      challenge,
      purpose: "register",
      account_id: account.id,
      expires_at: new Date(Date.now() + CHALLENGE_TTL_MS).toISOString(),
    });

    return sendJson(res, 200, {
      challenge,
      rp: { name: "ALEPH 소개 페이지", id: rp.rpID },
      // 사용자 식별값(user.id)을 패스키마다 다르게 만듭니다. 같은 값이면 같은 기기에서 새 패스키가 옛 패스키를 덮어쓰기 때문입니다.
      // 형식: "<계정>:<무작위>". 로그인 때 이 앞부분이 패스키의 계정과 같은지 확인합니다. (이름에는 패스키 이름을 붙여 선택 창에서 구분됨)
      user: { id: b64uEncode(Buffer.from(`${account.id}:${crypto.randomBytes(12).toString("hex")}`)), name: `${account.id} · ${body.name.trim()}`, displayName: `${account.label} · ${body.name.trim()}` },
      pubKeyCredParams: [
        { type: "public-key", alg: -7 }, // ES256
        { type: "public-key", alg: -257 }, // RS256
        { type: "public-key", alg: -8 }, // Ed25519
      ],
      timeout: 60000,
      attestation: "none",
      // excludeCredentials는 쓰지 않습니다: 같은 기기에 이름이 다른 패스키를 하나 더 만들 수 있어야 하기 때문입니다.
      excludeCredentials: [],
      authenticatorSelection: { residentKey: "required", requireResidentKey: true, userVerification: "preferred" },
    });
  } catch (err) {
    console.error("register-options failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
