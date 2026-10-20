// 패스키(WebAuthn) 확인을 하는 곳입니다. 외부 라이브러리 없이 Node 내장 crypto만 씁니다.
// 서버가 하는 일: ① 일회용 질문 만들기 ② 기기가 돌려준 값이 그 질문·이 사이트용인지 확인 ③ 공개키 꺼내기 ④(카드 3) 서명 확인
import crypto from "node:crypto";
import { b64uDecode, b64uEncode } from "./b64.js";
import { decodeCbor } from "./cbor.js";

export const CHALLENGE_TTL_MS = 5 * 60 * 1000; // 질문은 5분 안에 쓰지 않으면 못 씁니다

// 일회용 질문: 예측할 수 없는 난수 32바이트
export function newChallenge() {
  return b64uEncode(crypto.randomBytes(32));
}

// 이 요청이 어느 사이트(주소)로 온 것인지: 패스키는 만든 사이트에서만 쓸 수 있습니다.
export function relyingParty(req) {
  const host = String(req.headers["x-forwarded-host"] || req.headers.host || "").split(",")[0].trim().toLowerCase();
  const hostname = host.replace(/:\d+$/, "");
  const allowed = new Set(
    [process.env.WEBAUTHN_ALLOWED_HOSTS, process.env.VERCEL_PROJECT_PRODUCTION_URL, "aleph-about-me-page-passkey.vercel.app", "localhost"]
      .filter(Boolean)
      .flatMap((s) => String(s).split(","))
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)
  );
  if (!allowed.has(hostname)) return null;
  const local = hostname === "localhost";
  const proto = local ? "http" : "https";
  return { rpID: hostname, origin: `${proto}://${host}` };
}

const FLAG_UP = 0x01; // 사용자가 기기에서 직접 확인했음
const FLAG_AT = 0x40; // 새 패스키 정보 포함

function sha256(buf) {
  return crypto.createHash("sha256").update(buf).digest();
}

function parseClientData(clientDataJSON_b64u) {
  const raw = b64uDecode(clientDataJSON_b64u);
  let data;
  try {
    data = JSON.parse(raw.toString("utf8"));
  } catch {
    throw new Error("clientDataJSON을 읽을 수 없습니다");
  }
  return { raw, data };
}

// 브라우저가 돌려준 clientDataJSON 안의 질문(challenge) 값만 먼저 꺼냅니다. (서버가 보관한 질문을 찾는 데 씀)
export function challengeFromClientData(clientDataJSON_b64u) {
  try {
    const { data } = parseClientData(clientDataJSON_b64u);
    return typeof data.challenge === "string" ? data.challenge : null;
  } catch {
    return null;
  }
}

function parseAuthData(ad) {
  if (ad.length < 37) throw new Error("authenticatorData가 너무 짧습니다");
  const out = { rpIdHash: ad.subarray(0, 32), flags: ad[32], counter: ad.readUInt32BE(33) };
  if (out.flags & FLAG_AT) {
    let off = 37 + 16; // aaguid 16바이트 건너뜀
    const len = ad.readUInt16BE(off);
    off += 2;
    out.credentialId = ad.subarray(off, off + len);
    off += len;
    out.coseKey = decodeCbor(ad, off).value;
  }
  return out;
}

// COSE 공개키 → 표준 공개키(SPKI, DER). 지원: ES256(P-256), RS256, Ed25519
function coseToSpki(cose) {
  if (!(cose instanceof Map)) throw new Error("공개키 형식 오류");
  const kty = cose.get(1);
  let jwk;
  if (kty === 2 && cose.get(-1) === 1) {
    jwk = { kty: "EC", crv: "P-256", x: b64uEncode(cose.get(-2)), y: b64uEncode(cose.get(-3)) };
  } else if (kty === 3) {
    jwk = { kty: "RSA", n: b64uEncode(cose.get(-1)), e: b64uEncode(cose.get(-2)) };
  } else if (kty === 1 && cose.get(-1) === 6) {
    jwk = { kty: "OKP", crv: "Ed25519", x: b64uEncode(cose.get(-2)) };
  } else {
    throw new Error("지원하지 않는 공개키 종류입니다");
  }
  return crypto.createPublicKey({ key: jwk, format: "jwk" }).export({ type: "spki", format: "der" });
}

export function algorithmName(spkiDer) {
  const t = crypto.createPublicKey({ key: spkiDer, format: "der", type: "spki" }).asymmetricKeyType;
  return t === "ec" ? "ES256 (P-256)" : t === "rsa" ? "RS256 (RSA)" : t === "ed25519" ? "Ed25519" : t;
}

// 등록 확인: 서버가 낸 질문 그대로인지, 이 사이트용인지 확인하고 공개키를 꺼냅니다.
export function verifyRegistration({ response, expectedChallenge, expectedOrigin, expectedRpID }) {
  const { data } = parseClientData(response.clientDataJSON);
  if (data.type !== "webauthn.create") throw new Error("등록 요청이 아닙니다");
  if (data.challenge !== expectedChallenge) throw new Error("질문(challenge)이 서버가 낸 값과 다릅니다");
  if (data.origin !== expectedOrigin) throw new Error("다른 사이트에서 만든 패스키입니다");
  if (data.crossOrigin === true) throw new Error("다른 사이트 안에서 만든 요청입니다");

  const att = decodeCbor(b64uDecode(response.attestationObject)).value;
  if (!(att instanceof Map) || !Buffer.isBuffer(att.get("authData"))) throw new Error("attestationObject 형식 오류");
  const auth = parseAuthData(att.get("authData"));
  if (!auth.rpIdHash.equals(sha256(Buffer.from(expectedRpID)))) throw new Error("이 사이트용 패스키가 아닙니다");
  if (!(auth.flags & FLAG_UP)) throw new Error("기기에서 사용자 확인이 없었습니다");
  if (!auth.credentialId || !auth.coseKey) throw new Error("패스키 정보가 없습니다");

  const spki = coseToSpki(auth.coseKey);
  return {
    credentialId: b64uEncode(auth.credentialId),
    publicKey: b64uEncode(spki), // 서버에는 공개키만 저장합니다 (개인키는 기기 밖으로 나오지 않음)
    algorithm: algorithmName(spki),
    counter: auth.counter,
  };
}
