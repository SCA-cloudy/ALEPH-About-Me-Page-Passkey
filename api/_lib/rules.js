// 입력 규칙
export const NAME_RULE = (s) => typeof s === "string" && s.trim().length >= 1 && s.trim().length <= 40;
