/**
 * Werkroom "Ask the Library" — Cloudflare Worker proxy.
 *
 * Holds the Anthropic API key (Worker secret, never shipped to the browser),
 * retrieves relevant facts from the site's knowledge pack, and asks Claude to
 * answer ONLY from those facts, with routes the site can link to.
 *
 * Deploy: see README.md in this folder. Secret required: ANTHROPIC_API_KEY.
 */
const KB_URL = "https://anotterbryan.github.io/werkroom/kb/facts.json";
const ALLOW_ORIGINS = ["https://anotterbryan.github.io", "http://localhost:8000", "http://127.0.0.1:8000"];
const MODEL = "claude-haiku-4-5-20251001";
const MAX_FACTS = 40;

const cors = (origin) => ({
  "Access-Control-Allow-Origin": ALLOW_ORIGINS.includes(origin) ? origin : ALLOW_ORIGINS[0],
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
});

async function loadKB() {
  const cache = caches.default;
  const req = new Request(KB_URL);
  let res = await cache.match(req);
  if (!res) {
    res = await fetch(KB_URL, { cf: { cacheTtl: 3600 } });
    if (res.ok) await cache.put(req, res.clone());
  }
  return (await res.json()).facts;
}

function tokenize(s) {
  return (s.toLowerCase().match(/[a-z0-9'’]+/g) || []).filter(w => w.length > 2);
}

function retrieve(facts, question, n) {
  const qt = tokenize(question);
  const scored = facts.map(f => {
    const hay = (f.t + " " + f.k).toLowerCase();
    let score = 0;
    for (const w of qt) if (hay.includes(w)) score += w.length > 4 ? 2 : 1;
    // exact keyword field hits weigh extra (names, season labels)
    for (const w of qt) if (f.k.includes(w)) score += 2;
    return { f, score };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score);
  return scored.slice(0, n).map(x => x.f);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
    if (request.method !== "POST")
      return new Response(JSON.stringify({ error: "POST a JSON body: {question}" }),
        { status: 405, headers: { "Content-Type": "application/json", ...cors(origin) } });
    try {
      const { question, history = [] } = await request.json();
      if (!question || question.length > 500)
        return new Response(JSON.stringify({ error: "question required (max 500 chars)" }),
          { status: 400, headers: { "Content-Type": "application/json", ...cors(origin) } });

      const facts = retrieve(await loadKB(), question, MAX_FACTS);
      const context = facts.map((f, i) => `[${i + 1}|${f.l}] ${f.t}`).join("\n");

      const messages = [
        ...history.slice(-6).map(h => ({ role: h.role, content: h.content })),
        { role: "user", content: question },
      ];
      const system =
        "You are the Werkroom Librarian, the resident expert of a RuPaul's Drag Race fan database. " +
        "Answer the visitor's question using ONLY the facts below. If the facts don't contain the answer, " +
        "say so plainly and suggest what to browse instead. Keep answers short, warm, and a little playful. " +
        "End with up to 2 source tags copied exactly as they appear, e.g. [3|queen:Q0001], for the facts you used.\n\nFACTS:\n" + context;

      const api = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
          "content-type": "application/json",
        },
        body: JSON.stringify({ model: MODEL, max_tokens: 600, system, messages }),
      });
      if (!api.ok) {
        const detail = await api.text();
        return new Response(JSON.stringify({ error: "upstream", detail: detail.slice(0, 300) }),
          { status: 502, headers: { "Content-Type": "application/json", ...cors(origin) } });
      }
      const out = await api.json();
      const text = (out.content || []).map(b => b.text || "").join("");
      // lift [n|route] tags into structured links
      const links = [...text.matchAll(/\[(\d+)\|([a-z]+:?[A-Za-z0-9]*)\]/g)].map(m => m[2]);
      const clean = text.replace(/\s*\[\d+\|[a-z]+:?[A-Za-z0-9]*\]/g, "").trim();
      return new Response(JSON.stringify({ answer: clean, links: [...new Set(links)].slice(0, 3) }),
        { headers: { "Content-Type": "application/json", ...cors(origin) } });
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e).slice(0, 200) }),
        { status: 500, headers: { "Content-Type": "application/json", ...cors(origin) } });
    }
  },
};
