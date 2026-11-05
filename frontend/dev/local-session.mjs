import { readFile } from "node:fs/promises";

const ENDPOINT = "/__local/session";
const ORIGIN = "http://localhost:5173";
const LOOPBACK = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);

function reply(response, status, value) {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");
  response.end(JSON.stringify(value));
}

export function localSessionMiddleware({ credentialsFile, backendUrl = "http://127.0.0.1:8000", fetchImpl = fetch }) {
  const target = new URL(backendUrl);
  if (target.protocol !== "http:" || !["localhost", "127.0.0.1", "[::1]"].includes(target.hostname)
      || target.username || target.password) {
    throw new Error("Dev session chỉ kết nối backend loopback.");
  }
  return async function middleware(request, response, next) {
    if (request.url?.split("?")[0] !== ENDPOINT) return next();
    if (request.method !== "POST") {
      response.setHeader("Allow", "POST");
      return reply(response, 405, { error: "METHOD_NOT_ALLOWED" });
    }
    // Không tin X-Forwarded-For/Host. Chặn LAN, trang ngoài và DNS rebinding.
    if (!LOOPBACK.has(request.socket.remoteAddress) || request.headers.host !== "localhost:5173"
        || request.headers.origin !== ORIGIN
        || (request.headers["sec-fetch-site"] && request.headers["sec-fetch-site"] !== "same-origin")) {
      return reply(response, 403, { error: "OPEN_LOCALHOST" });
    }
    if (request.url !== ENDPOINT) return reply(response, 400, { error: "UNEXPECTED_QUERY" });
    try {
      const contents = await readFile(credentialsFile, "utf8");
      const matches = [...contents.matchAll(/^\s*OPERATOR_TOKEN\s*=\s*([^\r\n]+)$/gm)];
      if (matches.length !== 1) throw new Error("LOCAL_CONFIG");
      let token = matches[0][1].trim();
      if ((token.startsWith('"') && token.endsWith('"')) || (token.startsWith("'") && token.endsWith("'"))) {
        token = token.slice(1, -1);
      }
      if (token.length < 32) throw new Error("LOCAL_CONFIG");
      const upstream = await fetchImpl(new URL("/api/v1/auth/login", target), {
        method: "POST", headers: { "Content-Type": "application/json", Origin: ORIGIN },
        body: JSON.stringify({ token }), signal: AbortSignal.timeout(5000),
        redirect: "error",
      });
      const cookies = upstream.headers.getSetCookie();
      if (!upstream.ok || !cookies.length || cookies.some(cookie => !/;\s*httponly(?:;|$)/i.test(cookie))) {
        throw new Error("LOCAL_AUTH");
      }
      response.setHeader("Set-Cookie", cookies);
      return reply(response, 200, { authenticated: true });
    } catch {
      // Không trả nội dung file, token, body hoặc lỗi upstream cho browser/log.
      return reply(response, 503, { error: "LOCAL_SERVICE_UNAVAILABLE" });
    }
  };
}

export function localSessionPlugin(options) {
  return {
    name: "asd-local-session", apply: "serve",
    configureServer(server) {
      server.middlewares.use(localSessionMiddleware(options));
    },
  };
}
