// 비공개 자리에 들어가는 자료입니다. 서버 쪽에만 두고, 로그인한 계정의 것만 내려 줍니다.
//
// ※ 여기 있는 내용은 전부 과제용으로 "만들어 넣은 것"입니다. 실제 연락처·신분증 번호 같은
//   진짜 개인정보는 없습니다. (소스 저장소는 공개이므로 이 파일의 내용은 저장소에서 보입니다.)
// ※ 계정마다 내용이 다릅니다. 카드 2에서 계정이 만들어질 때 이 계정 키와 연결합니다.

const ITEMS_BY_ACCOUNT = {
  "account-a": [
    { id: "a-1", kind: "프로젝트 메모", title: "패스키 과제 진행 순서", body: "화면 나누기 → 등록 → 로그인 → 기기 분실 대비 → 교차 확인 순서로 진행한다. (만들어 넣은 내용)" },
    { id: "a-2", kind: "지원 목록", title: "가상의 스터디 모집 A", body: "보안 기초 스터디, 마감은 다음 주. 지원서 초안을 먼저 써 본다. (만들어 넣은 내용)" },
    { id: "a-3", kind: "회고", title: "이번 주에 새로 배운 것", body: "비밀번호 없이도 본인 확인이 되는 이유를 공개키와 일회용 질문으로 설명해 보았다. (만들어 넣은 내용)" },
  ],
  "account-b": [
    { id: "b-1", kind: "프로젝트 메모", title: "소개 페이지 문구 다듬기", body: "첫 화면 문장을 한 줄 줄이고, 활동 설명의 순서를 바꿔 본다. (만들어 넣은 내용)" },
    { id: "b-2", kind: "지원 목록", title: "가상의 동아리 공연 B", body: "드럼 파트 신청 일정과 합주곡 후보를 정리한다. (만들어 넣은 내용)" },
    { id: "b-3", kind: "회고", title: "실수에서 배운 것", body: "화면에서만 숨기면 소스에는 남는다는 점을 직접 확인해 보았다. (만들어 넣은 내용)" },
  ],
};

export function itemsFor(accountId) {
  return ITEMS_BY_ACCOUNT[accountId] ?? [];
}

// 점검용: 로그인 없이 받은 페이지·응답에 이 자료의 문장이 섞여 있지 않은지 검사할 때 쓰는 목록
// (scripts/collect_card1.py가 사용. 주소로는 열리지 않는 내부 파일입니다.)
export function allItemsForScan() {
  return Object.values(ITEMS_BY_ACCOUNT).flat();
}

// 점검용: 계정별 자료 건수 (내용은 돌려주지 않음)
export function itemCounts() {
  return Object.fromEntries(Object.entries(ITEMS_BY_ACCOUNT).map(([id, items]) => [id, items.length]));
}
