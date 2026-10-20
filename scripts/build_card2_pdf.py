#!/usr/bin/env python3
"""카드 2 '남길 것' PDF: 배포 주소에서 사람이 직접 확인한 화면·DB 캡처·기록을 묶습니다.
입력: evidence/card2/deployed/ (캡처 png, 기록 json), evidence/card2/local-test-results.json
출력: evidence/card2/card2-evidence-deployed.pdf
"""
import base64, html, json, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "evidence" / "card2" / "deployed"
e = html.escape
img = lambda n: base64.b64encode(((ROOT / "evidence" / "card4" / "deployed" / n[3:]) if n.startswith("C4:") else (D / n)).read_bytes()).decode()
local = json.loads((ROOT / "evidence" / "card2" / "local-test-results.json").read_text(encoding="utf-8"))
n_ok = sum(1 for c in local["점검"] if c["결과"] == "통과"); n_all = len(local["점검"])
log_b = (D / "log-register-B.json").read_text(encoding="utf-8").strip()
log_c = (D / "log-cancel.json").read_text(encoding="utf-8").strip()

rows = [
    ("C19", "서버가 등록용 질문(challenge)을 만들어 보내고, 확인할 때까지 보관한다", "통과", "2절: 응답에 질문이 오고, 같은 값이 DB 표 passkey_challenges에 보관됨"),
    ("C20", "등록 요청마다 질문 값이 서로 다르다는 기록이 있다", "통과", "2절: 세 번의 요청이 서로 다른 질문(bMXFGuMo4H… / oEhA2mfA7c… / 2RkvKdWC9m…)"),
    ("C21", "등록이 끝나면 서버에 공개키가 저장된다", "통과", "3절: passkey_credentials에 계정 A, B 각 1건(공개키)"),
    ("C22", "서버에 저장된 값이 있고, 그 값이 공개키이며 비밀번호가 아니라는 설명이 있다", "통과", "3절: 저장된 열과 설명(공개키 값, 비밀번호·개인키 열 없음), 3-1절: 패스키 목록 화면"),
    ("C23", "개인키가 서버로 전송되지 않는다는 사실이 등록 요청 본문 기록으로 확인된다", "통과", "4절: 요청 본문 항목 6개(개인키 없음), 개인키는 기기에 남음"),
    ("C24", "등록한 패스키에 사람이 알아볼 수 있는 이름이 붙는다", "통과", "3절: `A 1st passkey`, `B 1st passkey`"),
    ("C25", "등록 도중 취소하면 화면에 안내가 나오고 서버에 아무것도 저장되지 않는다", "통과", "5절: 취소 안내 화면·기록, 취소 직후 passkey_credentials 0건"),
    ("C26", "패스키를 저장한 곳이 어디인지가 제출문에 적혀 있다", "통과", "6절: Google 비밀번호 관리자(기기 쪽), 서버에는 공개키만"),
]
trs = "".join(f"<tr><td>{a}</td><td>{e(b)}</td><td class='ok'>{c}</td><td>{e(d)}</td></tr>" for a, b, c, d in rows)

doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:16mm 15mm; }}
body {{ font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; color:#20231f; font-size:10pt; line-height:1.55; }}
h1 {{ font-size:19pt; margin:0 0 4px; }} h2 {{ font-size:12.5pt; margin:20px 0 6px; border-bottom:2px solid #20231f; padding-bottom:3px; }}
.meta {{ color:#555; font-size:9pt; margin-bottom:5px; }}
table {{ border-collapse:collapse; width:100%; font-size:9pt; }} th,td {{ border:1px solid #bbb; padding:4px 6px; vertical-align:top; text-align:left; }}
th {{ background:#f0ebe0; }} td.ok {{ color:#0a6b3c; font-weight:700; white-space:nowrap; }} th.no {{ width:7%; }}
pre {{ background:#f6f4ee; border:1px solid #cfc7b9; padding:6px 8px; font-size:7.6pt; white-space:pre-wrap; word-break:break-all; margin:5px 0; font-family:'Noto Sans Mono CJK KR','DejaVu Sans Mono',monospace; line-height:1.35; }}
img {{ width:100%; border:1px solid #888; display:block; }} .cap {{ color:#555; font-size:8.6pt; margin:3px 0 8px; }}
.note {{ background:#fff7e6; border-left:4px solid #d29a77; padding:5px 9px; font-size:9pt; margin:10px 0; }}
section {{ break-inside:avoid-page; }} ul {{ margin:4px 0 4px 18px; padding:0; }} li {{ margin:1px 0; }}
</style></head><body>
<h1>ALEPH 과제 8 · 카드 2 — 남길 것</h1>
<div class="meta">확인 주소: https://aleph-about-me-page-passkey.vercel.app/ · 확인 시각(KST): 2026-10-20 15:06~16:00 · 확인한 사람: 본인(일반 Chrome 창에서 직접 등록)</div>
<div class="meta">이 문서의 내용은 모두 과제용으로 만든 것이며, 실제 개인정보와 비밀값은 없습니다. 패스키 저장 창에 보이는 계정 이메일은 담지 않았습니다.</div>

<section><h2>1. 등록이 이뤄지는 순서</h2>
<ul>
<li><b>① 질문 요청</b>: 브라우저가 서버에 “계정 A에 패스키를 만들고 싶다”고 알리면, 서버가 <b>일회용 질문(challenge)</b>을 새로 만들어 DB에 보관하고 브라우저에 줍니다. (POST /api/passkey/register-options)</li>
<li><b>② 기기가 답함</b>: 기기가 질문에 답하면서 <b>열쇠 한 쌍을 만듭니다.</b> 개인키는 기기(Google 비밀번호 관리자)에 남고, 공개키와 서명만 서버로 갑니다.</li>
<li><b>③ 서버 확인·저장</b>: 서버는 돌아온 질문이 자기가 낸 값인지, 아직 안 쓴 것인지, 이 사이트용인지 확인한 뒤 <b>공개키만</b> 저장합니다. 질문은 그 순간 “사용됨”이 되어 다시 못 씁니다. (POST /api/passkey/register-verify)</li>
</ul></section>

<section><h2>2. 서버가 낸 질문과 보관 (C19, C20)</h2>
<img src="data:image/png;base64,{img('db-challenges-3rows.png')}" alt="passkey_challenges 표">
<p class="cap">DB 표 passkey_challenges(Supabase, 서버만 읽을 수 있는 표)입니다. 세 번의 요청에 질문이 <b>모두 다른 값</b>입니다. 쓴 두 건(계정 A 등록, 계정 B 등록)은 used_at에 시각이 찍혀 다시 못 쓰고, 맨 위 한 건(취소한 시도)은 NULL이라 쓰이지 않았습니다. 질문은 만든 뒤 5분이 지나면(expires_at) 못 씁니다.</p></section>

<section><h2>3. 등록 결과와 서버에 저장된 값 (C21, C22, C24)</h2>
<img src="data:image/png;base64,{img('db-credentials-2rows.png')}" alt="passkey_credentials 표">
<p class="cap">DB 표 passkey_credentials: 계정 A와 B에 각각 이름 붙은 패스키가 1건씩 저장됐습니다.</p>
<table><tr><th style="width:24%">저장된 열</th><th>뜻</th></tr>
<tr><td>account_id</td><td>어느 계정의 패스키인지 (account-a, account-b)</td></tr>
<tr><td>name</td><td>사람이 알아볼 이름 (<b>A 1st passkey</b>, <b>B 1st passkey</b>)</td></tr>
<tr><td>credential_id</td><td>패스키 식별값(공개 정보)</td></tr>
<tr><td>public_key</td><td><b>공개키</b>(ES256, P-256). 서명이 맞는지 확인하는 데만 쓰이며, 이것으로 로그인할 수는 없습니다. 비밀번호가 아닙니다.</td></tr>
<tr><td>counter, transports, created_at</td><td>서명 횟수, 연결 방식, 등록 날짜</td></tr></table>
<p class="cap">비밀번호 열도, 개인키 열도 없습니다. 개인키는 서버로 오지 않기 때문입니다.</p>
<img src="data:image/png;base64,{img('page-register-A.png')}" alt="계정 A 등록 직후 화면">
<p class="cap">계정 A 등록 직후 화면: 서버가 저장했다고 돌려준 값이 그대로 보이고, 위 DB 표의 값(식별값 2hA0sIVGMQz6mb_zAr5IyQ, 공개키 MFkwEwYH…)과 같습니다.</p>
<img src="data:image/png;base64,{img('page-register-B.png')}" alt="계정 B 등록 직후 화면">
<p class="cap">계정 B 등록 직후 화면(식별값 GUC1V99lWv_RklAp-X5nPA).</p></section>

<section><h2>3-1. 패스키 목록 화면 (이름·등록 날짜)</h2>
<p>로그인한 계정의 “MY PASSKEYS” 목록입니다. 패스키마다 이름과 등록 날짜가 보이고, 이 계정의 것만 나옵니다.</p>
<img src="data:image/png;base64,{img('C4:page-list-1-passkey.png')}" alt="패스키 1개 목록" style="width:80%">
<p class="cap">패스키가 1개일 때: <b>B 1st passkey</b>, 등록 2026-10-20 06:17(UTC).</p>
<img src="data:image/png;base64,{img('C4:page-list-2-passkeys.png')}" alt="패스키 2개 목록" style="width:80%">
<p class="cap">같은 계정에 두 번째 패스키 <b>B 2nd passkey</b>(등록 06:54 UTC)를 더한 뒤: 목록에 2개가 이름·날짜와 함께 보입니다. 화면 아래쪽에는 방금 등록한 값(공개키 등)이 보입니다.</p></section>

<section><h2>4. 개인키가 서버로 전송되지 않는다 (C23) — 계정 B 등록의 요청·응답 기록</h2>
<p>화면의 “요청·응답 기록”에서 복사한 글입니다. 두 번째 단계의 <b>요청 본문</b>에 있는 항목은 id, rawId, type, response(clientDataJSON, attestationObject, transports) 뿐입니다. 이 중 어느 것에도 개인키는 들어 있지 않습니다. 긴 값은 앞부분과 글자 수만 줄여 보여 주도록 만들었고(질문 challenge는 전부 보임), 개인키가 들어갈 항목 자체가 없습니다.</p>
<pre>{e(log_b)}</pre>
<div class="note">추가 점검: 개발 환경에서 가상 인증기로 같은 흐름을 돌려, 인증기가 가진 <b>개인키 값이 오간 모든 요청·응답 본문 어디에도 없음</b>을 확인했습니다. 같은 점검 {n_ok}/{n_all}개가 통과했습니다(질문 재사용 거절, 출처 변조 거절, 취소 시 저장 0건 포함). 결과: evidence/card2/local-test-results.json</div></section>

<section><h2>5. 도중에 취소하면 (C25)</h2>
<p>패스키 저장 창에서 <b>취소</b>를 눌렀을 때의 기록입니다. 서버로 아무것도 보내지 않았고, 화면에는 “취소했습니다. 서버에는 아무것도 저장되지 않았습니다.”가 나왔습니다.</p>
<pre>{e(log_c)}</pre>
<p class="cap">첫 줄의 응답 500은 이 증거를 만들던 중 실제로 있었던 서버 오류입니다. 원인은 DB 표에 서버 키의 사용 권한이 없던 것이었고(서버 로그: <code>db GET passkey_accounts -&gt; 403</code>), SQL로 서버 키에만 권한을 주어 고쳤습니다(저장소 db/schema.sql, 커밋 02b913b). 고친 뒤 3시 10분의 두 번째 줄부터 정상입니다.</p>
<img src="data:image/png;base64,{img('db-credentials-empty.png')}" alt="취소 직후 passkey_credentials 빈 표">
<p class="cap">취소 직후(등록 전)의 passkey_credentials: <b>0건</b>(“This table is empty”). 취소로 저장된 것이 없습니다. 같은 시각 passkey_challenges에는 서버가 낸 질문만 1건 남아 있었고 used_at은 NULL이었습니다.</p></section>

<section><h2>6. 패스키를 저장한 곳 (C26)</h2>
<table>
<tr><th style="width:24%">개인키</th><td>이 PC의 Chrome이 <b>Google 비밀번호 관리자</b>에 저장했습니다(“패스키 저장됨 — Google 비밀번호 관리자에 저장된 패스키”). 이 사이트의 서버, Vercel, Supabase에는 없습니다.</td></tr>
<tr><th>공개키</th><td>Supabase 프로젝트 <code>t08-about-me-page-passkey</code>의 <code>passkey_credentials</code> 표. 서버 키로만 읽고 쓸 수 있습니다.</td></tr>
<tr><th>저장 위치 고르는 창</th><td>저장 위치로 “Google 비밀번호 관리자”와 “휴대전화·태블릿 또는 보안 키” 중에서 고를 수 있었고, 앞의 것을 골랐습니다.</td></tr></table></section>

<section><h2>7. 로그인하지 않은 사람은 남의 계정에 패스키를 붙일 수 없다</h2>
<img src="data:image/png;base64,{img('page-403-attempt.png')}" alt="이미 패스키가 있는 계정에 추가 시도">
<p class="cap">패스키가 이미 있는 계정 A에, 로그인하지 않은 채 “추가시도”라는 이름으로 등록을 시도하자 서버가 거절했습니다(403, “이미 패스키가 있는 계정입니다. 로그인한 뒤에 추가해야 합니다.”). 패스키 창은 뜨지 않았고 저장된 것도 늘지 않았습니다.</p></section>

<section><h2>8. 카드 2 통과 기준 대응</h2>
<table><tr><th class="no">번호</th><th>기준</th><th>결과</th><th>근거</th></tr>{trs}</table>
<div class="note"><b>이 문서의 범위</b>: 등록과 그 결과(서버에 저장된 공개키, 패스키 목록 화면)입니다. 서버 확인 코드는 외부 라이브러리 없이 Node.js 내장 crypto로 직접 구현했습니다(api/_lib/webauthn.js). 로그인·삭제 등은 별도 자료에 있습니다.</div></section>
</body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.set_content(doc, wait_until="load")
    pg.pdf(path=str(ROOT / "evidence" / "card2" / "card2-evidence-deployed.pdf"), format="A4", print_background=True,
           margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
    b.close()
print("ok")
