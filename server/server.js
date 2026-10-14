// Matchd API server.
//
// - POST /ai forwards a prompt to Claude. The API key stays here and never reaches the browser.
// - Every account has an AI budget in öre per period. Before each Claude call the server reserves the
//   worst-case cost of that call; afterwards it charges the real cost from the token usage. A call that
//   could exceed what is left is refused, so an account can never cost more than its plan's budget.
// - Paid plans go through Stripe Checkout. Plan budgets are set well below the price (see docs/PRICING.md).
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import Anthropic from "@anthropic-ai/sdk";
import Stripe from "stripe";

const env = process.env;
const PORT = Number(env.PORT || 8080);
const ORIGINS = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
const SITE_URL = (env.SITE_URL || ORIGINS[0] || "http://localhost:8766").replace(/\/$/, "") + "/";
const DATA_DIR = env.DATA_DIR || path.join(path.dirname(new URL(import.meta.url).pathname), "data");
const USD_SEK = Number(env.USD_SEK || 11); // a little above the real rate on purpose: costs are over- rather than under-estimated
const PER_IP_HOUR = Number(env.PER_IP_HOUR || 40);
const NEW_ACCOUNTS_PER_IP_DAY = Number(env.NEW_ACCOUNTS_PER_IP_DAY || 5);
const FREE_DAILY_ORE = Number(env.FREE_DAILY_ORE || 1000); // all free users together may cost at most this per day (10 kr)
const MAX_PROMPT = 120_000, MAX_BODY = 6_000_000;
const DAY = 86_400_000;

// What each plan costs and how much AI it may use per period. Budgets are in öre of real Claude cost.
const PLANS = {
  free: { name: "Gratis", price_ore: 0, budget_ore: Number(env.FREE_BUDGET_ORE || 150), days: 30 },
  week: { name: "Vecka", price_ore: 4900, budget_ore: Number(env.WEEK_BUDGET_ORE || 600), days: 7, stripePrice: env.STRIPE_PRICE_WEEK, mode: "payment" },
  month: { name: "Månad", price_ore: 12900, budget_ore: Number(env.MONTH_BUDGET_ORE || 1800), days: 30, stripePrice: env.STRIPE_PRICE_MONTH, mode: "subscription" },
  quarter: { name: "3 månader", price_ore: 29900, budget_ore: Number(env.QUARTER_BUDGET_ORE || 5400), days: 90, stripePrice: env.STRIPE_PRICE_QUARTER, mode: "payment" },
};
const LETTER_ORE = 30; // typical cost of one drafted application, used only to show "about N applications left"

// Claude models and their prices in USD per million tokens.
const MODELS = {
  quick: { id: env.MODEL_QUICK || "claude-haiku-5-5", in: 0.10, out: 0.50, maxTokens: 3000, effort: "low" },
  default: { id: env.MODEL_DEFAULT || "claude-sonnet-5-5", in: 2.0, out: 10.0, maxTokens: 4000, effort: "medium" },
};
const usdToOre = (usd) => usd * USD_SEK * 100;

const anthropic = env.ANTHROPIC_API_KEY ? new Anthropic() : null;
const stripe = env.STRIPE_SECRET_KEY ? new Stripe(env.STRIPE_SECRET_KEY) : null;
const MOCK = env.MOCK_AI === "1"; // local testing without a key

/* ---------- tiny JSON store on the Fly volume ---------- */
fs.mkdirSync(DATA_DIR, { recursive: true });
const DB_FILE = path.join(DATA_DIR, "db.json");
let db = { accounts: {}, tokens: {}, customers: {}, sessions: {}, newByIp: {}, free: { day: "", ore: 0 } };
try { db = Object.assign(db, JSON.parse(fs.readFileSync(DB_FILE, "utf8"))); } catch (_) {}
let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const tmp = DB_FILE + ".tmp";
    fs.writeFileSync(tmp, JSON.stringify(db));
    fs.renameSync(tmp, DB_FILE);
  }, 300);
}
const today = () => new Date().toISOString().slice(0, 10);

