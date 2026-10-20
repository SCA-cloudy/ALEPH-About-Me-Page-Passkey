#!/usr/bin/env python3
"""카드 2 로컬 점검: 가상 인증기(Chromium)로 패스키 등록 흐름을 실제로 돌려 봅니다.
개발용 서버(메모리 저장)에서 돌리며, 결과는 evidence/card2/local-test-results.json 에 남습니다.
실행: python3 scripts/test_card2.py
"""
import json, os, pathlib, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "card2"; OUT.mkdir(parents=True, exist_ok=True)
PORT = 3100
BASE = f"http://localhost:{PORT}"
env = {k: v for k, v in os.environ.items() if not k.startswith("SUPABASE_")}
env["PORT"] = str(PORT)
srv = subprocess.Popen(["node", "scripts/dev-with-probe.mjs"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(1.5)

def probe():
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT+1}/"))

results, checks = {}, []
def check(name, ok, detail=""):
    checks.append({"항목": name, "결과": "통과" if ok else "불통과", "내용": detail}); print(("PASS " if ok else "FAIL ") + name, detail)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="ko-KR")
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("WebAuthn.enable")
        auth = cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
                         "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})["authenticatorId"]
        bodies = []  # 이 브라우저가 서버로 보낸 요청 본문과 받은 응답 본문 전부
        page.on("request", lambda r: bodies.append(("req", r.url, r.post_data or "")) if "/api/" in r.url else None)
        def on_res(r):
            if "/api/" in r.url:
                try: bodies.append(("res", r.url, r.text()))
                except Exception: pass
        page.on("response", on_res)
        page.goto(BASE + "/#private", wait_until="load")
        page.wait_for_function("document.getElementById('vault-status').textContent.trim() !== '서버에 확인하는 중…'")

        # 0) 시작 상태
        check("시작: 저장된 패스키 0건", sum(len(v) for v in probe()["credentials"].values()) == 0)
        check("시작: 비공개 자료 주소는 401", page.evaluate("fetch('/api/private/items').then(r=>r.status)") == 401)

        # 1-a) 취소: 기기가 응답하지 않는 상황(= 창을 닫음과 같은 NotAllowedError)에서 서버에 아무것도 저장되지 않는지
        page.click("#reg > summary")
        page.select_option("#reg-account", "account-a")
        page.fill("#reg-name", "취소점검")
        cdp.send("WebAuthn.removeVirtualAuthenticator", {"authenticatorId": auth})
        page.click("#reg-go")
        page.wait_for_function("document.getElementById('reg-msg').textContent.length>0 && !document.getElementById('reg-go').disabled && !document.getElementById('reg-msg').textContent.includes('확인해 주세요')", timeout=70000)
        cancel_msg = page.inner_text("#reg-msg")
        check("취소하면 화면에 안내가 나옴", "취소했습니다" in cancel_msg, cancel_msg)
        check("취소 후 저장된 패스키 0건 (취소로 아무것도 저장되지 않음)", sum(len(v) for v in probe()["credentials"].values()) == 0)
        auth = cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
                         "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})["authenticatorId"]

        # 1-b) 화면에서 계정 A 등록 (이름 붙임)
        page.fill("#reg-name", "점검용 가상 기기 A")
        page.click("#reg-go")
        page.wait_for_function("document.getElementById('reg-msg').textContent.startsWith('등록했습니다') || document.getElementById('reg-msg').classList.contains('err')", timeout=15000)
        msg = page.inner_text("#reg-msg")
        check("화면에서 등록 성공", msg.startswith("등록했습니다"), msg)
        stored_text = page.inner_text("#reg-stored")
        pr = probe()["credentials"]["account-a"]
        check("서버에 패스키 1건 저장, 이름이 붙음", len(pr) == 1 and pr[0]["name"] == "점검용 가상 기기 A", json.dumps(pr, ensure_ascii=False)[:160])
        check("화면에 보인 '서버 저장 값'이 실제 저장된 공개키와 같음", pr and pr[0]["public_key"] in stored_text.replace("\n", ""))
        page.locator("#private").screenshot(path=str(OUT / "local-registered.png"))

        # 2) 가상 인증기가 가진 개인키가 서버 요청·응답 어디에도 없는지
        creds = cdp.send("WebAuthn.getCredentials", {"authenticatorId": auth})["credentials"]
        priv = creds[0]["privateKey"]
        blob = "".join(b for _, _, b in bodies)
        check("개인키 값이 어떤 요청·응답에도 없음", priv not in blob and len(priv) > 50, f"개인키 {len(priv)}자, 오간 본문 {len(blob)}자 검사")
        verify_req = next(b for k, u, b in bodies if k == "req" and u.endswith("register-verify"))
        rk = json.loads(verify_req)
        check("등록 요청 본문의 항목은 공개 정보뿐", sorted(rk["credential"]["response"].keys()) == ["attestationObject", "clientDataJSON", "transports"], str(sorted(rk["credential"]["response"].keys())))

        # 3) 질문이 요청마다 다름
        chs = page.evaluate("""async () => { const out=[]; for (let i=0;i<3;i++){ const r=await fetch('/api/passkey/register-options',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accountId:'account-b',name:'질문확인'+i})}); out.push((await r.json()).challenge);} return out; }""")
        check("등록 요청 3번의 질문이 모두 다름", len(set(chs)) == 3, " / ".join(c[:10] + "…" for c in chs))

        # 4) 같은 질문 재사용 거절 + 취소 시 저장 0 + 나머지 공격
        js = """async (mode) => {
          const b64uToBuf = s => { s=s.replace(/-/g,'+').replace(/_/g,'/'); while(s.length%4) s+='='; const bin=atob(s); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i); return u.buffer; };
          const bufToB64u = b => { const u=new Uint8Array(b); let bin=''; for(const c of u) bin+=String.fromCharCode(c); return btoa(bin).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,''); };
          const post = async (u,b) => { const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); return {status:r.status, data:await r.json()}; };
          const o = (await post('/api/passkey/register-options',{accountId:'account-b',name:'공격점검'})).data;
          const pk = {challenge:b64uToBuf(o.challenge), rp:o.rp, user:{id:b64uToBuf(o.user.id),name:o.user.name,displayName:o.user.displayName}, pubKeyCredParams:o.pubKeyCredParams, attestation:o.attestation, authenticatorSelection:o.authenticatorSelection, excludeCredentials:[]};
          const c = await navigator.credentials.create({publicKey:pk});
          const mk = (cdj) => ({name:'공격점검', credential:{id:c.id, rawId:bufToB64u(c.rawId), type:c.type, response:{clientDataJSON:cdj, attestationObject:bufToB64u(c.response.attestationObject), transports:[]}}});
          const cdj = bufToB64u(c.response.clientDataJSON);
          const parsed = JSON.parse(atob(cdj.replace(/-/g,'+').replace(/_/g,'/')));
          const forged = (patch) => bufToB64u(new TextEncoder().encode(JSON.stringify({...parsed, ...patch})));
          const out = {};
          out.wrong_origin = await post('/api/passkey/register-verify', mk(forged({origin:'https://evil.example'})));
          out.first_ok = await post('/api/passkey/register-verify', mk(cdj));
          out.replay = await post('/api/passkey/register-verify', mk(cdj));
          return out;
        }"""
        # 주의: 위조된 요청(출처 변조)도 질문을 소모하므로 따로 질문을 새로 받아 시험한다
        r = page.evaluate(js, "all")
        # wrong_origin 은 질문을 소모했으므로 first_ok 는 거절되는 것이 정상(질문 1회용) → 따로 정상 흐름을 한 번 더 시험
        check("출처를 바꾼 값은 거절(400)", r["wrong_origin"]["status"] == 400, r["wrong_origin"]["data"].get("error", ""))
        check("한 번 소모된 질문으로 다시 보내면 거절(400)", r["first_ok"]["status"] == 400 and r["first_ok"]["data"].get("error") == "challenge_invalid_or_used", r["first_ok"]["data"].get("error", ""))

        js2 = js.replace("out.wrong_origin = await post('/api/passkey/register-verify', mk(forged({origin:'https://evil.example'})));", "")
        r2 = page.evaluate(js2, "ok")
        check("정상 값은 처음 한 번만 통과(201)", r2["first_ok"]["status"] == 201, str(r2["first_ok"]["status"]))
        check("같은 값을 다시 보내면 거절(400, 이미 쓴 질문)", r2["replay"]["status"] == 400 and r2["replay"]["data"].get("error") == "challenge_invalid_or_used", r2["replay"]["data"].get("error", ""))
        check("계정 B에 패스키 1건만 저장됨(재전송으로 늘지 않음)", len(probe()["credentials"]["account-b"]) == 1)

        # 5) 이미 패스키가 있는 계정에 로그인 없이 또 등록 시도 → 거절
        again = page.evaluate("fetch('/api/passkey/register-options',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accountId:'account-a',name:'침입'})}).then(async r=>({s:r.status,d:await r.json()}))")
        check("패스키가 있는 계정에 로그인 없이 추가 등록 시도는 거절(403)", again["s"] == 403, again["d"].get("error", ""))
        unk = page.evaluate("fetch('/api/passkey/register-options',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accountId:'account-z',name:'x'})}).then(r=>r.status)")
        check("없는 계정은 거절(400)", unk == 400, str(unk))

        # 6) 다른 사이트 이름(Host)으로 온 요청은 거절
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/passkey/register-options", data=json.dumps({"accountId": "account-b", "name": "x"}).encode(), headers={"Host": "evil.example", "Content-Type": "application/json"}, method="POST")
        try: st = urllib.request.urlopen(req).status
        except urllib.error.HTTPError as e: st = e.code
        check("허용되지 않은 주소(Host)로 온 요청은 거절(400)", st == 400, str(st))

        # 7) 이미 패스키가 있는 계정을 화면에서 로그인 없이 시도 → 서버 안내가 보이고 저장은 변하지 않음
        before = probe()["credentials"]
        page.select_option("#reg-account", "account-b")
        page.fill("#reg-name", "중복시도")
        page.click("#reg-go")
        page.wait_for_function("document.getElementById('reg-msg').textContent.includes('이미 패스키가 있는 계정')", timeout=15000)
        check("이미 패스키가 있는 계정을 화면에서 시도하면 서버 안내가 보임", True, page.inner_text("#reg-msg"))
        check("시도 전후 저장된 패스키가 같음(변화 0)", before == probe()["credentials"])
        browser.close()
finally:
    srv.terminate()

(OUT / "local-test-results.json").write_text(json.dumps({"환경": "개발용 서버(메모리 저장) + Chromium 가상 인증기", "점검": checks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
bad = [c for c in checks if c["결과"] != "통과"]
print(f"\n{len(checks) - len(bad)}/{len(checks)} 통과")
sys.exit(1 if bad else 0)
