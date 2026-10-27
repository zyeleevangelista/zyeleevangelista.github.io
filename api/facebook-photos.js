"use strict";

import { cors, checkAccess, json, identifyPage, graphGet, reportError, PAGE_SIZE } from "../lib/facebook-photo-utils.js";

export default async function handler(req, res) {
  if (cors(req, res)) return;
  if (req.method !== "POST") return json(res, 405, { error: "POST required." });
  if (!checkAccess(req, res)) return;
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
    let reference = body.pageId ? String(body.pageId) : identifyPage(body.pageUrl || "");
    if (!/^[a-zA-Z0-9._-]{2,120}$/.test(reference)) throw Error("Invalid Page reference.");
    let pageId = reference;
    let pageName = "";
    if (!/^\d{5,30}$/.test(reference)) {
      const page = await graphGet(encodeURIComponent(reference), { fields: "id,name" });
      if (!/^\d{5,30}$/.test(String(page.id || ""))) {
        throw Error("Meta could not resolve this Page. Provide its numeric Page ID.");
      }
      pageId = String(page.id);
      pageName = String(page.name || "").slice(0, 150);
    }
    const after = body.after === undefined || body.after === null ? "" : String(body.after);
    if (after && (after.length > 1024 || !/^[a-zA-Z0-9+/_=-]+$/.test(after))) {
      throw Error("Invalid pagination cursor.");
    }
    const payload = await graphGet(encodeURIComponent(pageId) + "/photos", {
      type: "uploaded",
      fields: "id,name,created_time,images",
      limit: PAGE_SIZE,
      after
    });
    const photos = (Array.isArray(payload.data) ? payload.data : [])
      .filter((p) => /^\d{5,30}$/.test(String(p.id || "")))
      .map((p) => {
        const variants = Array.isArray(p.images) ? p.images : [];
        const preview = variants.length ? variants[variants.length - 1].source : "";
        return {
          id: String(p.id),
          caption: String(p.name || "").slice(0, 160),
          created: String(p.created_time || "").slice(0, 35),
          preview: typeof preview === "string" && /^https:\/\//.test(preview) ? preview : ""
        };
      });
    const cursor = payload.paging && payload.paging.next && payload.paging.cursors
      ? String(payload.paging.cursors.after || "") : "";
    return json(res, 200, {
      pageId,
      pageName,
      photos,
      nextCursor: cursor,
      notice: "Only uploaded photos Meta permits this token to read are returned."
    });
  } catch (error) {
    return reportError(res, error);
  }
};
