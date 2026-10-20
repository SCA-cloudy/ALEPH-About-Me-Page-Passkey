#!/usr/bin/env python3
"""제출용 보고서 PDF: docs/SUBMISSION.md(본문) + 카드별 증거(캡처·기록) + docs/TESTLOG.md(시험 기록)를 한 파일로 묶습니다.
출력: ALEPH-과제8-제출보고서.pdf"""
import base64, html, json, pathlib, re
import markdown
from playwright.sync_api import sync_playwright

R = pathlib.Path(__file__).resolve().parent.parent
E = R / "evidence"
e = html.escape
def img(path, cap="", w="100%", cls=False):
    b = base64.b64encode((E / path).read_bytes()).decode()
    return f'<figure class="{"c" if cls else ""}" style="width:{w};margin-left:auto;margin-right:auto"><img src="data:image/png;base64,{b}"><figcaption>{e(cap)}</figcaption></figure>'
def keep(*parts): return '<div class="keep">' + ''.join(parts) + '</div>'
def row(*figs): return '<div class="row">' + "".join(figs) + "</div>"
def jtxt(path):
    return json.dumps(json.loads((E / path).read_text(encoding="utf-8")), ensure_ascii=False, indent=1)
def pre(path):
    t = jtxt(path); cls = ' class="two"' if t.count("\n") > 28 else ""
    return f"<pre{cls}>{e(t)}</pre>"
def md(text): return markdown.markdown(text, extensions=["tables", "fenced_code"])

sub = (R / "docs" / "SUBMISSION.md").read_text(encoding="utf-8")
head, expl = sub.split("## 인증 설명", 1)
head_body = head.split("---", 1)[0]          # 제목+주소+4줄+3줄
head_body = head_body.replace("# ALEPH 개인과제 8 제출 문서 — 내 소개 페이지에 패스키 달기\n", "")
expl_html = md("## 인증 설명" + expl)
head_html = md(head_body)
log = (R / "docs" / "TESTLOG.md").read_text(encoding="utf-8")
log_html = md(log.split("\n", 2)[2].replace("## 1.", "### 1.").replace("## 2.", "### 2.").replace("## 3.", "### 3."))

c = []
def sec(t): c.append(f"<h2>{t}</h2>")
sec("① 공개 영역과 비공개 영역을 가른 화면, 로그인 없이 받은 응답 본문")
c.append('<div class="row eq">' + img("card1/deployed/deployed-page.png", "시크릿 창의 공개 페이지. 맨 아래 “나만의 자리”는 잠겨 있고 PUBLIC/PRIVATE 경계선이 보임", "49%") + '<div class="frame" style="width:49%">' + img("card1/deployed/deployed-api-body.png", "", "100%") + '<div class="cap">로그인 없이 /api/private/items 를 열면 401, 본문은 안내 문장뿐</div></div></div>')
c.append("<p>로그인 없이 받은 응답(요청: GET /api/private/items, 쿠키 없음) — 상태 401, 본문 <code>{\"error\":\"unauthorized\",\"message\":\"패스키로 로그인해야 볼 수 있습니다.\"}</code>. 페이지 소스·화면에서 비공개 문장 0/12건.</p>")
c.append('<div class="row eq21"><div style="width:66%">' + pre("card1/deployed/console-result.json") + '</div>' + img("card1/deployed/deployed-console-result.png", "위 결과가 나온 콘솔 화면", "32%") + "</div>")
c.append(img("final/incognito-final-check.png", "수정이 모두 끝난 뒤 다시 한 시크릿 창 점검: 자료 API 401, 비공개 문장 0/12건"))

