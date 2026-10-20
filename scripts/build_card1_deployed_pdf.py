#!/usr/bin/env python3
"""배포 주소에서 사람이 직접 확인한 카드 1 결과로 '남길 것' PDF를 만듭니다.

배포 주소는 제 작업 공간에서 직접 요청할 수 없어서, 시크릿 창에서 찍은 화면과
콘솔 확인 스크립트(scripts/check-deployed.js) 결과를 담은 파일을 받아 PDF로 묶습니다.
입력: evidence/card1/deployed/ 아래 deployed-page.png, deployed-api-body.png,
      deployed-console-result.png, console-result.json
출력: evidence/card1/card1-evidence-deployed.pdf
"""
import base64, datetime, html, json, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "evidence" / "card1" / "deployed"
r = json.loads((D / "console-result.json").read_text(encoding="utf-8"))
e = html.escape
b64 = lambda n: base64.b64encode((D / n).read_bytes()).decode()
KST = datetime.timezone(datetime.timedelta(hours=9))
t = datetime.datetime.fromisoformat(r["checked_at_utc"].replace("Z", "+00:00")).astimezone(KST)
ok = r["api_status"] in (401, 403)
rows = [
    ("C13", "공개 영역과 비공개 영역이 화면에서 구분되어 보인다", "통과", "1절: 경계 띠(PUBLIC ▲ / PRIVATE ▼)를 사이에 두고 아래가 비공개 구역"),
    ("C14", "비공개 영역의 항목이 세 개 이상이다", "부분 확인", "서버 자료는 계정마다 3건(저장소 코드 기준). 로그인 후 화면에서 보이는 것은 카드 3 이후에 확인"),
    ("C15", "패스키 없이는 비공개 내용이 화면에 보이지 않는다", "통과" if r["rendered_dom_matches"] == 0 else "불통과", f"1절: 잠금 상태만 보임. 열린 화면에서 비공개 문장 {r['rendered_dom_matches']}건 발견 (검사 {r['scanned_strings']}개)"),
    ("C16", "패스키 없이 서버에 직접 요청하면 거절된다", "통과" if ok else "불통과", f"2절: 쿠키 없는 GET 요청 → {r['api_status']}"),
    ("C17", "그 거절이 401 또는 403이다", "통과" if ok else "불통과", f"2절: 상태 코드 {r['api_status']}"),
    ("C18", "로그인 없이 받은 페이지 소스에 비공개 내용이 없다", "통과" if r["page_source_matches"] == 0 else "불통과", f"3절: 받은 페이지({r['page_source_chars']:,}글자)에서 비공개 문장 {r['page_source_matches']}건 발견 (검사 {r['scanned_strings']}개)"),
]
trs = "".join(f"<tr><td>{a}</td><td>{e(b)}</td><td class='{'ok' if c=='통과' else 'warn'}'>{c}</td><td>{e(d)}</td></tr>" for a, b, c, d in rows)
doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:16mm 15mm; }}
body {{ font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; color:#20231f; font-size:10.5pt; line-height:1.55; }}
h1 {{ font-size:19pt; margin:0 0 4px; }} h2 {{ font-size:13pt; margin:20px 0 6px; border-bottom:2px solid #20231f; padding-bottom:3px; }}
.meta {{ color:#555; font-size:9.5pt; margin-bottom:6px; }}
table {{ border-collapse:collapse; width:100%; font-size:9.5pt; }} th,td {{ border:1px solid #bbb; padding:5px 7px; vertical-align:top; text-align:left; }}
th {{ background:#f0ebe0; }} td.ok {{ color:#0a6b3c; font-weight:700; white-space:nowrap; }} td.warn {{ color:#a14a00; font-weight:700; white-space:nowrap; }}
pre {{ background:#f6f4ee; border:1px solid #cfc7b9; padding:8px 10px; font-size:9pt; white-space:pre-wrap; word-break:break-all; margin:6px 0; font-family:'Noto Sans Mono CJK KR','DejaVu Sans Mono',monospace; }}
img {{ width:100%; border:1px solid #888; }} .cap {{ color:#555; font-size:9pt; margin:4px 0 0; }}
.note {{ background:#fff7e6; border-left:4px solid #d29a77; padding:6px 10px; font-size:9.5pt; margin-top:14px; }}
section {{ break-inside:avoid; }} th.no {{ width:9%; white-space:nowrap; }}
img.tall {{ max-height:150mm; width:auto; max-width:100%; display:block; margin:0 auto; }}
</style></head><body>
<h1>ALEPH 과제 8 · 카드 1 — 남길 것</h1>
<div class="meta">확인 시각(KST): {t.strftime('%Y-%m-%d %H:%M:%S')} · 대상 주소: {e(r['page_url'])} · 환경: Vercel에 배포된 주소 (새 시크릿 창, 로그인 없음)</div>
<div class="meta">이 문서의 내용은 모두 과제용으로 만들어 넣은 것이며, 실제 개인정보와 비밀값(세션·토큰)은 없습니다. 이 단계에는 로그인 수단이 아직 없어 가릴 세션 값도 없습니다.</div>

<section><h2>1. 공개 영역과 비공개 영역을 가른 화면 (C13, C15)</h2>
<img class="tall" src="data:image/png;base64,{b64('deployed-page.png')}" alt="배포 주소의 첫 화면 아래쪽">
<p class="cap">시크릿 창에서 연 배포 주소입니다. 위 갈색 구역이 공개 소개(NOW)의 끝, 가운데 띠가 PUBLIC ▲ / PRIVATE ▼ 경계, 그 아래 사선 구역이 패스키로 잠긴 비공개 자리입니다. 항목 내용은 보이지 않고 “{e(r['screen_status_text'])}”만 표시됩니다.</p></section>

<section><h2>2. 로그인 없이 받은 응답 본문 (C16, C17)</h2>
<table><tr><th style="width:22%">요청</th><td>{e(r['api_request'])}</td></tr>
<tr><th>응답 상태</th><td><b>{r['api_status']}</b> (콘솔: “GET …/api/private/items 401 (Unauthorized)”)</td></tr>
<tr><th>응답 헤더(일부)</th><td>Content-Type: {e(r['api_content_type'])}<br>Cache-Control: {e(r['api_cache_control'])}</td></tr></table>
<p style="margin:8px 0 2px"><b>응답 본문 (그대로)</b></p><pre>{e(r['api_body'])}</pre>
<img src="data:image/png;base64,{b64('deployed-api-body.png')}" alt="시크릿 창에서 API 주소를 직접 연 화면">
<p class="cap">시크릿 창 주소창에 이 주소를 직접 입력해 연 화면입니다. 비공개 자료는 한 글자도 오지 않고 거절 안내만 왔습니다.</p></section>

<section><h2>3. 로그인 없이 받은 페이지 소스에 비공개 내용이 없는지 (C18)</h2>
<table><tr><th style="width:22%">방법</th><td>시크릿 창 콘솔에서 확인 스크립트(scripts/check-deployed.js)를 실행했습니다. 쿠키 없이 첫 화면({e(r['page_url'])})을 다시 받아, 서버가 가진 비공개 자료의 제목·본문 문장 {r['scanned_strings']}개가 들어 있는지 찾았습니다.</td></tr>
<tr><th>받은 페이지</th><td>{r['page_source_chars']:,}글자</td></tr>
<tr><th>일치한 문장</th><td><b>{r['page_source_matches']}건</b> (열린 화면에서도 {r['rendered_dom_matches']}건)</td></tr></table>
<img src="data:image/png;base64,{b64('deployed-console-result.png')}" alt="콘솔 실행 결과">
<p class="cap">콘솔 실행 결과 화면입니다. 위 표의 값은 이 화면에서 옮겨 적었습니다(evidence/card1/deployed/console-result.json).</p></section>

<section><h2>4. 카드 1 통과 기준 대응</h2>
<table><tr><th class="no">번호</th><th>기준</th><th>결과</th><th>근거</th></tr>{trs}</table></section>
<div class="note"><b>이 문서의 범위</b>: 배포 주소에서 사람이 시크릿 창으로 확인한 결과입니다. C14는 서버 자료 건수까지만 확인했고, 로그인 후 화면에서 3개 이상 보이는 것은 카드 3 이후에 확인합니다.</div>
</body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.set_content(doc, wait_until="load")
    pg.pdf(path=str(ROOT / "evidence/card1/card1-evidence-deployed.pdf"), format="A4", print_background=True,
           margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"}); b.close()
print("ok")
