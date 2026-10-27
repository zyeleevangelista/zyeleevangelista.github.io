"use strict";

import { cors, checkAccess, json, graphGet, reportError } from "../lib/facebook-photo-utils.js";

function allowedImageUrl(value) {
  let url;
  try { url = new URL(value); } catch { return null; }
  const host = url.hostname.toLowerCase();
  if (url.protocol !== "https:" || url.username || url.password || url.port) return null;
  if (host === "fbcdn.net" || host.endsWith(".fbcdn.net") ||
      host === "fbsbx.com" || host.endsWith(".fbsbx.com") ||
      host === "facebook.com" || host.endsWith(".facebook.com")) return url;
  return null;
}

async function fetchImage(source) {
  let current = allowedImageUrl(source);
  if (!current) throw Error("Meta supplied an unsupported image URL.");
  for (let hop = 0; hop < 4; hop++) {
    const response = await fetch(current, {
      method: "GET",
      redirect: "manual",
      headers: { "User-Agent": "PageImageExport/1.0" },
      signal: AbortSignal.timeout(25000)
    });
    if (response.status >= 300 && response.status < 400) {
      const target = new URL(response.headers.get("location") || "", current);
      current = allowedImageUrl(target.href);
      if (!current) throw Error("Photo redirected outside approved Meta image hosts.");
      continue;
    }
    if (!response.ok) {
      const e = new Error("Photo unavailable or its temporary image URL expired.");
      e.status = 502;
      throw e;
    }
    const contentType = (response.headers.get("content-type") || "").toLowerCase();
    if (!contentType.startsWith("image/") || contentType.includes("svg") || !response.body) {
      throw Error("Meta returned unsupported image data.");
    }
    if (Number(response.headers.get("content-length") || 0) > 25000000) {
      const error = new Error("Image exceeds the 25 MB per-image safety limit.");
      error.status = 413;
      throw error;
    }
    return { response, contentType };
  }
  throw Error("Too many image redirects.");
}

export default async function handler(req, res) {
  if (cors(req, res)) return;
  if (req.method !== "GET") return json(res, 405, { error: "GET required." });
  if (!checkAccess(req, res)) return;
  try {
    const photoId = String(req.query.id || "");
    if (!/^\d{5,30}$/.test(photoId)) throw Error("Invalid numeric photo ID.");
    const photo = await graphGet(encodeURIComponent(photoId), { fields: "images" });
    const variants = Array.isArray(photo.images) ? photo.images : [];
    const largest = [...variants].sort((a, b) =>
      (Number(b.width) || 0) * (Number(b.height) || 0) -
      (Number(a.width) || 0) * (Number(a.height) || 0))[0];
    if (!largest || typeof largest.source !== "string") {
      throw Error("No downloadable image is available for this photo.");
    }
    const { response, contentType } = await fetchImage(largest.source);
    const extension = contentType.includes("png") ? "png" :
      contentType.includes("webp") ? "webp" :
      contentType.includes("gif") ? "gif" :
      contentType.includes("heic") ? "heic" : "jpg";
    res.statusCode = 200;
    res.setHeader("Content-Type", contentType.split(";")[0]);
    res.setHeader("Content-Disposition", "attachment; filename=\"facebook-" + photoId + "." + extension + "\"");
    res.setHeader("Cache-Control", "no-store");
    // Stream one file at a time; no persistent image copies are saved by the server.
    let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length;
      if (size > 25000000) {
        res.destroy(new Error("Image exceeds size limit."));
        return;
      }
      res.write(chunk);
    }
    res.end();
  } catch (error) {
    if (res.headersSent) return res.destroy(error);
    return reportError(res, error);
  }
};
