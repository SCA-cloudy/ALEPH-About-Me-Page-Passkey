// 내 컴퓨터에서 페이지와 api를 함께 돌려 보는 개발용 서버입니다. (배포에는 쓰이지 않습니다)
// 실행: npm run dev  →  http://localhost:3000
// 배포(Vercel)에서는 api/ 폴더의 파일이 주소 /api/... 로 자동 연결됩니다. 여기서는 같은 규칙을 흉내 냅니다.
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);

function send(res, status, type, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", type);
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  const { pathname } = new URL(req.url, "http://localhost");

  // 화면: 첫 화면은 항상 공개 소개 페이지(index.html)
  if (pathname === "/" || pathname === "/index.html") {
    return send(res, 200, "text/html; charset=utf-8", await readFile(path.join(root, "index.html")));
  }

  // api: /api/a/b → api/a/b.js   (밑줄로 시작하는 폴더·파일은 내부용이라 주소로 열지 않음)
  if (pathname.startsWith("/api/")) {
    const parts = pathname.slice(5).split("/").filter(Boolean);
    const ok = parts.length > 0 && parts.every((p) => /^[A-Za-z0-9-]+$/.test(p));
    if (!ok) return send(res, 404, "text/plain; charset=utf-8", "Not Found");
    const file = path.join(root, "api", ...parts) + ".js";
    try {
      const mod = await import(pathToFileURL(file).href);
      return await mod.default(req, res);
    } catch (err) {
      if (err?.code === "ERR_MODULE_NOT_FOUND" || err?.code === "ENOENT") {
        return send(res, 404, "text/plain; charset=utf-8", "Not Found");
      }
      console.error(err);
      return send(res, 500, "text/plain; charset=utf-8", "Server Error");
    }
  }

  send(res, 404, "text/plain; charset=utf-8", "Not Found");
});

server.listen(PORT, () => console.log(`http://localhost:${PORT}`));
