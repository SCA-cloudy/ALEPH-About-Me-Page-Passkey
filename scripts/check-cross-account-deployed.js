// 배포 주소에서 "다른 계정의 것에 손댈 수 있는가"를 확인하는 스크립트 (일반 Chrome 창에서 사이트를 연 뒤 콘솔에 붙여 넣어 실행)
// 1) 패스키 창에서 확인할 계정을 고르면 로그인합니다. 2) 상대 계정의 패스키 id(uuid)를 물어봅니다. 3) 끝나면 로그아웃합니다.
(async () => {
  const b2u = s => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; const bin = atob(s); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; };
  const u2b = b => { const u = new Uint8Array(b); let bin = ""; for (const c of u) bin += String.fromCharCode(c); return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); };
  const post = async (url, body) => { const r = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }); let d = null; try { d = await r.json(); } catch (e) {} return { status: r.status, body: d }; };
  const get = async url => { const r = await fetch(url, { credentials: "same-origin", cache: "no-store" }); let d = null; try { d = await r.json(); } catch (e) {} return { status: r.status, body: d }; };
  const out = { checked_at_utc: new Date().toISOString(), page_url: location.href };

  const o = (await post("/api/passkey/login-options")).body;
  const c = await navigator.credentials.get({ publicKey: { challenge: b2u(o.challenge), rpId: o.rpId, timeout: o.timeout, userVerification: o.userVerification, allowCredentials: [] } });
  const r = c.response;
  const lg = await post("/api/passkey/login-verify", { credential: { id: c.id, rawId: u2b(c.rawId), type: c.type, response: { clientDataJSON: u2b(r.clientDataJSON), authenticatorData: u2b(r.authenticatorData), signature: u2b(r.signature), userHandle: r.userHandle ? u2b(r.userHandle) : null } } });
  out.login = { status: lg.status, account: lg.body && lg.body.account && lg.body.account.id };
  if (lg.status !== 200) { console.log(JSON.stringify(out, null, 1)); return; }
  const me = lg.body.account.id, other = me === "account-a" ? "account-b" : "account-a";
  const otherId = prompt("지금 로그인한 계정은 " + me + " 입니다. 상대 계정(" + other + ")의 passkey_credentials 행 id(uuid)를 붙여 넣으세요:");
  out.me = me; out.other_account = other;

  const titles = d => d && d.items ? d.items.map(i => i.kind + ": " + i.title) : d;
  const mine = await get("/api/private/items");
  out.my_items = { status: mine.status, titles: titles(mine.body) };
  const viaUrl = await get("/api/private/items?account=" + other + "&accountId=" + other);
  out.items_with_other_account_in_url = { status: viaUrl.status, titles: titles(viaUrl.body), same_as_mine: JSON.stringify(titles(viaUrl.body)) === JSON.stringify(titles(mine.body)) };
  const l0 = await get("/api/passkey/list?account=" + other);
  out.list_with_other_account_in_url = { status: l0.status, account: l0.body && l0.body.account && l0.body.account.id, count: l0.body && l0.body.passkeys && l0.body.passkeys.length };
  const ro = await post("/api/passkey/register-options", { accountId: other, name: "x" });
  out.register_options_with_other_account_in_body = { status: ro.status, user_name_starts_with: ro.body && ro.body.user && ro.body.user.name.split(" ")[0], note: "로그인한 계정으로 만들어져야 함" };
  const del = await post("/api/passkey/delete", { id: otherId, accountId: other });
  out.delete_other_accounts_passkey = { status: del.status, message: del.body && del.body.message };
  const l1 = await get("/api/passkey/list");
  out.my_passkey_count_after = l1.body && l1.body.passkeys && l1.body.passkeys.length;
  const lo = await post("/api/passkey/logout");
  out.logout = lo.status;
  out.items_after_logout = (await get("/api/private/items")).status;
  console.log(JSON.stringify(out, null, 1));
})();
