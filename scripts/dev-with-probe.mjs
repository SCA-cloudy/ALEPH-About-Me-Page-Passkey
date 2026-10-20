// 점검용 실행기(배포되지 않음): 개발용 서버를 띄우고, 한 포트 옆에서 "저장된 개수"만 알려 주는 확인 주소를 엽니다.
import http from "node:http";
import "../dev-server.mjs";
import * as db from "../api/_lib/db.js";

const PORT = Number(process.env.PORT || 3000) + 1;
http.createServer(async (req, res) => {
  const out = { usingMemory: db.usingMemory, credentials: {}, sessions: await db.sessionCount() };
  for (const id of ["account-a", "account-b"]) out.credentials[id] = (await db.listCredentials(id)).map((c) => ({ name: c.name, credential_id: c.credential_id, public_key: c.public_key }));
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(out));
}).listen(PORT, "127.0.0.1");
