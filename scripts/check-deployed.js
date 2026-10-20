// 배포 주소를 로그인 없이 확인하는 스크립트 (시크릿 창의 개발자도구 콘솔에서 실행)
(async()=>{
const needles=["ALEPH 대형 과제 정리","자격증 준비 + 지원 공고","이번 주에 새로 배운 것","커피 커뮤니티 경험 정리","지원 공고 + 자격증 + 커핑 + 대회","추출 연습에서 배운 것","방어전 1~2차 · 기본 방어 단계를 차례로 완성함. 아쉬운 점: 설명을 더 짧게 쓰기. 다음: 로그 읽는 순서 정리.\n방어전 3차 · 여러 단계를 이어서 마무리함. 아쉬운 점: 막힌 이유를 바로 적어 두지 않음. 다음: 막힌 지점 메모하기.\nXDR 보너스 6종 · 탐지 유형별로 나눠서 정리함. 아쉬운 점: 비슷한 유형이 헷갈림. 다음: 비교표 만들기.\n방어전 4차 · 화면에 보이는 값을 만들고 다시 제출하며 고침. 아쉬운 점: 예외 값을 늦게 챙김. 다음: 먼저 예외부터 확인하기.\n(만들어 넣은 내용)","자격증 · 가상의 보안 기초 자격증. 준비 일정: 다음 달 모의시험 1회, 틀린 문제 정리.\n지원 공고 · 가상의 보안 관제 스터디. 마감: 이번 달 말. 해 둘 일: 지원서 초안 쓰기.\n(만들어 넣은 내용)","비밀번호 없이도 본인 확인이 되는 이유를 공개키와 일회용 질문으로 설명해 보았다. 아직 헷갈리는 점은 서명을 어디서 확인하는지다. (만들어 넣은 내용)","카페쇼 커핑·센서리 · 처음 향미를 말로 적어 봄. 느낀 점: 같은 커피도 표현이 사람마다 다름. 다음: 향미 단어 목록 만들기.\n퍼블릭 커핑 · 여러 사람과 같은 원두를 맛봄. 느낀 점: 다른 사람의 표현이 도움이 됨. 다음: 내 표현을 먼저 적고 비교하기.\n커피 세미나 · 추출과 보관 이야기를 들음. 느낀 점: 보관 방법이 맛에 영향을 줌. 다음: 보관 방법을 바꿔 시도해 보기.\n(만들어 넣은 내용)","지원 공고 · 가상의 커피 세미나 스태프 모집. 마감: 이번 달 중순.\n자격증 · 가상의 커피 자격 시험. 준비 일정: 매주 두 번 기출 풀이.\n커핑 지원 · 가상의 커핑 모임 신청. 준비물: 커핑 노트, 개인 스푼.\n대회 · 가상의 바리스타 대회 구경 후 참가 여부 정하기.\n(만들어 넣은 내용)","물 온도와 분쇄도를 한 번에 하나씩만 바꿔야 차이를 알 수 있다는 것을 확인했다. 다음에는 같은 원두로 세 번 비교해 본다. (만들어 넣은 내용)"];
const t0=new Date().toISOString();
const api=await fetch('/api/private/items',{credentials:'omit',cache:'no-store'});
const apiBody=await api.text();
const src=await (await fetch('/',{credentials:'omit',cache:'no-store'})).text();
await new Promise(r=>setTimeout(r,1500));
const dom=document.documentElement.outerHTML+document.body.innerText;
const out={checked_at_utc:t0,page_url:location.href,api_request:'GET '+location.origin+'/api/private/items (쿠키 없음)',api_status:api.status,api_content_type:api.headers.get('content-type'),api_cache_control:api.headers.get('cache-control'),api_body:apiBody,page_source_bytes:src.length,scanned_strings:needles.length,page_source_matches:needles.filter(n=>src.includes(n)).length,rendered_dom_matches:needles.filter(n=>dom.includes(n)).length,screen_status_text:(document.getElementById('vault-status')||{}).textContent};
console.log(JSON.stringify(out,null,1));
})();