sec("② 등록 요청과 응답 기록, 서버에 저장된 공개키, 패스키 목록 화면")
c.append("<p>계정 B 등록의 요청·응답 기록(화면의 “요청·응답 기록 보기”에서 복사). 요청 본문에 개인키는 없습니다.</p><pre class=\"two\">" + e((E / "card2/deployed/log-register-B.json").read_text(encoding="utf-8")) + "</pre>")
c.append(row(img("card2/deployed/page-register-A.png", "계정 A 등록 직후", "49%"), img("card2/deployed/page-register-B.png", "계정 B 등록 직후", "49%")))
c.append(img("card2/deployed/db-credentials-2rows.png", "서버(Supabase)에 저장된 것은 공개키(public_key)와 이름뿐. 비밀번호·개인키 열은 없음"))
c.append(img("card2/deployed/db-challenges-3rows.png", "서버가 낸 일회용 질문 3건: 모두 다른 값. 쓴 질문은 used_at이 찍힘(취소한 시도는 NULL)"))
c.append(row(img("card4/deployed/page-list-1-passkey.png", "패스키 목록 화면(이름·등록 날짜·식별값)", "60%")))
c.append("<p>등록 도중 취소: 서버로 아무것도 보내지 않았고 passkey_credentials는 0건. 이미 패스키가 있는 계정에 로그인 없이 등록 시도 → 403.</p>")
c.append(row(img("card2/deployed/db-credentials-empty.png", "취소 직후 passkey_credentials: 0건", "49%"), img("card2/deployed/page-403-attempt.png", "로그인 없이 등록 시도 → 403", "49%")))
c.append("<p>개인키는 이 PC의 Chrome이 로그인된 <b>Google 비밀번호 관리자</b>에 저장했고, 서버에는 공개키만 있습니다.</p>")

sec("③ 성공한 로그인 요청, 실패한 요청, 이미 쓴 질문을 재사용한 요청과 거절 응답")
c.append(row(img("card3/deployed/page-locked.png", "로그인 전: 잠김, 비밀번호 입력칸 없음", "32%"), img("card3/deployed/dialog-chooser.png", "기기의 패스키 선택 창", "32%"), img("card3/deployed/page-logged-in-B.png", "로그인 후: 계정 B 자료 3개, 토큰은 앞 4글자만", "32%")))
c.append("<p><b>성공한 로그인 요청·응답</b>(질문 요청 → 기기 서명 → 서버 응답 200). 토큰은 마스킹.</p>" + pre("card3/deployed/log-login-B.json"))
c.append(img("card3/deployed/db-sessions-1row.png", "로그인 중 passkey_sessions: 1행. token_hash는 토큰의 해시(원문 아님)"))
c.append(img("card3/deployed/db-credentials-counter0.png", "서명 횟수(counter)는 0 — 동기화 패스키는 0을 보냄"))
c.append(keep("<p><b>실패한 요청과 이미 쓴 질문의 재사용</b>(배포 주소 콘솔 스크립트): 망가뜨린 서명 401, 서버가 낸 적 없는 질문 401, <u>같은 로그인 값(이미 쓴 질문) 재전송 401</u>, 질문은 요청마다 새 값, 로그아웃 후 자료 요청 401.</p>" + pre("card3/deployed/console-result.json"), img("card3/deployed/console-checks.png", "위 결과가 나온 콘솔 화면(401 오류 줄이 거절의 증거)", "60%")))
c.append(row(img("card3/deployed/page-logged-out.png", "로그아웃 후 다시 잠김(서버 응답 401)", "49%"), img("card3/deployed/db-sessions-empty.png", "로그아웃 후 passkey_sessions 0행", "49%")))

