#!/usr/bin/env python3
"""카드 4·5 로컬 점검: 패스키 2개, 목록, 삭제, 삭제한 패스키로 로그인, 마지막 하나 삭제 거절, 다른 계정 삭제·접근 거절.
결과: evidence/card4/local-test-results.json
"""
import base64, json, os, pathlib, subprocess, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "card4"; OUT.mkdir(parents=True, exist_ok=True)
PORT = 3400; BASE = f"http://localhost:{PORT}"
env = {k: v for k, v in os.environ.items() if not k.startswith("SUPABASE_")}; env["PORT"] = str(PORT)
srv = subprocess.Popen(["node", "scripts/dev-with-probe.mjs"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(1.5)
checks = []
def check(name, ok, detail=""):
    checks.append({"항목": name, "결과": "통과" if ok else "불통과", "내용": detail}); print(("PASS " if ok else "FAIL ") + name, detail)
def probe(): return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT+1}/"))
def count(): return {k: len(v) for k, v in probe()["credentials"].items()}
def http(method, path, body=None, cookie=None):
    h = {"Content-Type": "application/json"}
    if cookie: h["Cookie"] = cookie
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method=method, headers=h)
    try:
        r = urllib.request.urlopen(req); return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="ko-KR")
        page = ctx.new_page(); cdp = ctx.new_cdp_session(page); cdp.send("WebAuthn.enable")
        cur = {"id": None}
        def set_auth(kind, cred_list):
            """가상 인증 장치를 하나만 켜 둡니다. kind: internal(이 기기) / usb(보안 키). 같은 장치에는 같은 계정의 패스키가 하나만 들어갈 수 있습니다."""
            if cur["id"]: cdp.send("WebAuthn.removeVirtualAuthenticator", {"authenticatorId": cur["id"]})
            cur["id"] = cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": kind, "hasResidentKey": True,
                            "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})["authenticatorId"]
            for c in cred_list: cdp.send("WebAuthn.addCredential", {"authenticatorId": cur["id"], "credential": c})
        def creds(): return cdp.send("WebAuthn.getCredentials", {"authenticatorId": cur["id"]})["credentials"]
        def uh(c): return base64.b64decode(c["userHandle"]).decode().split(":")[0]
        set_auth("internal", [])
        page.goto(BASE + "/#private", wait_until="load")
        page.wait_for_function("document.getElementById('vault-status').textContent.includes('401')")

        def register(account, name):
            if not page.is_visible("#reg-go"): page.click("#reg > summary")
            if not page.locator("#reg-account").is_disabled(): page.select_option("#reg-account", account)
            page.fill("#reg-name", name); page.click("#reg-go")
            page.wait_for_function("document.getElementById('reg-msg').textContent.startsWith('등록했습니다') || document.getElementById('reg-msg').classList.contains('err')", timeout=15000)
            return page.inner_text("#reg-msg")
        def login():
            page.click("#login-go")
            page.wait_for_function("document.getElementById('login-msg').textContent.startsWith('로그인했습니다') || document.getElementById('login-msg').classList.contains('err') || document.getElementById('login-msg').textContent.startsWith('취소')", timeout=15000)
            return page.inner_text("#login-msg")

        check("A 첫 패스키 등록", register("account-a", "A first").startswith("등록했습니다"))
        check("B 첫 패스키 등록", register("account-b", "B first").startswith("등록했습니다"))
        saved = {uh(c): c for c in creds()}
        a_first = saved["account-a"]; b_first = saved["account-b"]

        # 로그인 B
        set_auth("internal", [b_first])
        check("B로 로그인", "계정 B" in login())
        page.wait_for_selector("#pk-panel:not([hidden])")
        names = page.inner_text("#pk-list")
        check("목록: 이름과 등록 날짜가 보임(1개)", "B first" in names and "등록 20" in names and page.locator("#pk-list li").count() == 1, names.replace("\n", " | "))
        check("로그인한 동안 등록 칸의 계정이 고정됨(선택 불가)", page.locator("#reg-account").is_disabled() and page.input_value("#reg-account") == "account-b")

        # 마지막 하나 삭제 거절
        page.click("#pk-list .vault-btn"); page.click("#pk-list .vault-btn")
        page.wait_for_function("document.getElementById('pk-msg').textContent.length>0")
        msg = page.inner_text("#pk-msg")
        check("마지막 패스키는 삭제 거절(화면 안내)", "마지막" in msg and count()["account-b"] == 1, msg)

        # 같은 계정에 두 번째 패스키: 기기에서 첫 번째 패스키를 치운 상태(=다른 인증 장치)에서 만들고, 첫 번째를 되돌림
        # 같은 기기(이미 B first가 들어 있는 장치)에 이름이 다른 두 번째 패스키를 만듭니다. (사용자 식별값이 달라 덮어쓰지 않음)
        m = register("account-b", "B second")
        check("같은 기기에 패스키가 2개로 따로 저장됨(덮어쓰지 않음)", len([c for c in creds() if uh(c) == "account-b"]) == 2, str(len(creds())))
        check("로그인한 상태에서 두 번째 패스키 추가", m.startswith("등록했습니다"), m)
        b_second = [c for c in creds() if uh(c) == "account-b" and c["credentialId"] != b_first["credentialId"]][0]
        page.wait_for_function("document.querySelectorAll('#pk-list li').length===2")
        names = page.inner_text("#pk-list")
        check("목록: 2개, 이름과 날짜", "B first" in names and "B second" in names, names.replace("\n", " | "))
        check("서버에 B 패스키 2건, A 1건", count() == {"account-a": 1, "account-b": 2}, str(count()))
        page.locator("#private").screenshot(path=str(OUT / "local-two-passkeys.png"))

        # 다른 계정 접근: 로그인한 B가 A의 패스키 id를 지우려는 시도
        cookie = "aleph_session=" + {c["name"]: c for c in ctx.cookies()}["aleph_session"]["value"]
        a_id = probe()["credentials"]["account-a"][0]["id"]
        before = count()
        s, t = http("POST", "/api/passkey/delete", {"id": a_id}, cookie)
        check("B가 A의 패스키를 지우려 하면 404, 개수 그대로", s == 404 and count() == before, f"{s} {t[:70]} / {before} → {count()}")
        s, t = http("GET", "/api/passkey/list?account=account-a", None, cookie)
        lst = json.loads(t)
        check("목록 주소에 A를 적어도 B의 목록만 옴", s == 200 and lst["account"]["id"] == "account-b" and len(lst["passkeys"]) == 2)
        s, t = http("POST", "/api/passkey/delete", {"id": a_id}, None)
        check("로그인 없이 삭제 요청은 401", s == 401)
        s, t = http("POST", "/api/passkey/register-options", {"accountId": "account-a", "name": "x"}, cookie)
        check("로그인한 B가 본문에 account-a를 적어 등록 요청해도 B 계정용 질문(user=account-b)", s == 200 and json.loads(t)["user"]["name"].startswith("account-b"), t[:0])

        # B first 삭제 (화면에서)
        page.locator("#pk-list li", has_text="B first").locator(".vault-btn").click()
        page.locator("#pk-list li", has_text="B first").locator(".vault-btn").click()
        page.wait_for_function("document.querySelectorAll('#pk-list li').length===1")
        check("화면에서 삭제 → 목록 1개, 서버 B 1건", page.inner_text("#pk-list").count("B second") == 1 and count()["account-b"] == 1, page.inner_text("#pk-msg"))

        # 로그아웃 → 삭제된 B first 로 로그인 시도: 실패
        page.click("#logout-go"); page.wait_for_selector("#vault-locked", state="visible")
        set_auth("internal", [b_first])
        m = login()
        check("삭제한 패스키(B first)로 로그인하면 거절", "삭제" in m or "등록되어 있지" in m, m)
        check("거절 후에도 잠김 상태, 자료 요청 401", page.is_visible("#vault-locked") and http("GET", "/api/private/items", None, None)[0] == 401)
        # 남은 B second 로는 로그인 됨
        set_auth("internal", [b_second])
        m = login()
        check("남은 패스키(B second)로 로그인 성공", "계정 B" in m and "B second" in m, m)
        page.wait_for_selector("#vault-items:not([hidden])")
        page.locator("#private").screenshot(path=str(OUT / "local-after-delete-login.png"))
        # 마지막 하나(B second)도 지우려 하면 거절 = 0개가 되지 않음
        cookie = "aleph_session=" + {c["name"]: c for c in ctx.cookies()}["aleph_session"]["value"]
        b_id = probe()["credentials"]["account-b"][0]["id"]
        s, t = http("POST", "/api/passkey/delete", {"id": b_id}, cookie)
        check("마지막 하나 삭제는 409, 0개가 되지 않음", s == 409 and count()["account-b"] == 1, f"{s} {t[:60]}")

        # A로도 로그인해서 자료가 다른지 (카드 5)
        page.click("#logout-go"); page.wait_for_selector("#vault-locked", state="visible")
        set_auth("internal", [a_first]); m = login()
        page.wait_for_selector("#vault-items:not([hidden])")
        txt = page.inner_text("#vault-items")
        check("A로 로그인하면 A의 자료(보안)만 보임", "계정 A" in m and "ALEPH 대형 과제 정리" in txt and "커피" not in txt)
        # A가 B의 패스키를 지우려는 시도
        cookie = "aleph_session=" + {c["name"]: c for c in ctx.cookies()}["aleph_session"]["value"]
        before = count()
        s, t = http("POST", "/api/passkey/delete", {"id": b_id}, cookie)
        check("A가 B의 패스키를 지우려 하면 404, 개수 그대로", s == 404 and count() == before, f"{s}")
        browser.close()
finally:
    srv.terminate()
(OUT / "local-test-results.json").write_text(json.dumps({"점검": checks}, ensure_ascii=False, indent=1), encoding="utf-8")
bad = [c for c in checks if c["결과"] != "통과"]
print(f"\n{len(checks)-len(bad)}/{len(checks)} 통과")
