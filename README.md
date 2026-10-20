# ALEPH-About-Me-Page-Passkey

ALEPH 개인과제 8 — 1번 소개 페이지 맨 아래에 **패스키(WebAuthn)로만 열리는 나만의 자리**를 붙인 프로젝트입니다. 비밀번호는 없습니다.

- 결과 주소: https://aleph-about-me-page-passkey.vercel.app/
- 소스: https://github.com/SCA-cloudy/ALEPH-About-Me-Page-Passkey
- 제출 문서: [docs/SUBMISSION.md](docs/SUBMISSION.md) / 시험 기록: [docs/TESTLOG.md](docs/TESTLOG.md)

※ 비공개 자리에 들어 있는 내용은 모두 과제용으로 **만들어 넣은 것**입니다. 실제 개인정보는 없습니다.

## 구성

| 위치 | 하는 일 |
|---|---|
| `index.html` | 과제 1번 소개 페이지(공개) + 맨 아래 나만의 자리(잠금 화면, 로그인, 패스키 목록·등록 화면). 비공개 내용은 이 파일에 없습니다. |
| `api/passkey/register-options.js`, `register-verify.js` | 등록: 서버가 일회용 질문을 내고, 기기의 답을 확인해 **공개키만** 저장 |
| `api/passkey/login-options.js`, `login-verify.js` | 로그인: 요청마다 새 질문, 저장된 공개키로 서명 확인, 성공하면 세션 시작 |
| `api/passkey/logout.js`, `session.js` | 로그아웃(서버의 세션 기록 삭제), 로그인 상태 확인 |
| `api/passkey/list.js`, `delete.js` | 내 패스키 목록(이름·날짜), 삭제(마지막 하나는 거절) |
| `api/private/items.js` | 비공개 자료. 로그인한 계정의 것만, 아니면 401 |
| `api/_lib/session.js` | **누구인지는 여기(쿠키의 세션)에서만 정함.** 주소·본문의 계정 값은 읽지 않음 |
| `api/_lib/webauthn.js`, `cbor.js` | 패스키 확인(외부 라이브러리 없이 Node 내장 `crypto`로 직접 구현) |
| `api/_lib/private-data.js` | 계정별 비공개 자료(서버 쪽 파일. 주소로 열리지 않음) |
| `api/_lib/db.js` | Supabase 저장(없으면 개발용 메모리) |
| `db/schema.sql` | 표 4개(계정, 패스키 공개키, 일회용 질문, 세션 해시) |
| `scripts/` | 시험·증거 도구(로컬 시험 `test_card*.py`, 배포 주소 확인용 콘솔 스크립트 `check-*.js`) |
| `evidence/` | 카드별 증거(캡처, 기록, 시험 결과) |

## 보안 구조 한 줄 요약

- 서버에는 **공개키만** 저장하고 개인키는 기기 밖으로 나오지 않습니다.
- 질문(challenge)은 요청마다 새로 만들고 5분 안에 한 번만 쓸 수 있습니다(한 번의 갱신 명령으로 소모).
- 세션 토큰은 HttpOnly·SameSite=Strict 쿠키로만 가고, 서버에는 해시만 저장합니다. 화면·기록에는 앞 4글자만 보입니다.
- 계정은 세션에서만 정합니다. 남의 패스키·자료를 가리키는 값을 보내도 무시하거나 404로 거절합니다.

## 실행

배포: Vercel(`api/*.js`가 자동으로 주소 `/api/...`가 됨), 저장: Supabase.
환경 변수(Vercel): `SUPABASE_URL`, `SUPABASE_SECRET_KEY`(서버 전용 비밀 키, 어디에도 출력하지 않음).
Supabase SQL Editor에서 `db/schema.sql`을 한 번 실행합니다(서버 키에만 표 사용 권한을 줍니다).

내 컴퓨터에서 돌려 보기(환경 변수가 없으면 메모리에 임시 저장):

```
node dev-server.mjs      # http://localhost:3000
python3 scripts/test_card2.py   # 등록 20개 점검 (가상 인증기)
python3 scripts/test_card3.py   # 로그인·로그아웃 22개 점검
python3 scripts/test_card4.py   # 패스키 2개·삭제·다른 계정 21개 점검
```
