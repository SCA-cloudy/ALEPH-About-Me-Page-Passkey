// 배포 주소에서 로그인 보호를 확인하는 스크립트 (일반 Chrome 창에서 사이트를 연 뒤 개발자도구 콘솔에 붙여 넣어 실행)
// 패스키 창이 두 번 뜹니다. 두 번 모두 같은 계정을 골라 확인해 주세요. 끝나면 로그아웃까지 합니다.
(async () => {
  const b2u = s => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; const bin = atob(s); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; };
  const u2b = b => { const u = new Uint8Array(b); let bin = ""; for (const c of u) bin += String.fromCharCode(c); return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); };
  const post = async (url, body) => { const r = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }); let d = null; try { d = await r.json(); } catch (e) {} return { status: r.status, body: d }; };
  const items = async () => (await fetch("/api/private/items", { credentials: "same-origin", cache: "no-store" })).status;
  const sign = async o => {
    const c = await navigator.credentials.get({ publicKey: { challenge: b2u(o.challenge), rpId: o.rpId, timeout: o.timeout, userVerification: o.userVerification, allowCredentials: [] } });
    const r = c.response;
    return { credential: { id: c.id, rawId: u2b(c.rawId), type: c.type, response: { clientDataJSON: u2b(r.clientDataJSON), authenticatorData: u2b(r.authenticatorData), signature: u2b(r.signature), userHandle: r.userHandle ? u2b(r.userHandle) : null } } };
  };
  const out = { checked_at_utc: new Date().toISOString(), page_url: location.href };
  out.start_items_status = await items();

  // 1) 질문은 요청할 때마다 새 값
  const o1 = (await post("/api/passkey/login-options")).body, o2 = (await post("/api/passkey/login-options")).body;
  out.fresh_challenge_each_time = { first: o1.challenge, second: o2.challenge, different: o1.challenge !== o2.challenge };

  // 2) 서명을 일부러 망가뜨려 보내면 거절 (패스키 창 1회)
  const b1 = await sign(o1);
  const bad = JSON.parse(JSON.stringify(b1)); const s = bad.credential.response.signature; bad.credential.response.signature = s.slice(0, -4) + (s.endsWith("AAAA") ? "BBBB" : "AAAA");
  const r1 = await post("/api/passkey/login-verify", bad);
  out.tampered_signature = { status: r1.status, message: r1.body && r1.body.message };
  out.items_after_tampered = await items();

  // 3) 서버가 낸 적 없는 질문으로 보내면 거절
  const fake = JSON.parse(JSON.stringify(b1));
  const cd = JSON.parse(atob(fake.credential.response.clientDataJSON.replace(/-/g, "+").replace(/_/g, "/") + "==".slice(0, (4 - fake.credential.response.clientDataJSON.length % 4) % 4)));
  cd.challenge = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
  fake.credential.response.clientDataJSON = btoa(JSON.stringify(cd)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const r2 = await post("/api/passkey/login-verify", fake);
  out.unissued_challenge = { status: r2.status, message: r2.body && r2.body.message };

  // 4) 정상 로그인 → 같은 값을 다시 보내면 거절 (패스키 창 1회 더)
  const o3 = (await post("/api/passkey/login-options")).body;
  const b3 = await sign(o3);
  const ok1 = await post("/api/passkey/login-verify", b3);
  out.valid_login = { status: ok1.status, account: ok1.body && ok1.body.account && ok1.body.account.label, token_preview: ok1.body && ok1.body.session && ok1.body.session.token_preview };
  out.items_after_login = await items();
  const ok2 = await post("/api/passkey/login-verify", b3);
  out.replay_same_login_value = { status: ok2.status, message: ok2.body && ok2.body.message };

  // 5) 로그아웃 → 비공개 자료 요청은 다시 401
  const lo = await post("/api/passkey/logout");
  out.logout = { status: lo.status };
  out.items_after_logout = await items();
  console.log(JSON.stringify(out, null, 1));
})();
