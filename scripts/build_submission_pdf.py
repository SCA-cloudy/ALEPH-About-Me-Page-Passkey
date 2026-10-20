#!/usr/bin/env python3
"""제출용 보고서 PDF: docs/SUBMISSION.md(본문) + 카드별 증거(캡처·기록) + docs/TESTLOG.md(시험 기록)를 한 파일로 묶습니다.
출력: ALEPH-과제8-제출보고서.pdf"""
import base64, html, json, pathlib, re
import markdown
from playwright.sync_api import sync_playwright

R = pathlib.Path(__file__).resolve().parent.parent
E = R / "evidence"
e = html.escape
def img(path, cap="", w="100%"):
    b = base64.b64encode((E / path).read_bytes()).decode()
    return f'<figure style="width:{w}"><img src="data:image/png;base64,{b}"><figcaption>{e(cap)}</figcaption></figure>'
def row(*figs): return '<div class="row">' + "".join(figs) + "</div>"
def jtxt(path):
    return json.dumps(json.loads((E / path).read_text(encoding="utf-8")), ensure_ascii=False, indent=1)
def pre(path): return f"<pre>{e(jtxt(path))}</pre>"
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
c.append("<h2>카드 1 — 공개와 비공개 나누기 (로그인 없이)</h2>")
c.append(row(img("card1/deployed/deployed-page.png", "시크릿 창의 공개 페이지. 맨 아래 “나만의 자리”는 잠겨 있고 PUBLIC/PRIVATE 경계선이 보임", "46%"),
             '<div style="width:52%">' + img("card1/deployed/deployed-api-body.png", "로그인 없이 /api/private/items 를 열면 401") + img("card1/deployed/deployed-console-result.png", "콘솔 점검: api_status 401, 페이지 소스·화면에서 비공개 문장 0건") + "</div>"))
