// GET /api/top — 최근 7일(오늘 UTC 포함) 병 id별 합계 상위 50개. 공개 자료이며 빌드 도구(tools/fetch_views.py)가 내려받아 data/views.json 으로 쓴다.
// 응답: {"week": 시작일, "to": 끝날, "top": [[id, n], …]}. env.DB 가 없거나 표가 없으면 {"week": null, "top": []}.
// 120일 지난 행은 호출 20번에 한 번꼴로 지운다(Cron 없이 정리).
export const DAYS = 7, LIMIT = 50, KEEP_DAYS = 120, PRUNE_P = 0.05;
const H = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=3600" };
const day = (t) => new Date(t).toISOString().slice(0, 10);
const out = (o) => new Response(JSON.stringify(o), { headers: H });

// Pages Functions 진입점. GET(과 HEAD)만 받는다
export async function onRequest({ request, env }) {
  if (request.method !== "GET" && request.method !== "HEAD") return new Response(null, { status: 405, headers: { "Allow": "GET", "Cache-Control": "no-store" } });
  return top(env, Date.now(), Math.random());
}

export async function top(env, now, rnd) {
  if (!env || !env.DB) return out({ week: null, top: [] });
  const from = day(now - (DAYS - 1) * 864e5), to = day(now);
  try {
    if (rnd < PRUNE_P) await env.DB.prepare("DELETE FROM v WHERE d < ?1").bind(day(now - KEEP_DAYS * 864e5)).run();
    const r = await env.DB.prepare("SELECT id, SUM(n) AS n FROM v WHERE d >= ?1 AND d <= ?2 GROUP BY id ORDER BY n DESC, id LIMIT ?3").bind(from, to, LIMIT).all();
    return out({ week: from, to, top: (r.results || []).map((x) => [x.id, Number(x.n)]) });
  } catch (e) {
    return out({ week: null, top: [] });   // 표가 아직 없음 등
  }
}
