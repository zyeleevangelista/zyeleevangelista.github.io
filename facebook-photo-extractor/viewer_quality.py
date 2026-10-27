#!/usr/bin/env python3
"""Collect the largest *available viewer rendition* of saved Facebook Page photos.

This is an optional, user-driven workflow. It opens actual photo posts in a
locally controlled Chromium session; it never asks for, exports or sends your
Facebook password/cookies. It is not an original-camera-file recovery tool.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from time import sleep
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile, ZIP_STORED


ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_BYTES = 25 * 1024 * 1024
PHOTO_ID = re.compile(r"^\d{5,30}$")


def verified_post(url: str) -> tuple[str, str] | None:
    try:
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        photo_id = query.get("fbid", [""])[0]
        album = query.get("set", [""])[0]
        if (
            parts.scheme == "https"
            and parts.hostname in ("www.facebook.com", "facebook.com")
            and parts.path == "/photo.php"
            and PHOTO_ID.fullmatch(photo_id)
            and album.startswith("pb.")
        ):
            return photo_id, album
    except ValueError:
        pass
    return None


class PhotoPostLinks(HTMLParser):
    """Restrict link selection to photo-post links that contain a photo thumbnail."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str, str] | None] = []
        self.photos: dict[str, dict] = {}

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "a":
            url = attr.get("href", "")
            parsed = verified_post(url)
            self.anchors.append((parsed[0], parsed[1], url) if parsed else None)
        elif tag == "img" and self.anchors:
            active = next((a for a in reversed(self.anchors) if a), None)
            if active and active[0] not in self.photos:
                self.photos[active[0]] = {
                    "id": active[0], "album": active[1],
                    "post": active[2], "thumbnail": attr.get("src", "")
                }

    def handle_endtag(self, tag):
        if tag == "a" and self.anchors:
            self.anchors.pop()


def parse_saved_gallery(source: str) -> list[dict]:
    parser = PhotoPostLinks()
    parser.feed(source)
    if not parser.photos:
        return []
    album = Counter(x["album"] for x in parser.photos.values()).most_common(1)[0][0]
    return [x for x in parser.photos.values() if x["album"] == album]


def create_post_index(photos: list[dict], path: Path) -> None:
    """Offline index can always be used to manually open full-sized posts."""
    parts = [
        "<!doctype html><html lang='en'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Original Facebook photo posts</title>",
        "<style>body{font:16px/1.6 system-ui,sans-serif;max-width:780px;margin:50px auto;"
        "padding:0 18px;color:#20302c}li{margin:7px 0}a{color:#116a58}</style>",
        "<h1>Facebook Page photo posts</h1>",
        "<p>Open each photo in Facebook's full-size viewer. Use its Download "
        "option if available. A Facebook rendition may still differ from the "
        "original camera upload.</p><ol>",
    ]
    for photo in photos:
        parts.append(
            '<li><a rel="noopener noreferrer" target="_blank" href="'
            + escape(photo["post"], quote=True) + '">Photo post '
            + escape(photo["id"]) + "</a></li>"
        )
    path.write_text("\n".join(parts + ["</ol></html>"]), encoding="utf-8")


def is_facebook_cdn_photo(url: str) -> bool:
    try:
        target = urlsplit(url)
        host = (target.hostname or "").lower()
        return (
            target.scheme == "https"
            and host.startswith("scontent.")
            and host.endswith(".fbcdn.net")
            and target.username is None
            and target.password is None
            and target.port in (None, 443)
        )
    except ValueError:
        return False


JS_PHOTO_CANDIDATES = """
({photoId, filenamePrefix}) => {
  const results = [];
  for (const image of document.querySelectorAll('img')) {
    const url = image.currentSrc || image.src || '';
    let host = '';
    try { host = new URL(url).hostname.toLowerCase(); } catch { continue; }
    if (!host.startsWith('scontent.') || !host.endsWith('.fbcdn.net')) continue;
    const width = image.naturalWidth || 0, height = image.naturalHeight || 0;
    if (width < 300 || height < 300) continue;
    // Do not capture unrelated images: the source URL must match the photo ID
    // or the CDN file prefix from its saved gallery image.
    const match = url.includes(photoId) ||
      (filenamePrefix.length >= 7 && url.includes(filenamePrefix));
    if (!match) continue;
    results.push({url, width, height, area: width * height});
  }
  return results.sort((a, b) => b.area - a.area);
}
"""


def photo_filename_prefix(thumbnail: str) -> str:
    name = Path(urlsplit(thumbnail).path).name
    match = re.match(r"([0-9]{6,16}_[0-9]{6,19})_", name)
    return match.group(1) if match else ""


