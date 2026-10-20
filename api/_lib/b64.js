// base64url (패스키 값은 이 형식으로 주고받습니다)
export const b64uEncode = (buf) => Buffer.from(buf).toString("base64url");
export const b64uDecode = (str) => Buffer.from(String(str), "base64url");
