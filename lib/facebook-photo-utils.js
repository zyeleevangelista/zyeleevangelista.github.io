"use strict";

/**
 * Shared safeguards for the Page photo tool.
 * Meta credentials stay in Vercel environment variables, never in browser code.
 */
const crypto = require("node:crypto");

const GRAPH_VERSION = "v26.0";
const GRAPH_ROOT = "https://graph.facebook.com/" + GRAPH_VERSION + "/";
const PAGE_SIZE = 100;

function json(res, status, payload) {
  res.status(status).setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  return res.end(JSON.stringify(payload));
}

function cors(req, res) {
  res.setHeader("Vary", "Origin");
  const origin = req.headers.origin || "";
  const allowed = (process.env.EXTRACTOR_ALLOWED_ORIGIN || "https://zyeleevangelista.github.io")
    .split(",").map((v) => v.trim()).filter(Boolean);
  if (origin && allowed.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-Extractor-Key");
  }
  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    res.end();
    return true;
  }
  return false;
}

function checkAccess(req, res, requireMetaToken = true) {
  const expected = process.env.EXTRACTOR_ACCESS_KEY;
  const token = process.env.META_PAGE_ACCESS_TOKEN;
  if (!expected || (requireMetaToken && !token)) {
    json(res, 503, { error: "Backend not configured. Set EXTRACTOR_ACCESS_KEY and, for Meta Page API mode, META_PAGE_ACCESS_TOKEN on Vercel." });
    return false;
  }
  const received = String(req.headers["x-extractor-key"] || "");
  const a = Buffer.from(received);
  const b = Buffer.from(expected);
  if (!received || a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    json(res, 401, { error: "Invalid access key. Enter the extractor key configured for your deployment." });
    return false;
  }
  return true;
}

function identifyPage(value) {
  if (typeof value !== "string" || value.length > 2000) throw Error("Enter a valid Facebook Page URL.");
  const input = value.trim();
  if (/^\d{5,30}$/.test(input)) return input;
  let parsed;
  try {
    parsed = new URL(input);
  } catch {
    throw Error("Paste the full Facebook Page URL, starting with https://.");
  }
  if (parsed.protocol !== "https:" ||
      !/^(?:www\.|m\.|web\.)?(?:facebook\.com|fb\.com)$/i.test(parsed.hostname)) {
    throw Error("Only Facebook Page URLs are supported.");
  }
  const queryId = parsed.searchParams.get("id");
  if (/^\d{5,30}$/.test(queryId || "")) return queryId;
  const segments = parsed.pathname.split("/").filter(Boolean);
  if (!segments.length) throw Error("Enter a Facebook Page URL, not the Facebook homepage.");
  if (segments[0].toLowerCase() === "pages") {
    const last = segments[segments.length - 1];
    if (/^\d{5,30}$/.test(last)) return last;
  }
  const reserved = new Set(["photos", "photo", "posts", "videos", "reels", "groups", "events", "watch", "share", "story.php", "permalink.php", "profile.php"]);
  const candidate = segments[0];
  if (reserved.has(candidate.toLowerCase()) || !/^[a-zA-Z0-9._-]{2,120}$/.test(candidate)) {
    throw Error("Couldn't identify a Page from that link. Enter its numeric Page ID instead.");
  }
  return candidate;
}

async function graphGet(path, params = {}) {
  const url = new URL(GRAPH_ROOT + path);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  let response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: { Authorization: "Bearer " + process.env.META_PAGE_ACCESS_TOKEN },
      signal: AbortSignal.timeout(20000)
    });
  } catch {
    const error = new Error("Meta's API did not respond. Try again later.");
    error.status = 502;
    throw error;
  }
  let body;
  try {
    body = await response.json();
  } catch {
    const error = new Error("Meta returned an invalid response.");
    error.status = 502;
    throw error;
  }
  if (!response.ok || body.error) {
    const apiCode = body.error && body.error.code;
    const raw = body.error && body.error.message;
    const err = new Error(typeof raw === "string" ? raw.slice(0, 400) : "Meta could not retrieve these photos.");
    err.status = response.status === 400 || response.status === 403 ? 403 : 502;
    err.code = apiCode;
    throw err;
  }
  return body;
}

function reportError(res, error) {
  const status = error.status || 400;
  return json(res, status, {
    error: error.message || "Could not complete the request.",
    code: error.code || undefined
  });
}

module.exports = { cors, checkAccess, json, identifyPage, graphGet, reportError, PAGE_SIZE };
