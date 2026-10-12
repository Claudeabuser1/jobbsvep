// Jobbsvep AI server: one endpoint, POST /ai, that forwards a prompt to Claude.
// The API key stays here (ANTHROPIC_API_KEY) and never reaches the browser.
import http from "node:http";
import Anthropic from "@anthropic-ai/sdk";

const PORT = Number(process.env.PORT || 8080);
const ORIGINS = (process.env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
const MODELS = { quick: process.env.MODEL_QUICK || "claude-haiku-5-5", default: process.env.MODEL_DEFAULT || "claude-sonnet-5-5" };
const PER_IP_HOUR = Number(process.env.PER_IP_HOUR || 40);
const DAILY_CAP = Number(process.env.DAILY_CAP || 3000); // total requests per day, a hard stop on spend
const MAX_PROMPT = 120_000, MAX_BODY = 6_000_000;

const client = process.env.ANTHROPIC_API_KEY ? new Anthropic() : null;
const hits = new Map(); // ip -> timestamps within the last hour
let day = "", dayCount = 0;

function allow(ip) {
  const now = Date.now(), today = new Date().toISOString().slice(0, 10);
  if (today !== day) { day = today; dayCount = 0; hits.clear(); }
  if (dayCount >= DAILY_CAP) return false;
  const list = (hits.get(ip) || []).filter((t) => now - t < 3_600_000);
  if (list.length >= PER_IP_HOUR) { hits.set(ip, list); return false; }
  list.push(now); hits.set(ip, list); dayCount++;
  return true;
}

function send(res, status, body, origin) {
  const headers = { "content-type": "application/json", vary: "Origin" };
  if (origin) { headers["access-control-allow-origin"] = origin; headers["access-control-allow-headers"] = "content-type"; headers["access-control-allow-methods"] = "POST, OPTIONS"; }
  res.writeHead(status, headers);
  res.end(JSON.stringify(body));
}

http.createServer(async (req, res) => {
  const origin = req.headers.origin || "";
  const okOrigin = ORIGINS.length === 0 ? origin : ORIGINS.includes(origin) ? origin : "";
  if (req.method === "OPTIONS") return send(res, okOrigin ? 204 : 403, {}, okOrigin);
  if (req.method === "GET" && req.url === "/health") return send(res, 200, { ok: true, ai: Boolean(client) }, okOrigin);
  if (req.method !== "POST" || req.url !== "/ai") return send(res, 404, { error: "not_found" }, okOrigin);
  if (ORIGINS.length && !okOrigin) return send(res, 403, { error: "origin" }, "");
  if (!client) return send(res, 503, { error: "not_configured" }, okOrigin);

  const ip = String(req.headers["fly-client-ip"] || req.headers["x-forwarded-for"] || req.socket.remoteAddress || "").split(",")[0].trim();
  if (!allow(ip)) return send(res, 429, { error: "rate_limited" }, okOrigin);

  let raw = "", size = 0;
  try {
    for await (const chunk of req) { size += chunk.length; if (size > MAX_BODY) return send(res, 413, { error: "too_large" }, okOrigin); raw += chunk; }
    const body = JSON.parse(raw);
    const prompt = typeof body.prompt === "string" ? body.prompt : "";
    if (!prompt.trim()) return send(res, 400, { error: "empty" }, okOrigin);
    if (prompt.length > MAX_PROMPT) return send(res, 413, { error: "too_large" }, okOrigin);
    const tier = body.tier === "quick" ? "quick" : "default";
    const content = [];
    for (const img of Array.isArray(body.images) ? body.images.slice(0, 3) : []) {
      if (img && typeof img.data === "string" && /^image\/(jpeg|png|webp|gif)$/.test(img.type)) content.push({ type: "image", source: { type: "base64", media_type: img.type, data: img.data } });
    }
    content.push({ type: "text", text: prompt });

    const response = await client.messages.create({
      model: MODELS[tier],
      max_tokens: 8000,
      output_config: { effort: tier === "quick" ? "low" : "medium" },
      messages: [{ role: "user", content }],
    });
    if (response.stop_reason === "refusal") return send(res, 200, { refused: true }, okOrigin);
    let text = "";
    for (const block of response.content) if (block.type === "text") text += block.text;
    return send(res, 200, { text, truncated: response.stop_reason === "max_tokens" }, okOrigin);
  } catch (error) {
    if (error instanceof SyntaxError) return send(res, 400, { error: "bad_json" }, okOrigin);
    if (error instanceof Anthropic.RateLimitError) return send(res, 429, { error: "rate_limited" }, okOrigin);
    if (error instanceof Anthropic.AuthenticationError) return send(res, 503, { error: "not_configured" }, okOrigin);
    if (error instanceof Anthropic.BadRequestError) { console.error("bad request:", error.message); return send(res, 400, { error: "bad_request" }, okOrigin); }
    if (error instanceof Anthropic.APIError) { console.error("api error", error.status, error.message); return send(res, 502, { error: "upstream" }, okOrigin); }
    console.error(error);
    return send(res, 500, { error: "server" }, okOrigin);
  }
}).listen(PORT, () => console.log("jobbsvep-api on :" + PORT + (client ? "" : " (no ANTHROPIC_API_KEY set, /ai returns 503)")));
