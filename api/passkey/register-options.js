// POST /api/passkey/register-options  — 패스키 등록 1단계: 서버가 "일회용 질문"을 만들어 브라우저에 줍니다.
// 서버는 이 질문을 DB에 보관해 두었다가, 2단계(register-verify)에서 돌아온 값과 맞는지 확인합니다.
import { sendJson, methodNotAllowed, readJson } from "../_lib/http.js";
import { getAccount, listCredentials, insertChallenge, deleteOldChallenges } from "../_lib/db.js";
import { newChallenge, relyingParty, CHALLENGE_TTL_MS } from "../_lib/webauthn.js";
import { getSessionAccount } from "../_lib/session.js";
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
      user: { id: b64uEncode(Buffer.from(account.id)), name: account.id, displayName: account.label },
      pubKeyCredParams: [
        { type: "public-key", alg: -7 }, // ES256
        { type: "public-key", alg: -257 }, // RS256
        { type: "public-key", alg: -8 }, // Ed25519
      ],
      timeout: 60000,
      attestation: "none",
      // 이미 등록된 패스키가 같은 기기에 또 만들어지지 않게 알려 줍니다.
      excludeCredentials: existing.map((c) => ({ type: "public-key", id: c.credential_id, transports: c.transports ?? undefined })),
      authenticatorSelection: { residentKey: "required", requireResidentKey: true, userVerification: "preferred" },
    });
  } catch (err) {
    console.error("register-options failed:", err.message);
    return sendJson(res, 500, { error: "server_error", message: "서버에서 처리하지 못했습니다." });
  }
}
