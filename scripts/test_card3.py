#!/usr/bin/env python3
"""카드 3 로컬 점검: 가상 인증기로 로그인·로그아웃 흐름을 실제로 돌려 봅니다. (개발용 서버, 메모리 저장)
결과: evidence/card3/local-test-results.json
"""
import json, os, pathlib, subprocess, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "card3"; OUT.mkdir(parents=True, exist_ok=True)
PORT = 3200; BASE = f"http://localhost:{PORT}"
env = {k: v for k, v in os.environ.items() if not k.startswith("SUPABASE_")}; env["PORT"] = str(PORT)
srv = subprocess.Popen(["node", "scripts/dev-with-probe.mjs"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(1.5)
checks = []
def check(name, ok, detail=""):
    checks.append({"항목": name, "결과": "통과" if ok else "불통과", "내용": detail}); print(("PASS " if ok else "FAIL ") + name, detail)
def probe(): return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT+1}/"))
def http(method, path, body=None, cookie=None, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if cookie: h["Cookie"] = cookie
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method=method, headers=h)
    try:
        r = urllib.request.urlopen(req); return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers

def new_auth(cdp):
    return cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
            "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})["authenticatorId"]

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="ko-KR")
        page = ctx.new_page(); cdp = ctx.new_cdp_session(page); cdp.send("WebAuthn.enable")
        authA = new_auth(cdp)
        bodies = []
        page.on("request", lambda r: bodies.append(("req", r.url, r.post_data or "")) if "/api/" in r.url else None)
        def on_res(r):
            if "/api/" in r.url:
                try: bodies.append(("res", r.url, r.text()))
                except Exception: pass
        page.on("response", on_res)
        page.goto(BASE + "/#private", wait_until="load")
        page.wait_for_function("document.getElementById('vault-status').textContent.includes('401')")

        def register(account, name):
            page.click("#reg > summary") if not page.is_visible("#reg-go") else None
            page.select_option("#reg-account", account); page.fill("#reg-name", name); page.click("#reg-go")
            page.wait_for_function("document.getElementById('reg-msg').textContent.startsWith('등록했습니다') || document.getElementById('reg-msg').classList.contains('err')", timeout=15000)
            return page.inner_text("#reg-msg")
        check("A 등록", register("account-a", "A 가상기기").startswith("등록했습니다"))
        check("B 등록", register("account-b", "B 가상기기").startswith("등록했습니다"))
        creds = cdp.send("WebAuthn.getCredentials", {"authenticatorId": authA})["credentials"]
        by_user = {bytes.fromhex(c["userHandle"]).decode() if False else __import__("base64").b64decode(c["userHandle"]).decode(): c for c in creds}
        check("가상 기기에 A·B 패스키가 각각 있음", set(by_user) == {"account-a", "account-b"}, str(sorted(by_user)))
        def only(account):
            """기기에 해당 계정의 패스키만 남깁니다 (자동 선택으로 로그인 계정을 정하기 위함)"""
            for acct, c in by_user.items():
                cdp.send("WebAuthn.removeCredential", {"authenticatorId": authA, "credentialId": c["credentialId"]}) if acct != account and any(x["credentialId"] == c["credentialId"] for x in cdp.send("WebAuthn.getCredentials", {"authenticatorId": authA})["credentials"]) else None
            have = {x["credentialId"] for x in cdp.send("WebAuthn.getCredentials", {"authenticatorId": authA})["credentials"]}
            if by_user[account]["credentialId"] not in have:
                cdp.send("WebAuthn.addCredential", {"authenticatorId": authA, "credential": by_user[account]})
        only("account-b")
        before = len(bodies)
        page.reload(wait_until="load"); page.wait_for_function("document.getElementById('vault-status').textContent.includes('401')")
        check("로그인 전 화면: 잠김, 비공개 자료 없음", page.is_visible("#vault-locked") and not page.is_visible("#vault-items"))
        check("로그인 화면에 비밀번호 입력칸이 없음", page.locator("input[type=password]").count() == 0)
        page.click("#login-go")
        page.wait_for_function("document.getElementById('login-msg').textContent.startsWith('로그인했습니다') || document.getElementById('login-msg').classList.contains('err')", timeout=15000)
        m1 = page.inner_text("#login-msg")
        check("B 패스키로 로그인 성공", m1.startswith("로그인했습니다") and "계정 B" in m1, m1)
        page.wait_for_selector("#vault-items:not([hidden])")
        txt = page.inner_text("#vault-items")
        check("로그인 후 B의 자료가 보임(커피)", "커피 커뮤니티 경험 정리" in txt and "ALEPH 대형 과제 정리" not in txt)
        tok_shown = page.inner_text("#bar-token")
        check("화면의 토큰은 마스킹됨", "…" in tok_shown and len(tok_shown) < 16, tok_shown)
        cookies = {c["name"]: c for c in ctx.cookies()}
        ck = cookies.get("aleph_session")
        check("세션 쿠키: HttpOnly, SameSite=Strict", ck and ck["httpOnly"] and ck["sameSite"] == "Strict", json.dumps({k: ck[k] for k in ("httpOnly","sameSite","path")}))
        tok = ck["value"]
        check("화면 스크립트는 쿠키를 읽을 수 없음", page.evaluate("document.cookie") == "")
        blob = "".join(b for _, _, b in bodies[before:])
        check("응답·요청 본문 어디에도 토큰 원문이 없음", tok not in blob)
        check("서버 세션 1건(해시 저장)", probe()["sessions"] == 1)

        # 질문이 로그인마다 다름 + 서버 재사용 거절
        login_reqs = [json.loads(b) for k, u, b in bodies[before:] if k == "res" and u.endswith("login-options")]
        c1 = login_reqs[0]["challenge"]
        verify_body = next(b for k, u, b in bodies[before:] if k == "req" and u.endswith("login-verify"))
        s, t, _ = http("POST", "/api/passkey/login-verify", json.loads(verify_body))
        check("같은 로그인 값을 다시 보내면 거절(질문 재사용)", s == 401 and "이미 썼" in t, f"{s} {t[:80]}")

        # 로그아웃
        page.click("#logout-go"); page.wait_for_selector("#vault-locked", state="visible")
        check("로그아웃 후 화면이 다시 잠김", page.is_visible("#vault-locked") and not page.is_visible("#vault-items"))
        check("로그아웃 후 서버 세션 0건", probe()["sessions"] == 0)
        s, t, _ = http("GET", "/api/private/items", cookie=f"aleph_session={tok}")
        check("로그아웃한 옛 토큰으로 요청하면 401", s == 401, f"{s} {t[:60]}")

        # 두 번째 로그인: 질문이 새 값
        page.click("#login-go")
        page.wait_for_function("document.getElementById('login-msg').textContent.startsWith('로그인했습니다')", timeout=15000)
        login_reqs = [json.loads(b) for k, u, b in bodies if k == "res" and u.endswith("login-options")]
        check("로그인할 때마다 질문이 다름", len({x["challenge"] for x in login_reqs}) == len(login_reqs) >= 2, f"{len(login_reqs)}회, 서로 다름")
        tok2 = {c["name"]: c for c in ctx.cookies()}["aleph_session"]["value"]
        check("로그인할 때마다 세션 토큰도 새 값", tok2 != tok)

        # 가짜 값들
        s, t, _ = http("GET", "/api/private/items", cookie="aleph_session=" + "A" * 43)
        check("엉터리 토큰은 401", s == 401)
        s, t, _ = http("GET", "/api/private/items?account=account-a", cookie=f"aleph_session={tok2}")
        check("주소에 다른 계정을 적어도 로그인한 계정(B)의 자료만 옴", s == 200 and "커피" in t and "ALEPH" not in t)
        s, t, _ = http("POST", "/api/passkey/login-verify", {"credential": {"id": "x", "response": {"clientDataJSON": "e30", "authenticatorData": "AA", "signature": "AA"}}})
        check("서버가 낸 적 없는 질문으로 로그인 시도는 401", s == 401)
        s, t, _ = http("POST", "/api/passkey/login-options", {}); s2, t2, _ = http("POST", "/api/passkey/login-options", {})
        check("login-options 응답마다 새 질문", json.loads(t)["challenge"] != json.loads(t2)["challenge"])
        # 만료
        page.screenshot(path=str(OUT / "local-login.png"))
        page.locator("#private").screenshot(path=str(OUT / "local-logged-in.png"))
        browser.close()
finally:
    srv.terminate()

(OUT / "local-test-results.json").write_text(json.dumps({"점검": checks}, ensure_ascii=False, indent=1), encoding="utf-8")
bad = [c for c in checks if c["결과"] != "통과"]
print(f"\n{len(checks)-len(bad)}/{len(checks)} 통과")
