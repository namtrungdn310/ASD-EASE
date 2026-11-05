import assert from "node:assert/strict";
import { after, test } from "node:test";
import { mkdtempSync, writeFileSync, unlinkSync, rmdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { localSessionMiddleware } from "../dev/local-session.mjs";

const directory = mkdtempSync(join(tmpdir(), "asd-session-test-"));
const credentialsFile = join(directory, "backend.env");
const token = "operator-unit-" + "x".repeat(40);
writeFileSync(credentialsFile, `OPERATOR_TOKEN=${token}\n`);
after(() => { unlinkSync(credentialsFile); rmdirSync(directory); });

async function call(patch = {}, upstream = undefined) {
  let sent;
  let forwarded = false;
  const middleware = localSessionMiddleware({ credentialsFile, fetchImpl: upstream ?? (async (url, options) => {
    sent = { url: String(url), ...options };
    return new Response("{}", { status: 200, headers: {
      "Set-Cookie": "asd_operator=unit-cookie; HttpOnly; Path=/api/v1; SameSite=lax",
    } });
  }) });
  const request = { method: "POST", url: "/__local/session", socket: { remoteAddress: "127.0.0.1" },
    headers: { host: "localhost:5173", origin: "http://localhost:5173", "sec-fetch-site": "same-origin" }, ...patch };
  const response = { statusCode: 200, headers: {}, body: "", setHeader(key, value) { this.headers[key.toLowerCase()] = value; },
    end(value) { this.body = value; } };
  await middleware(request, response, () => { forwarded = true; });
  return { response, sent, forwarded };
}

test("local session returns only a HttpOnly cookie; token stays in server-to-server request", async () => {
  const { response, sent } = await call();
  assert.equal(response.statusCode, 200);
  assert.deepEqual(JSON.parse(response.body), { authenticated: true });
  assert.equal(response.headers["cache-control"], "no-store");
  assert.match(response.headers["set-cookie"][0], /HttpOnly/);
  assert.equal(JSON.parse(sent.body).token, token);
  assert.equal(sent.url, "http://127.0.0.1:8000/api/v1/auth/login");
  assert.ok(!JSON.stringify(response).includes(token));
});

for (const [label, patch] of [
  ["LAN client", { socket: { remoteAddress: "172.20.10.5" } }],
  ["forged forwarding header", { socket: { remoteAddress: "172.20.10.5" }, headers: {
    host: "localhost:5173", origin: "http://localhost:5173", "x-forwarded-for": "127.0.0.1" } }],
  ["other website", { headers: { host: "localhost:5173", origin: "https://evil.invalid" } }],
  ["DNS rebinding host", { headers: { host: "evil.invalid:5173", origin: "http://localhost:5173" } }],
  ["missing Origin", { headers: { host: "localhost:5173" } }],
  ["cross-site fetch", { headers: { host: "localhost:5173", origin: "http://localhost:5173", "sec-fetch-site": "cross-site" } }],
]) {
  test(`rejects ${label} before reading/forwarding credentials`, async () => {
    let calls = 0;
    const { response } = await call(patch, async () => { calls++; throw new Error(token); });
    assert.equal(response.statusCode, 403);
    assert.equal(calls, 0);
    assert.ok(!response.body.includes(token));
  });
}

test("GET cannot open a session; query strings cannot carry credentials", async () => {
  assert.equal((await call({ method: "GET" })).response.statusCode, 405);
  assert.equal((await call({ url: "/__local/session?token=not-used" })).response.statusCode, 400);
  assert.equal((await call({ url: "/ordinary-page" })).forwarded, true);
});

test("upstream failures never expose credentials or internal errors", async () => {
  const { response } = await call({}, async () => { throw new Error(token); });
  assert.equal(response.statusCode, 503);
  assert.ok(!response.body.includes(token));
  const rejected = await call({}, async () => new Response(token, { status: 401 }));
  assert.equal(rejected.response.statusCode, 503);
  assert.ok(!rejected.response.body.includes(token));
});

test("no cookie is issued if upstream omits HttpOnly", async () => {
  const { response } = await call({}, async () => new Response("{}", { headers: { "Set-Cookie": "asd_operator=unsafe" } }));
  assert.equal(response.statusCode, 503);
  assert.equal(response.headers["set-cookie"], undefined);
});

test("reuses a quoted local token without changing its value", async () => {
  writeFileSync(credentialsFile, `OPERATOR_TOKEN = "${token}"\r\n`);
  try {
    const { response, sent } = await call();
    assert.equal(response.statusCode, 200);
    assert.equal(JSON.parse(sent.body).token, token);
  } finally {
    writeFileSync(credentialsFile, `OPERATOR_TOKEN=${token}\n`);
  }
});