sec("④ 패스키 두 개가 보이는 목록, 하나를 지운 뒤의 로그인 성공과 실패 기록")
c.append(row(img("card4/deployed/page-list-1-passkey.png", "패스키 1개", "49%", True), img("card4/deployed/page-list-2-passkeys.png", "두 번째 추가 후 목록에 2개", "49%", True)))
c.append(row(img("card4/deployed/dialog-chooser-3-entries.png", "선택 창에 패스키가 따로 보임(…B 2nd passkey)", "49%", True), img("card4/deployed/page-login-with-2nd.png", "두 번째 패스키로 로그인 성공", "49%", True)))
c.append(pre("card4/deployed/log-login-2nd.json"))
c.append(row(img("card4/deployed/page-deleted-1st.png", "첫 번째 패스키 삭제 → 남은 1개", "49%", True), img("card4/deployed/page-last-409.png", "마지막 하나를 지우려 하면 서버가 거절(409)", "49%", True)))
c.append("<p><b>삭제 뒤 실패 기록</b> — 삭제한 패스키(1st)로 로그인 → 401 “등록되어 있지 않은(또는 삭제된) 패스키입니다.”</p>")
c.append(img("card4/deployed/page-deleted-login-rejected.png", "삭제한 패스키로 로그인 거절", "70%", True))
c.append(pre("card4/deployed/log-deleted-login-rejected.json"))
c.append("<p><b>삭제 뒤 로그인 성공 기록</b> — 남은 패스키(B 2nd passkey, 식별값 hmLfMUCQ…)로 로그인 → 200 (오후 4:45~4:47), 이어서 로그아웃 200.</p>")
c.append(row(img("card4/deployed/dialog-chooser-after-delete.png", "삭제 뒤 선택 창: 남은 패스키로 로그인 시도", "49%", True), img("card4/deployed/page-login-after-delete.png", "로그인 성공, 목록에는 B 2nd passkey만", "49%", True)))
c.append(pre("card4/deployed/log-login-after-delete.json"))
c.append(img("card4/deployed/page-logout-after-delete.png", "로그아웃 응답 200(오후 4:47:01), 다시 잠김", "70%", True))
c.append("<p><b>마지막 패스키까지 없어지면?</b> 서버가 마지막 하나의 삭제를 거절합니다(409). 0개가 되면 주인 없는 계정이 되어 아무나 먼저 등록할 수 있게 되기 때문입니다.</p>")

c.append('<div style="break-before:page"></div>')
sec("⑤ 확인 네 가지의 요청과 응답, 인증 구현 설명서 여섯 항목")
c.append("<p>확인 네 가지: ㉮ 로그인 없이 비공개 자료 → 401 (위 ①) ㉯ 서명이 맞으면 200, 망가뜨리면 401 (위 ③) ㉰ 같은 질문 재사용: 처음 200, 둘째 401 (위 ③) ㉱ 다른 계정 건드리기 (아래).</p>")
c.append("<p>두 계정의 비공개 내용은 서로 다릅니다. 계정 A(보안·네트워크): ARCHIVE “ALEPH 대형 과제 정리”, ROADMAP “자격증 준비 + 지원 공고”, REVIEW “이번 주에 새로 배운 것”. 계정 B(커피): ARCHIVE “커피 커뮤니티 경험 정리”, ROADMAP “지원 공고 + 자격증 + 커핑 + 대회”, REVIEW “추출 연습에서 배운 것”.</p>")
c.append(img("card5/deployed/page-logged-in-A.png", "계정 A로 로그인한 화면: A의 자료와 A의 패스키만", "62%"))
c.append(keep("<p><b>B로 로그인해서 A를 건드림</b> (주소·본문에 account-a를 적고, A의 패스키 id로 삭제 요청)</p>" + pre("card5/deployed/console-B-touches-A.json"), img("card5/deployed/console-B-touches-A.png", "실행 화면", "55%")))
c.append(keep("<p><b>A로 로그인해서 B를 건드림</b></p>" + pre("card5/deployed/console-A-touches-B.json"), img("card5/deployed/console-A-touches-B.png", "실행 화면", "55%")))
c.append("<p>시험 전·후 DB passkey_credentials(2행, id·날짜 그대로) — 삭제 요청이 다른 계정의 것을 지우지 않았음:</p>")
c.append(keep(img("card5/deployed/db-credentials-before.png", "시험 전 (A 1행, B 1행)", "85%"), img("card5/deployed/db-credentials-after.png", "시험 후 (그대로)", "85%")))
evid = "\n".join(c)

doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:15mm 14mm; }}
body {{ font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; color:#20231f; font-size:9.6pt; line-height:1.55; }}
h1 {{ font-size:20pt; margin:0 0 6px; }} h2 {{ font-size:13pt; margin:20px 0 6px; border-bottom:2px solid #20231f; padding-bottom:3px; break-after:avoid; }}
h3 {{ font-size:10.8pt; margin:14px 0 4px; break-after:avoid; }}
table {{ border-collapse:collapse; width:100%; font-size:8.6pt; margin:6px 0; }} th,td {{ border:1px solid #bbb; padding:3px 6px; vertical-align:top; text-align:left; }} th {{ background:#f0ebe0; }}
pre {{ background:#f6f4ee; border:1px solid #cfc7b9; padding:6px 8px; font-size:7.2pt; white-space:pre-wrap; word-break:break-all; line-height:1.35; font-family:'Noto Sans Mono CJK KR','DejaVu Sans Mono',monospace; }}
code {{ font-family:'Noto Sans Mono CJK KR','DejaVu Sans Mono',monospace; font-size:.9em; background:#f1eee6; padding:0 2px; }}
pre code {{ background:none; padding:0; }}
figure {{ margin:6px auto; break-inside:avoid; }} .keep {{ break-inside:avoid; }} .keep p {{ margin:4px 0; }} pre {{ break-inside:avoid; }} pre.two {{ column-count:2; column-gap:14px; font-size:6.6pt; }} figure.c img {{ aspect-ratio:1080/985; object-fit:cover; object-position:top; }} figure img {{ width:100%; border:1px solid #888; display:block; }} figcaption {{ font-size:8pt; color:#555; margin-top:2px; }}
.row.eq {{ align-items:stretch; }} .row.eq .frame {{ display:flex; flex-direction:column; justify-content:center; border:1px solid #888; background:#f4f4f4; padding:8px; box-sizing:border-box; }} .frame figure {{ margin:0; }} .frame .cap {{ font-size:8pt; color:#555; margin-top:8px; text-align:center; }} .row.eq21 {{ align-items:center; }} .row.eq21 pre {{ margin:0; }} .row {{ display:flex; gap:2%; align-items:flex-start; break-inside:avoid; }}
.note {{ background:#fff7e6; border-left:4px solid #d29a77; padding:5px 9px; font-size:9pt; }}
div.log td:nth-last-child(2) {{ white-space:nowrap; }}
ul,ol {{ margin:3px 0 3px 18px; padding:0; }}
</style></head><body>
<h1>ALEPH 개인과제 8 — 내 소개 페이지에 패스키 달기</h1>
<div class="note">과제용으로 만들어 넣은 내용입니다. 실제 개인정보는 없습니다. 비공개 자리는 패스키로 로그인해야만 열리므로, 열린 모습과 시험 결과를 이 보고서 뒷부분의 캡처와 기록으로 남겼습니다.</div>
{head_html}
<h2 style="break-before:page">남긴 증거 (다섯 묶음)</h2>
<p>모두 배포 주소(https://aleph-about-me-page-passkey.vercel.app/)에서 일반 Chrome 창으로 직접 한 시험입니다. 시각은 2026-10-20(KST).</p>
{evid}
<div style="break-before:page">{expl_html}</div>
<h2 style="break-before:page">시험 기록</h2>
<div class="log">{log_html}</div>
</body></html>"""
out = R / "ALEPH-과제8-제출보고서.pdf"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.set_content(doc, wait_until="load")
    pg.pdf(path=str(out), format="A4", print_background=True, margin={"top": "13mm", "bottom": "14mm", "left": "11mm", "right": "11mm"},
           display_header_footer=True, header_template="<span></span>", footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#777"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')
    b.close()
print(out)
