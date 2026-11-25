// POST /api/v — 병 상세를 연 횟수를 (UTC 날짜, 병 id) 하루 합계로만 센다(S7). 티어·종합 점수·트렌드지수 계산에는 넣지 않는다.
// IP·User-Agent·쿠키·리퍼러는 저장하지도 로그로 남기지도 않는다(console.* 금지). UA 는 크롤러 판정에만 쓰고 버린다.
// env.DB(D1 바인딩)가 없으면 아무것도 하지 않고 204 를 돌려준다(D1 을 만들기 전에 배포해도 오류 없음).
import { IDS } from "./_ids.js";   // build.py 가 bottles.json 으로 만드는 유효 병 id 목록

export const CAP = 200;            // 병당 하루 상한
export const MAX_BODY = 64;        // 본문 최대 바이트
export const ID_RE = /^[a-z0-9-]{1,60}$/;
export const BOT_RE = /bot|crawl|spider|slurp|scrap|fetch|curl|wget|python|java\/|go-http|okhttp|axios|node-fetch|httpclient|libwww|headless|phantom|puppeteer|playwright|selenium|lighthouse|pagespeed|preview|facebookexternalhit|embedly|whatsapp|telegram|discord|slack|monitor|uptime|pingdom/i;
export const SCHEMA = "CREATE TABLE IF NOT EXISTS v(d TEXT NOT NULL, id TEXT NOT NULL, n INTEGER NOT NULL, PRIMARY KEY(d, id))";
const UPSERT = "INSERT INTO v(d, id, n) VALUES(?1, ?2, 1) ON CONFLICT(d, id) DO UPDATE SET n = n + 1 WHERE n < ?3";

const res = (s) => new Response(null, { status: s, headers: { "Cache-Control": "no-store" } });

// 같은 출처에서 보낸 요청만 받는다. 브라우저의 sendBeacon 은 Origin 을 붙이고, Sec-Fetch-Site 는 붙는 브라우저에서만 본다
export function sameOrigin(request) {
  const own = new URL(request.url).origin, o = request.headers.get("Origin"), s = request.headers.get("Sec-Fetch-Site");
  if (s && s !== "same-origin") return false;
  return o === own;
}

export async function count(db, id, day) {
  const run = () => db.prepare(UPSERT).bind(day, id, CAP).run();
  try { await run(); }
  catch (e) {   // 테이블이 아직 없을 때만 한 번 만들고 다시 시도한다(매 요청마다 CREATE 하지 않음)
    if (!/no such table/i.test(String(e && e.message))) return false;
    await db.prepare(SCHEMA).run(); await run();
  }
  return true;
}

// Pages Functions 진입점. 방법별 처리기를 섞지 않고 하나로 받아 POST 만 처리한다
export async function onRequest({ request, env }) {
  if (request.method !== "POST") return new Response(null, { status: 405, headers: { "Allow": "POST", "Cache-Control": "no-store" } });
  return handle(request, env);
}

export async function handle(request, env) {
  if (!env || !env.DB) return res(204);
  if (!sameOrigin(request)) return res(403);
  const len = Number(request.headers.get("Content-Length") || 0);
  if (len > MAX_BODY) return res(413);
  const raw = new Uint8Array(await request.arrayBuffer());
  if (raw.length > MAX_BODY) return res(413);
  const id = new TextDecoder().decode(raw).trim();
  if (!ID_RE.test(id) || !IDS.has(id)) return res(400);
  const ua = request.headers.get("User-Agent") || "";
  if (!ua || BOT_RE.test(ua)) return res(204);   // 크롤러·UA 없는 요청은 세지 않지만 오류도 내지 않는다
  try { await count(env.DB, id, new Date().toISOString().slice(0, 10)); } catch (e) { /* 집계 실패는 조용히 넘긴다(기록 없음) */ }
  return res(204);
}