/* ---------- accounts and budgets ---------- */
function newAccount() {
  const id = crypto.randomBytes(9).toString("base64url");
  const token = "jsv_" + crypto.randomBytes(24).toString("base64url");
  const now = Date.now();
  db.accounts[id] = { plan: "free", used_ore: 0, reserved_ore: 0, period_end: now + PLANS.free.days * DAY, created: now };
  db.tokens[token] = id;
  save();
  return { id, token };
}
function accountFrom(req) {
  const m = String(req.headers.authorization || "").match(/^Bearer (jsv_[A-Za-z0-9_-]{20,})$/);
  const id = m && db.tokens[m[1]];
  return id && db.accounts[id] ? { id, acc: db.accounts[id] } : null;
}
// Roll the period over when it has ended: paid plans fall back to free unless Stripe renewed them.
function refresh(acc) {
  const now = Date.now();
  if (now < acc.period_end) return acc;
  if (acc.plan !== "free") acc.plan = "free";
  acc.used_ore = 0;
  acc.period_end = now + PLANS.free.days * DAY;
  save();
  return acc;
}
function left(acc) { return Math.max(0, PLANS[acc.plan].budget_ore - acc.used_ore - (acc.reserved_ore || 0)); }
function status(acc) {
  const p = PLANS[acc.plan], remaining = left(acc);
  return { plan: acc.plan, plan_name: p.name, budget_ore: p.budget_ore, remaining_ore: Math.floor(remaining),
    est_letters: Math.floor(remaining / LETTER_ORE), period_end: acc.period_end, can_manage: Boolean(acc.customer && stripe),
    payments: Boolean(stripe && PLANS.week.stripePrice && PLANS.month.stripePrice) };
}
function applyPlan(acc, plan, periodEndMs, customer, subscription) {
  acc.plan = plan;
  acc.used_ore = 0;
  acc.period_end = periodEndMs || Date.now() + PLANS[plan].days * DAY;
  if (customer) { acc.customer = customer; }
  if (subscription) acc.subscription = subscription;
  save();
}

/* ---------- limits that protect you from abuse ---------- */
const hits = new Map();
function ipAllowed(ip) {
  const now = Date.now(), list = (hits.get(ip) || []).filter((t) => now - t < 3_600_000);
  if (list.length >= PER_IP_HOUR) { hits.set(ip, list); return false; }
  list.push(now); hits.set(ip, list);
  return true;
}
function freeDayLeft() { if (db.free.day !== today()) db.free = { day: today(), ore: 0 }; return FREE_DAILY_ORE - db.free.ore; }

/* ---------- http helpers ---------- */
function send(res, status, body, origin) {
  const headers = { "content-type": "application/json", vary: "Origin" };
  if (origin) Object.assign(headers, { "access-control-allow-origin": origin, "access-control-allow-headers": "content-type, authorization", "access-control-allow-methods": "GET, POST, OPTIONS" });
  res.writeHead(status, headers);
  res.end(JSON.stringify(body));
}
async function readBody(req, limit) {
  const chunks = []; let size = 0;
  for await (const c of req) { size += c.length; if (size > limit) throw Object.assign(new Error("too large"), { status: 413 }); chunks.push(c); }
  return Buffer.concat(chunks);
}
const clientIp = (req) => String(req.headers["fly-client-ip"] || req.headers["x-forwarded-for"] || req.socket.remoteAddress || "").split(",")[0].trim();

/* ---------- Claude ---------- */
async function callClaude(model, content) {
  if (MOCK) {
    const chars = content.reduce((n, b) => n + (b.text ? b.text.length : 1600 * 3), 0);
    return { text: '{"mock":true}', usage: { input_tokens: Math.ceil(chars / 3), output_tokens: 600 }, refused: false, truncated: false };
  }
  const response = await anthropic.messages.create({
    model: model.id,
    max_tokens: model.maxTokens,
    output_config: { effort: model.effort },
    messages: [{ role: "user", content }],
  });
  let text = "";
  for (const block of response.content) if (block.type === "text") text += block.text;
  return { text, usage: response.usage, refused: response.stop_reason === "refusal", truncated: response.stop_reason === "max_tokens" };
}
function costOre(model, usage) {
  const input = (usage.input_tokens || 0) + (usage.cache_creation_input_tokens || 0) * 1.25 + (usage.cache_read_input_tokens || 0) * 0.1;
  return usdToOre((input * model.in + (usage.output_tokens || 0) * model.out) / 1e6);
}

