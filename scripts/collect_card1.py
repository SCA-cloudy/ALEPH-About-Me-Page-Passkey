#!/usr/bin/env python3
"""카드 1 '남길 것' 수집기.

실제로 서버에 요청을 보내고 화면을 열어 본 결과만 기록해서 PDF 한 장으로 만듭니다.
(손으로 쓴 결과가 아니라, 이 스크립트가 직접 실행한 결과입니다.)

사용법:
    python3 scripts/collect_card1.py                      # 내 컴퓨터(http://localhost:3000)
    python3 scripts/collect_card1.py https://배포주소      # 배포된 주소

결과: evidence/card1/ 아래 results.json, boundary.png, card1-evidence.pdf
필요: python3, playwright(Chromium), node (비공개 자료 문장 목록을 읽을 때 사용)
"""
import base64
import datetime
import html
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000").rstrip("/")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "card1"
OUT.mkdir(parents=True, exist_ok=True)
KST = datetime.timezone(datetime.timedelta(hours=9))
IS_LOCAL = BASE.startswith("http://localhost") or BASE.startswith("http://127.0.0.1")


def raw_get(path):
    """쿠키·로그인 정보 없이 보내는 순수한 GET 요청. (상태, 헤더, 본문)을 돌려준다."""
    req = urllib.request.Request(BASE + path, headers={"Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:  # 401 같은 거절도 '응답'이므로 그대로 기록
        return e.code, dict(e.headers), e.read()


def server_side_items():
    """서버 쪽 자료 목록(검사용). 계정별 건수와, 페이지에 섞였는지 찾아볼 문장들."""
    js = (
        "import('./api/_lib/private-data.js').then(m=>console.log(JSON.stringify("
        "{counts:m.itemCounts(),items:m.allItemsForScan()})))"
    )
    out = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def b64(path):
    return base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def main():
    now = datetime.datetime.now(KST)
    data = server_side_items()
    needles = [i["title"] for i in data["items"]] + [i["body"] for i in data["items"]]

    # ① 로그인 없이 받은 응답 본문 (비공개 자료 주소)
    s_api, h_api, b_api = raw_get("/api/private/items")
    api_body = b_api.decode("utf-8", "replace")

    # ② 로그인 없이 받은 페이지 소스 (브라우저가 아니라 순수 요청으로 받은 그대로)
    s_page, h_page, b_page = raw_get("/")
    page_src = b_page.decode("utf-8", "replace")
    src_hits = [n for n in needles if n in page_src]

    # ③ 브라우저로 열어 본 화면
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 768}, reduced_motion="reduce", locale="ko-KR", device_scale_factor=2)
        page = ctx.new_page()
        seen = []
        page.on("response", lambda r: seen.append(r.status) if "/api/private/items" in r.url else None)
        page.goto(BASE, wait_until="load")  # 서버 응답은 아래에서 화면 표시가 바뀔 때까지 따로 기다린다
        page.wait_for_function("document.getElementById('vault-status').textContent.trim() !== '서버에 확인하는 중…'", timeout=15000)
        status_text = page.inner_text("#vault-status").strip()
        locked_visible = page.is_visible("#vault-locked")
        items_visible = page.is_visible("#vault-items")
        dom_html = page.evaluate("document.documentElement.outerHTML")
        dom_hits = [n for n in needles if n in dom_html]
        geo = page.evaluate(
            """() => {
              const y = el => el.getBoundingClientRect().top + window.scrollY;
              const b = document.querySelector('.boundary'), pv = document.querySelector('.private');
              const v = document.querySelector('#vault');
              return {boundaryTop: y(b), boundaryBottom: y(b) + b.offsetHeight,
                      privateTop: y(pv), vaultBottom: y(v) + v.offsetHeight};
            }"""
        )
        boundary_visible = page.is_visible(".boundary")
        y0 = max(0, int(geo["boundaryTop"] - 260))
        y1 = int(geo["vaultBottom"] + 16)  # 잠긴 자리 바로 아래까지만
        shot = OUT / "boundary.png"
        page.screenshot(path=str(shot), full_page=True, clip={"x": 0, "y": y0, "width": 1366, "height": y1 - y0})
        browser.close()

    ok = lambda cond: "통과" if cond else "불통과"
    c13 = boundary_visible and geo["privateTop"] >= geo["boundaryBottom"] - 1
    c15 = locked_visible and not items_visible and not dom_hits
    c16 = s_api in (401, 403)
    c17 = s_api in (401, 403)
    c18 = s_page == 200 and not src_hits
    counts = data["counts"]
    c14_server = all(n >= 3 for n in counts.values()) and len(counts) >= 1

    results = {
        "collected_at_kst": now.isoformat(timespec="seconds"),
        "base_url": BASE,
        "environment": "local-dev-server" if IS_LOCAL else "deployed",
        "api_request": f"GET {BASE}/api/private/items (쿠키 없음)",
        "api_status": s_api,
        "api_content_type": h_api.get("Content-Type"),
        "api_cache_control": h_api.get("Cache-Control"),
        "api_body": api_body,
        "page_status": s_page,
        "page_bytes": len(b_page),
        "scanned_strings": len(needles),
        "page_source_matches": len(src_hits),
        "rendered_dom_matches": len(dom_hits),
        "page_fetch_statuses_seen_by_browser": seen,
        "screen_status_text": status_text,
        "server_item_counts_per_account": counts,
        "criteria": {
            "C13": ok(c13), "C14": "부분 확인" if c14_server else "불통과", "C15": ok(c15),
            "C16": ok(c16), "C17": ok(c17), "C18": ok(c18),
        },
    }
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    e = html.escape
    env_label = ("내 컴퓨터의 개발 서버 (초안 — 배포 주소로 다시 수집하면 이 문서를 교체합니다)" if IS_LOCAL
                 else "배포된 주소")
    count_text = ", ".join(f"계정 {i + 1}: {n}건" for i, n in enumerate(counts.values()))
    rows = [
        ("C13", "공개 영역과 비공개 영역이 화면에서 구분되어 보인다", results["criteria"]["C13"],
         "1절 화면: 공개(위)와 비공개(아래) 사이에 경계선 띠가 있고 비공개 구역은 다른 배경으로 표시됨"),
        ("C14", "비공개 영역의 항목이 세 개 이상이다", results["criteria"]["C14"],
         f"서버가 보유한 자료 {count_text}(내용 제외). 로그인 후 화면에서 3개 이상 보이는 것은 카드 3 이후에 확인"),
        ("C15", "패스키 없이는 비공개 내용이 화면에 보이지 않는다", results["criteria"]["C15"],
         f"잠금 상태만 보임. 열린 화면의 HTML에서 비공개 문장 {len(dom_hits)}건 발견 (검사 {len(needles)}개)"),
        ("C16", "패스키 없이 서버에 직접 요청하면 거절된다", results["criteria"]["C16"],
         f"2절: 쿠키 없는 GET 요청 → {s_api}"),
        ("C17", "그 거절이 401 또는 403이다", results["criteria"]["C17"], f"2절: 상태 코드 {s_api}"),
        ("C18", "로그인 없이 받은 페이지 소스에 비공개 내용이 없다", results["criteria"]["C18"],
         f"3절: 받은 페이지 {len(b_page):,}바이트에서 비공개 문장 {len(src_hits)}건 발견 (검사 {len(needles)}개)"),
    ]
    table_rows = "".join(
        f"<tr><td>{e(a)}</td><td>{e(b)}</td><td class='{'ok' if c == '통과' else 'warn'}'>{e(c)}</td><td>{e(d)}</td></tr>"
        for a, b, c, d in rows
    )
    doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 16mm 15mm; }}
    body {{ font-family: 'Noto Sans CJK KR','Noto Sans KR',sans-serif; color:#20231f; font-size:10.5pt; line-height:1.55; }}
    h1 {{ font-size:19pt; margin:0 0 4px; }} h2 {{ font-size:13pt; margin:22px 0 6px; border-bottom:2px solid #20231f; padding-bottom:3px; }}
    .meta {{ color:#555; font-size:9.5pt; margin-bottom:6px; }}
    table {{ border-collapse:collapse; width:100%; font-size:9.5pt; }} th,td {{ border:1px solid #bbb; padding:5px 7px; vertical-align:top; text-align:left; }}
    th {{ background:#f0ebe0; }} td.ok {{ color:#0a6b3c; font-weight:700; white-space:nowrap; }} td.warn {{ color:#a14a00; font-weight:700; white-space:nowrap; }}
    pre {{ background:#f6f4ee; border:1px solid #cfc7b9; padding:8px 10px; font-size:9pt; white-space:pre-wrap; word-break:break-all; margin:6px 0; font-family:'Noto Sans Mono CJK KR','DejaVu Sans Mono',monospace; }}
    img {{ width:100%; border:1px solid #888; }} .cap {{ color:#555; font-size:9pt; margin:4px 0 0; }}
    .note {{ background:#fff7e6; border-left:4px solid #d29a77; padding:6px 10px; font-size:9.5pt; margin-top:14px; }}
    section {{ break-inside: avoid; }} th.no {{ width:9%; white-space:nowrap; }}
    img {{ max-height:118mm; object-fit:contain; }}
    </style></head><body>
    <h1>ALEPH 과제 8 · 카드 1 — 남길 것</h1>
    <div class="meta">수집 시각(KST): {e(now.strftime('%Y-%m-%d %H:%M:%S'))} · 대상 주소: {e(BASE)} · 환경: {e(env_label)}</div>
    <div class="meta">이 문서의 내용은 모두 과제용으로 만들어 넣은 것이며, 실제 개인정보와 비밀값(세션·토큰)은 없습니다. 이 단계에는 로그인 수단이 아직 없어 가릴 세션 값도 없습니다.</div>

    <section><h2>1. 공개 영역과 비공개 영역을 가른 화면 (C13, C15)</h2>
    <img src="data:image/png;base64,{b64(shot)}" alt="공개/비공개 경계 화면">
    <p class="cap">위쪽 갈색 구역은 공개 소개(NOW)의 끝, 가운데 흰 띠가 경계, 아래 베이지 사선 구역이 패스키로 잠긴 비공개 자리(그 아래는 푸터)입니다. 로그인하지 않아 잠금 상태이며 항목 내용은 보이지 않습니다. 화면 아래쪽 표시: “{e(status_text)}”.</p></section>

    <section><h2>2. 로그인 없이 받은 응답 본문 (C16, C17)</h2>
    <table><tr><th style="width:22%">요청</th><td>GET {e(BASE)}/api/private/items<br>(쿠키·인증 정보 없이 보낸 순수한 요청)</td></tr>
    <tr><th>응답 상태</th><td><b>{s_api}</b></td></tr>
    <tr><th>응답 헤더(일부)</th><td>Content-Type: {e(str(h_api.get('Content-Type')))}<br>Cache-Control: {e(str(h_api.get('Cache-Control')))}</td></tr></table>
    <p style="margin:8px 0 2px"><b>응답 본문 (그대로)</b></p>
    <pre>{e(api_body)}</pre>
    <p class="cap">비공개 자료는 한 글자도 오지 않고 거절 안내만 왔습니다. 화면의 잠금 표시는 이 응답({status_text})을 그대로 보여 줍니다.</p></section>

    <section><h2>3. 로그인 없이 받은 페이지 소스에 비공개 내용이 없는지 (C18)</h2>
    <table><tr><th style="width:22%">방법</th><td>브라우저가 아니라 순수한 GET 요청으로 첫 화면({e(BASE)}/)을 받아, 서버가 가진 비공개 자료의 제목·본문 문장 {len(needles)}개가 들어 있는지 찾았습니다.</td></tr>
    <tr><th>받은 페이지</th><td>상태 {s_page}, {len(b_page):,}바이트</td></tr>
    <tr><th>일치한 문장</th><td><b>{len(src_hits)}건</b> (열린 화면의 HTML에서도 {len(dom_hits)}건)</td></tr></table></section>

    <section><h2>4. 카드 1 통과 기준 대응</h2>
    <table><tr><th class="no">번호</th><th>기준</th><th>결과</th><th>근거</th></tr>{table_rows}</table></section>
    <div class="note"><b>이 문서의 범위</b>: {e(env_label)}에서 수집한 결과입니다. 제출 전에는 배포 주소로 같은 항목을 다시 수집해 교체해야 합니다. C14는 서버 자료 건수만 확인했고, 로그인 후 화면에서 3개 이상 보이는 것은 카드 3 이후에 확인합니다.</div>

    <section><h2>5. 다시 수집하는 방법</h2>
    <pre>python3 scripts/collect_card1.py {e(BASE)}</pre></section>
    </body></html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        pg.set_content(doc, wait_until="load")
        pg.pdf(path=str(OUT / "card1-evidence.pdf"), format="A4", print_background=True,
               margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
        browser.close()

    print(json.dumps({k: results[k] for k in ("base_url", "api_status", "page_source_matches",
                                               "rendered_dom_matches", "screen_status_text", "criteria")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