c.append("<h2>카드 2 — 패스키 등록</h2>")
c.append(img("card2/deployed/db-challenges-3rows.png", "서버가 낸 일회용 질문 3건: 모두 다른 값. 쓴 질문은 used_at이 찍혀 다시 못 씀(취소한 시도는 NULL)"))
c.append(img("card2/deployed/db-credentials-2rows.png", "서버에 저장된 것은 공개키(public_key)와 이름뿐. 비밀번호·개인키 열은 없음"))
c.append(row(img("card2/deployed/page-register-A.png", "계정 A 등록 직후", "49%"), img("card2/deployed/page-register-B.png", "계정 B 등록 직후", "49%")))
c.append("<p>계정 B 등록의 요청·응답 기록(화면의 “요청·응답 기록 보기”에서 복사). 요청 본문에 개인키는 없습니다.</p><pre>" + e((E / "card2/deployed/log-register-B.json").read_text(encoding="utf-8")) + "</pre>")
c.append("<p>등록 도중 취소: 서버로 아무것도 보내지 않았고, 취소 직후 passkey_credentials는 0건.</p>")
c.append(row(img("card2/deployed/db-credentials-empty.png", "취소 직후 passkey_credentials: 0건", "100%")))
c.append(row(img("card2/deployed/page-403-attempt.png", "이미 패스키가 있는 계정 A에 로그인 없이 등록 시도 → 403", "70%")))
c.append("<p>저장 위치: 개인키는 이 PC의 Chrome이 로그인된 <b>Google 비밀번호 관리자</b>에 저장했고, 서버(Supabase)에는 공개키만 있습니다.</p>")
c.append("<h2>카드 3 — 패스키 로그인·로그아웃</h2>")
c.append(row(img("card3/deployed/page-locked.png", "로그인 전: 잠김, 비밀번호 입력칸 없음, “패스키로 열기” 버튼", "32%"), img("card3/deployed/dialog-chooser.png", "기기의 패스키 선택 창(계정 이름만 보임)", "32%"), img("card3/deployed/page-logged-in-B.png", "로그인 후: 계정 B 자료 3개, 세션 토큰은 앞 4글자만", "32%")))
c.append("<p>로그인 요청·응답 기록(질문 요청 → 기기 서명 → 서버 응답 200). 토큰은 마스킹되어 있고 비밀번호 항목이 없습니다.</p>" + pre("card3/deployed/log-login-B.json"))
c.append(img("card3/deployed/db-sessions-1row.png", "로그인 중 passkey_sessions: 1행. token_hash는 토큰의 해시(원문 아님)"))
c.append(img("card3/deployed/db-credentials-counter0.png", "서명 횟수(counter)는 0 — 동기화 패스키는 0을 보냄"))
c.append(row(img("card3/deployed/page-logged-out.png", "로그아웃 후 다시 잠김(서버 응답 401)", "49%"), img("card3/deployed/db-sessions-empty.png", "로그아웃 후 passkey_sessions 0행 — 서버의 세션 기록도 지움", "49%")))
c.append("<p>배포 주소에서 거절 확인(콘솔 스크립트): 망가뜨린 서명, 서버가 낸 적 없는 질문, 같은 로그인 값 재전송이 모두 401, 질문은 요청마다 새 값, 로그아웃 후 자료 요청 401.</p>" + pre("card3/deployed/console-result.json"))
c.append(img("card3/deployed/console-checks.png", "위 결과가 나온 콘솔 화면(401 오류 줄이 거절의 증거)"))
c.append("<h2>카드 4 — 패스키 2개, 삭제, 거절</h2>")
c.append(row(img("card4/deployed/page-list-1-passkey.png", "패스키 1개 목록(이름·등록 날짜)", "49%"), img("card4/deployed/page-list-2-passkeys.png", "두 번째 패스키 추가 후 목록 2개", "49%")))
c.append(row(img("card4/deployed/dialog-chooser-3-entries.png", "선택 창에 패스키가 따로 보임(…B 2nd passkey)", "40%"), img("card4/deployed/page-login-with-2nd.png", "두 번째 패스키로 로그인 성공", "58%")))
c.append(pre("card4/deployed/log-login-2nd.json"))
c.append(row(img("card4/deployed/page-deleted-1st.png", "첫 번째 패스키 삭제 → 남은 1개", "49%"), img("card4/deployed/page-last-409.png", "마지막 하나를 지우려 하면 서버가 거절(409): 0개가 되지 않음", "49%")))
c.append(row(img("card4/deployed/page-deleted-login-rejected.png", "삭제한 패스키로 로그인 → “등록되어 있지 않은(또는 삭제된) 패스키입니다.”", "58%")))
c.append(pre("card4/deployed/log-deleted-login-rejected.json"))
c.append("<p><b>마지막 패스키까지 없어지면?</b> 서버가 마지막 하나의 삭제를 거절합니다(409). 0개가 되면 아무도 그 계정에 들어갈 수 없고, 주인 없는 계정이 되어 아무나 먼저 등록할 수 있게 되기 때문입니다.</p>")
c.append("<h2>카드 5 — 두 계정 서로 건드리기</h2>")
c.append("<p>두 계정의 비공개 내용은 서로 다릅니다. 계정 A(보안·네트워크): ARCHIVE “ALEPH 대형 과제 정리”, ROADMAP “자격증 준비 + 지원 공고”, REVIEW “이번 주에 새로 배운 것”. 계정 B(커피): ARCHIVE “커피 커뮤니티 경험 정리”, ROADMAP “지원 공고 + 자격증 + 커핑 + 대회”, REVIEW “추출 연습에서 배운 것”.</p>")
c.append(img("card5/deployed/page-logged-in-A.png", "계정 A로 로그인한 화면: A의 자료와 A의 패스키만", "62%"))
c.append("<p><b>B로 로그인해서 A를 건드림</b> (주소·본문에 account-a를 적고, A의 패스키 id로 삭제 요청)</p>" + pre("card5/deployed/console-B-touches-A.json"))
c.append(img("card5/deployed/console-B-touches-A.png", "실행 화면(삭제 404, 자료 요청 401은 로그아웃 후 확인)"))
c.append("<p><b>A로 로그인해서 B를 건드림</b></p>" + pre("card5/deployed/console-A-touches-B.json"))
c.append(img("card5/deployed/console-A-touches-B.png", "실행 화면"))
c.append("<p>시험 전·후 DB passkey_credentials(개수 2행, id·날짜 그대로) — 삭제 요청이 다른 계정의 것을 지우지 않았음:</p>")
c.append(img("card5/deployed/db-credentials-before.png", "시험 전 (A 1행, B 1행)"))
c.append(img("card5/deployed/db-credentials-after.png", "시험 후 (그대로)"))
c.append("<h2>최종 점검 — 모든 수정 뒤 시크릿 창</h2>")
c.append(img("final/incognito-final-check.png", "자료 API 401, 페이지 소스·화면에서 비공개 문장 0/12건"))
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
figure {{ margin:6px 0; break-inside:avoid; }} figure img {{ width:100%; border:1px solid #888; display:block; }} figcaption {{ font-size:8pt; color:#555; margin-top:2px; }}
.row {{ display:flex; gap:2%; align-items:flex-start; break-inside:avoid; }}
.note {{ background:#fff7e6; border-left:4px solid #d29a77; padding:5px 9px; font-size:9pt; }}
div.log td:nth-last-child(2) {{ white-space:nowrap; }}
ul,ol {{ margin:3px 0 3px 18px; padding:0; }}
</style></head><body>
<h1>ALEPH 개인과제 8 — 내 소개 페이지에 패스키 달기</h1>
<div class="note">과제용으로 만들어 넣은 내용입니다. 실제 개인정보는 없습니다. 비공개 자리는 패스키로 로그인해야만 열리므로, 열린 모습과 시험 결과를 이 보고서 뒷부분의 캡처와 기록으로 남겼습니다.</div>
{head_html}
{expl_html}
<h2 style="break-before:page">증거 (카드별 화면·기록)</h2>
<p>모두 배포 주소(https://aleph-about-me-page-passkey.vercel.app/)에서 일반 Chrome 창으로 직접 한 시험입니다. 시각은 2026-10-20(KST).</p>
{evid}
<h2 style="break-before:page">시험 기록</h2>
<div class="log">{log_html}</div>
</body></html>"""
out = R / "ALEPH-과제8-제출보고서.pdf"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.set_content(doc, wait_until="load")
    pg.pdf(path=str(out), format="A4", print_background=True, margin={"top": "15mm", "bottom": "15mm", "left": "14mm", "right": "14mm"},
           display_header_footer=True, header_template="<span></span>", footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#777"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')
    b.close()
print(out)