async function handleAi(req, res, origin, who) {
  if (!anthropic && !MOCK) return send(res, 503, { error: "not_configured" }, origin);
  const body = JSON.parse((await readBody(req, MAX_BODY)).toString("utf8"));
  const prompt = typeof body.prompt === "string" ? body.prompt : "";
  if (!prompt.trim()) return send(res, 400, { error: "empty" }, origin);
  if (prompt.length > MAX_PROMPT) return send(res, 413, { error: "too_large" }, origin);
  const model = body.tier === "quick" ? MODELS.quick : MODELS.default;
  const content = [];
  for (const img of Array.isArray(body.images) ? body.images.slice(0, 3) : []) {
    if (img && typeof img.data === "string" && /^image\/(jpeg|png|webp|gif)$/.test(img.type)) content.push({ type: "image", source: { type: "base64", media_type: img.type, data: img.data } });
  }
  content.push({ type: "text", text: prompt });

  // Reserve the worst case: every character as a token at a third of a character, plus the full output limit.
  const acc = refresh(who.acc);
  const worst = usdToOre(((Math.ceil(prompt.length / 3) + (content.length - 1) * 1600) * model.in + model.maxTokens * model.out) / 1e6);
  if (left(acc) < worst) return send(res, 402, { error: "no_credits", ...status(acc) }, origin);
  if (acc.plan === "free" && freeDayLeft() < worst) return send(res, 402, { error: "free_pool_empty", ...status(acc) }, origin);
  acc.reserved_ore = (acc.reserved_ore || 0) + worst;
  if (acc.plan === "free") db.free.ore += worst;
  let r;
  try {
    r = await callClaude(model, content);
  } catch (error) {
    acc.reserved_ore = Math.max(0, acc.reserved_ore - worst);
    if (acc.plan === "free") db.free.ore -= worst;
    save();
    throw error;
  }
  const cost = costOre(model, r.usage);
  acc.reserved_ore = Math.max(0, acc.reserved_ore - worst);
  acc.used_ore += cost;
  if (acc.plan === "free") db.free.ore += cost - worst;
  save();
  return send(res, 200, { text: r.text, refused: r.refused, truncated: r.truncated, cost_ore: Math.round(cost * 100) / 100, ...status(acc) }, origin);
}

/* ---------- Stripe ---------- */
async function confirmCheckout(sessionId) {
  if (db.sessions[sessionId]) return db.sessions[sessionId];
  const s = await stripe.checkout.sessions.retrieve(sessionId);
  if (s.status !== "complete" || !["paid", "no_payment_required"].includes(s.payment_status)) return null;
  const accountId = s.client_reference_id || (s.metadata && s.metadata.account);
  const plan = s.metadata && s.metadata.plan;
  const acc = db.accounts[accountId];
  if (!acc || !PLANS[plan] || plan === "free") return null;
  let end = Date.now() + PLANS[plan].days * DAY;
  if (s.mode === "subscription" && s.subscription) {
    const sub = await stripe.subscriptions.retrieve(typeof s.subscription === "string" ? s.subscription : s.subscription.id);
    const periodEnd = sub.current_period_end || (sub.items && sub.items.data[0] && sub.items.data[0].current_period_end);
    if (periodEnd) end = periodEnd * 1000;
  }
  const customer = typeof s.customer === "string" ? s.customer : s.customer && s.customer.id;
  applyPlan(acc, plan, end, customer, typeof s.subscription === "string" ? s.subscription : s.subscription && s.subscription.id);
  if (customer) db.customers[customer] = accountId;
  db.sessions[sessionId] = accountId;
  save();
  return accountId;
}
async function handleWebhook(req, res) {
  const raw = await readBody(req, 1_000_000);
  let event;
  try { event = stripe.webhooks.constructEvent(raw, req.headers["stripe-signature"], env.STRIPE_WEBHOOK_SECRET); }
  catch (e) { return send(res, 400, { error: "signature" }, ""); }
  const o = event.data.object;
  if (event.type === "checkout.session.completed") await confirmCheckout(o.id);
  if (event.type === "invoice.paid") {
    const accId = db.customers[o.customer], acc = accId && db.accounts[accId];
    const line = o.lines && o.lines.data && o.lines.data[0];
    if (acc && line && line.period && line.period.end) applyPlan(acc, "month", line.period.end * 1000);
  }
  if (event.type === "customer.subscription.deleted") {
    const accId = db.customers[o.customer], acc = accId && db.accounts[accId];
    if (acc && acc.plan === "month") { acc.plan = "free"; acc.used_ore = 0; acc.period_end = Date.now() + PLANS.free.days * DAY; save(); }
  }
  return send(res, 200, { received: true }, "");
}

