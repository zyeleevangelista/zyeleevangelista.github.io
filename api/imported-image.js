"use strict";

import { cors, checkAccess, json, reportError } from "../lib/facebook-photo-utils.js";

// Download only user-supplied Facebook CDN image URLs from the HTML file.
// Not an arbitrary URL proxy; does not send Facebook cookies or read HTML.
function imageURL(input) {
  if (typeof input !== "string" || input.length > 3500) return null;
  let url;
  try { url = new URL(input); } catch { return null; }
  if (url.protocol !== "https:" || url.username || url.password ||
      (url.port && url.port !== "443")) return null;
  const host = url.hostname.toLowerCase();
  if (!(host.startsWith("scontent.") && host.endsWith(".fbcdn.net"))) return null;
  if (!/\.(?:jpe?g|png|webp|gif)$/i.test(url.pathname)) return null;
  return url;
}

export default async function handler(req, res) {
  if (cors(req, res)) return;
  if (req.method !== "POST") return json(res, 405, { error: "POST required." });
  if (!checkAccess(req, res, false)) return;
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
    let target = imageURL(body.url);
    if (!target) return json(res, 400, { error: "Only HTTPS Facebook CDN image URLs from saved HTML are supported." });

    let response;
    for (let redirect = 0; redirect < 4; redirect++) {
      response = await fetch(target, {
        method: "GET", redirect: "manual",
        signal: AbortSignal.timeout(25000)
      });
      if (response.status >= 300 && response.status < 400) {
        let dest;
        try { dest = new URL(response.headers.get("location") || "", target); } catch { dest = null; }
        target = dest && imageURL(dest.href);
        if (!target) return json(res, 403, { error: "Image redirected outside authorized Facebook CDN hosts." });
        continue;
      }
      break;
    }
    if (!response || !response.ok) {
      return json(res, 502, { error: "Facebook CDN image unavailable or link expired." });
    }
    const mime = (response.headers.get("content-type") || "").split(";")[0].toLowerCase();
    if (!/^image\/(?:jpeg|png|webp|gif)$/.test(mime)) {
      return json(res, 415, { error: "The source did not return a supported image." });
    }
    if (Number(response.headers.get("content-length") || 0) > 25000000) {
      return json(res, 413, { error: "Photo exceeds the 25 MB size limit." });
    }
    res.setHeader("Content-Type", mime);
    res.setHeader("Cache-Control", "no-store");
    res.statusCode = 200;
    let bytes = 0;
    for await (const chunk of response.body) {
      bytes += chunk.length;
      if (bytes > 25000000) return res.destroy(new Error("Image too large."));
      res.write(chunk);
    }
    res.end();
  } catch (err) {
    if (res.headersSent) return res.destroy(err);
    return reportError(res, err);
  }
};