def fetch_photo(context, candidate: dict, output: Path, index: int) -> dict:
    url = candidate["url"]
    if not is_facebook_cdn_photo(url):
        raise ValueError("Image host is not an approved Facebook CDN")
    response = context.request.get(
        url, headers={"Referer": "https://www.facebook.com/"},
        timeout=30000, max_redirects=3
    )
    if not response.ok or not is_facebook_cdn_photo(response.url):
        raise ValueError("Photo not accessible or redirected outside the Facebook CDN")
    kind = response.headers.get("content-type", "").split(";")[0].lower()
    if kind not in ALLOWED_TYPES:
        raise ValueError("Facebook did not serve a supported image")
    if int(response.headers.get("content-length", "0") or 0) > MAX_BYTES:
        raise ValueError("Photo larger than 25 MB")
    data = response.body()
    if not 1024 <= len(data) <= MAX_BYTES:
        raise ValueError("Image empty or exceeds 25 MB")
    filename = f"photo_{index:04d}_{candidate['width']}x{candidate['height']}{ALLOWED_TYPES[kind]}"
    (output / filename).write_bytes(data)
    return {"file": filename, "bytes": len(data),
            "width": candidate["width"], "height": candidate["height"]}


def main() -> int:
    cli = argparse.ArgumentParser(description="Collect high-resolution renditions from Page photo posts in a user-controlled browser.")
    cli.add_argument("source", type=Path, help="Saved Chrome/Brave Facebook Photos .html file")
    cli.add_argument("--limit", type=int, default=20, help="Number of posts (1–150; default 20)")
    cli.add_argument("--manual-only", action="store_true", help="Create clickable post links without browser automation")
    cli.add_argument("--output", type=Path, default=None, help="Output folder")
    args = cli.parse_args()

    if not args.source.is_file() or args.source.stat().st_size > 40 * 1024 * 1024:
        cli.error("Saved HTML not found or exceeds 40 MB")
    if not 1 <= args.limit <= 150:
        cli.error("--limit must be between 1 and 150")
    source = args.source.read_text(encoding="utf-8", errors="replace")
    posts = parse_saved_gallery(source)
    if not posts:
        print("No Page photo links found. Save the Page Photos gallery as 'Webpage, Complete'.")
        return 1
    posts = posts[:args.limit]
    output = args.output or (args.source.parent / "Facebook_Photo_Viewer_Quality")
    original = output
    n = 2
    while output.exists() or output.with_suffix(".zip").exists():
        output = Path(str(original) + f"_{n}")
        n += 1
    output.mkdir(parents=True)
    create_post_index(posts, output / "PHOTO_POST_LINKS.html")
    print(f"Identified {len(posts)} Page photo posts. Photo links saved for manual access.")
    if args.manual_only:
        print(f"Open: {output / 'PHOTO_POST_LINKS.html'}")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Missing Playwright. Install once: py -3 -m pip install playwright")
        print("Then install Chromium: py -3 -m playwright install chromium")
        print(f"You can still open the links in: {output / 'PHOTO_POST_LINKS.html'}")
        return 2

    manifest = {"captured": datetime.now().isoformat(timespec="seconds"),
                "posts": len(posts), "results": [],
                "notice": "These are the largest matching visible Facebook viewer images, NOT verified original uploads."}
    profile = Path.home() / ".facebook-photo-viewer-capture"
    print("A separate Chromium browser opens. Sign into Facebook there if necessary.")
    print("Login stays on your device in:", profile)
    print("Do not share this browser profile or the saved Facebook HTML.")
    with sync_playwright() as playwright:
        ctx = playwright.chromium.launch_persistent_context(
            str(profile), headless=False, viewport={"width": 1440, "height": 950},
            accept_downloads=True, args=["--disable-background-timer-throttling"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(posts[0]["post"], wait_until="domcontentloaded", timeout=35000)
        print("If Facebook asks you to sign in, complete it in the opened browser.")
        input("When the first photo is visible, press Enter here to start capturing...")
        for number, photo in enumerate(posts, start=1):
            result = {"index": number, "photo_id": photo["id"], "status": "skipped"}
            try:
                page.goto(photo["post"], wait_until="domcontentloaded", timeout=35000)
                page.wait_for_timeout(2500)
                prefix = photo_filename_prefix(photo["thumbnail"])
                candidates = page.evaluate(JS_PHOTO_CANDIDATES, {"photoId": photo["id"], "filenamePrefix": prefix})
                # Ignore tiny preview renditions. A viewer image is still not
                # guaranteed to be the full camera original.
                candidates = [c for c in candidates if c["width"] >= 600 and c["height"] >= 600]
                if not candidates:
                    result["reason"] = "Matching full viewer image not available."
                else:
                    chosen = candidates[0]
                    info = fetch_photo(ctx, chosen, output, number)
                    result.update(status="saved", **info)
            except Exception as error:
                result["reason"] = str(error)[:160]
            manifest["results"].append(result)
            status = result.get("file") or result.get("reason", "Unavailable")
            print(f"[{number}/{len(posts)}] {photo['id']}: {status}", flush=True)
            sleep(0.6)
        ctx.close()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive_path = output.with_suffix(".zip")
    with ZipFile(archive_path, "w", compression=ZIP_STORED) as archive:
        for file in output.iterdir():
            if file.is_file():
                archive.write(file, arcname=f"{output.name}/{file.name}")
    count = sum(r["status"] == "saved" for r in manifest["results"])
    print(f"Saved {count}/{len(posts)} available viewer images.")
    print(f"ZIP: {archive_path}")
    print("For true originals, request the uploader's files or authorized Page export.")
    return 0 if count else 2


if __name__ == "__main__":
    sys.exit(main())