/* ---------- routes ---------- */
http.createServer(async (req, res) => {
  const origin = req.headers.origin || "";
  const okOrigin = ORIGINS.length === 0 ? origin : ORIGINS.includes(origin) ? origin : "";
  const url = new URL(req.url, "http://x");
  try {
    if (req.method === "POST" && url.pathname === "/stripe/webhook") return stripe ? handleWebhook(req, res) : send(res, 404, {}, "");
    if (req.method === "OPTIONS") return send(res, okOrigin ? 204 : 403, {}, okOrigin);
    if (req.method === "GET" && url.pathname === "/health") return send(res, 200, { ok: true, ai: Boolean(anthropic) || MOCK, payments: Boolean(stripe) }, okOrigin);
    if (ORIGINS.length && !okOrigin) return send(res, 403, { error: "origin" }, "");
    const ip = clientIp(req);
    if (!ipAllowed(ip)) return send(res, 429, { error: "rate_limited" }, okOrigin);

    if (req.method === "POST" && url.pathname === "/session") {
      const d = today();
      if (db.newByIp.day !== d) db.newByIp = { day: d };
      if ((db.newByIp[ip] || 0) >= NEW_ACCOUNTS_PER_IP_DAY) return send(res, 429, { error: "rate_limited" }, okOrigin);
      db.newByIp[ip] = (db.newByIp[ip] || 0) + 1;
      const { id, token } = newAccount();
      return send(res, 200, { token, ...status(db.accounts[id]) }, okOrigin);
    }
    const who = accountFrom(req);
    if (!who) return send(res, 401, { error: "no_account" }, okOrigin);

    if (req.method === "GET" && url.pathname === "/me") return send(res, 200, status(refresh(who.acc)), okOrigin);
    if (req.method === "POST" && url.pathname === "/ai") return handleAi(req, res, okOrigin, who);

    if (req.method === "POST" && url.pathname === "/checkout") {
      if (!stripe) return send(res, 503, { error: "payments_not_configured" }, okOrigin);
      const { plan } = JSON.parse((await readBody(req, 10_000)).toString("utf8") || "{}");
      const p = PLANS[plan];
      if (!p || plan === "free" || !p.stripePrice) return send(res, 400, { error: "plan" }, okOrigin);
      const session = await stripe.checkout.sessions.create({
        mode: p.mode,
        line_items: [{ price: p.stripePrice, quantity: 1 }],
        client_reference_id: who.id,
        metadata: { account: who.id, plan },
        ...(p.mode === "subscription" ? { subscription_data: { metadata: { account: who.id } } } : { customer_creation: "always" }),
        ...(who.acc.customer ? { customer: who.acc.customer } : {}),
        allow_promotion_codes: true,
        locale: "auto",
        success_url: SITE_URL + "?checkout={CHECKOUT_SESSION_ID}",
        cancel_url: SITE_URL + "?checkout=cancel",
      });
      return send(res, 200, { url: session.url }, okOrigin);
    }
    if (req.method === "GET" && url.pathname === "/checkout/confirm") {
      if (!stripe) return send(res, 503, { error: "payments_not_configured" }, okOrigin);
      const accountId = await confirmCheckout(String(url.searchParams.get("session_id") || ""));
      if (!accountId) return send(res, 409, { error: "not_paid" }, okOrigin);
      if (accountId !== who.id) { // paid from another device: hand this device the paying account
        const token = Object.keys(db.tokens).find((t) => db.tokens[t] === accountId);
        return send(res, 200, { token, ...status(db.accounts[accountId]) }, okOrigin);
      }
      return send(res, 200, status(who.acc), okOrigin);
    }
    if (req.method === "POST" && url.pathname === "/portal") {
      if (!stripe || !who.acc.customer) return send(res, 400, { error: "no_subscription" }, okOrigin);
      const s = await stripe.billingPortal.sessions.create({ customer: who.acc.customer, return_url: SITE_URL });
      return send(res, 200, { url: s.url }, okOrigin);
    }
    return send(res, 404, { error: "not_found" }, okOrigin);
  } catch (error) {
    if (error.status === 413) return send(res, 413, { error: "too_large" }, okOrigin);
    if (error instanceof SyntaxError) return send(res, 400, { error: "bad_json" }, okOrigin);
    if (error instanceof Anthropic.RateLimitError) return send(res, 429, { error: "rate_limited" }, okOrigin);
    if (error instanceof Anthropic.AuthenticationError) return send(res, 503, { error: "not_configured" }, okOrigin);
    if (error instanceof Anthropic.BadRequestError) { console.error("claude bad request:", error.message); return send(res, 400, { error: "bad_request" }, okOrigin); }
    if (error instanceof Anthropic.APIError) { console.error("claude error", error.status, error.message); return send(res, 502, { error: "upstream" }, okOrigin); }
    if (error && error.type && String(error.type).startsWith("Stripe")) { console.error("stripe", error.message); return send(res, 502, { error: "payments" }, okOrigin); }
    console.error(error);
    return send(res, 500, { error: "server" }, okOrigin);
  }
}).listen(PORT, () => console.log("jobbsvep-api on :" + PORT + (anthropic ? "" : MOCK ? " (mock AI)" : " (no ANTHROPIC_API_KEY: /ai returns 503)") + (stripe ? ", payments on" : ", payments off")));
