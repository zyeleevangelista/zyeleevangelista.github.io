#!/usr/bin/env python3
"""Export available Facebook CDN photos from a locally saved Facebook Page HTML file.

No Meta API, login automation, third-party packages or backend required.
Only media URLs already present in the user's saved HTML can be downloaded.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import html
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import (
    HTTPRedirectHandler, Request, build_opener,
)
from zipfile import ZipFile, ZIP_STORED

URL_PATTERN = re.compile(r"https?://[^\s<>\"'\\\x00-\x1f]+", re.I)
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_FILE_BYTES = 40 * 1024 * 1024


def is_facebook_image(url: str) -> bool:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        return (
            parts.scheme == "https"
            and host.startswith("scontent.")
            and host.endswith(".fbcdn.net")
            and (not parts.port or parts.port == 443)
            and not parts.username
            and not parts.password
            and Path(parts.path).suffix.lower() in EXTENSIONS
        )
    except (ValueError, TypeError):
        return False


def quality_score(url: str) -> float:
    """Prefer higher-res variants of the same file path where discernible."""
    query = parse_qs(urlsplit(url).query)
    stp = query.get("stp", [""])[0]
    cstp = query.get("cstp", [""])[0]
    ctp = query.get("ctp", [""])[0]
    score = 100
    for value in (stp, cstp, ctp):
        small = re.search(r"(?:s|p|mx)(\d{2,5})x?(\d{0,5})", value, re.I)
        if small:
            w = int(small.group(1))
            h = int(small.group(2)) if small.group(2) else w
            score += min(w, h) / 10
            if w <= 320 or h <= 320:
                score -= 75
    if re.search(r"(?:^|_)c\d{1,5}\.\d+\.\d+\.\d+[a-z]*", stp):
        score -= 25  # cropped version
    if "s40x40" in stp or "s80x80" in stp:
        score -= 100
    return score


def image_urls_from_saved_html(source: str) -> list[str]:
    # Decode HTML ampersands and common JSON slash/unicode escapes.
    # Do not deserialize or transmit Facebook app/session data.
    source = html.unescape(source)
    source = source.replace("\\/", "/")
    for old, new in (
        ("\\u0026", "&"), ("\\u003d", "="), ("\\u0025", "%"),
        ("\\u003f", "?"), ("\\u002f", "/"), ("\\u002F", "/"),
    ):
        source = source.replace(old, new)
    chosen: dict[str, str] = {}
    for raw in URL_PATTERN.findall(source):
        url = raw.rstrip(");,]}")
        if not is_facebook_image(url):
            continue
        parts = urlsplit(url)
        key = parts.path  # same photo may have several query/host variants
        if key not in chosen or quality_score(url) > quality_score(chosen[key]):
            chosen[key] = url
    return list(chosen.values())


class SafeRedirects(HTTPRedirectHandler):
    """Never follow an extracted photo URL to an unrelated host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_facebook_image(newurl):
            raise URLError("Redirect outside permitted Facebook image hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(SafeRedirects)
CONTENT_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "image/gif": ".gif",
}


def download_one(index: int, url: str, directory: Path) -> dict:
    name_prefix = f"photo_{index:04d}"
    entry = {"number": index, "name": None, "status": "failed"}
    for attempt in range(2):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
                    "Referer": "https://www.facebook.com/",
                    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
                },
            )
            with OPENER.open(request, timeout=18) as response:
                mime = response.headers.get_content_type().lower()
                if mime not in CONTENT_TYPES:
                    raise ValueError(f"Not an image (type: {mime})")
                if int(response.headers.get("Content-Length", "0") or 0) > MAX_IMAGE_BYTES:
                    raise ValueError("File exceeds 25 MB")
                chunks = []
                total = 0
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_IMAGE_BYTES:
                        raise ValueError("File exceeds 25 MB")
                    chunks.append(chunk)
            if total < 1024:
                raise ValueError("Tiny/invalid image (under 1 KB)")
            filename = name_prefix + CONTENT_TYPES[mime]
            (directory / filename).write_bytes(b"".join(chunks))
            entry.update(name=filename, status="ok", bytes=total)
            return entry
        except (OSError, HTTPError, URLError, ValueError) as error:
            entry["reason"] = str(error)[:160]
            if attempt == 0:
                time.sleep(0.5)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download accessible photos found in saved Facebook HTML; no API required."
    )
    parser.add_argument("source", type=Path, help="Saved .html or .txt from Facebook's photos page")
    parser.add_argument("--output", type=Path, help="Output folder (default: beside input file)")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum media items (default 1000)")
    parser.add_argument("--workers", type=int, default=3, help="Parallel downloads 1–5 (default 3)")
    parser.add_argument("--list-only", action="store_true", help="List count without downloading")
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"Saved HTML not found: {args.source}")
    if args.source.stat().st_size > MAX_FILE_BYTES:
        parser.error("HTML file exceeds the 40 MB limit")
    if not 1 <= args.workers <= 5 or not 1 <= args.limit <= 5000:
        parser.error("--workers must be 1–5 and --limit must be 1–5000")

    document = args.source.read_text(encoding="utf-8", errors="replace")
    urls = image_urls_from_saved_html(document)[:args.limit]
    print(f"Discovered {len(urls)} distinct Facebook CDN image paths.")
    if not urls:
        print("No image references found. Try saving the photo gallery after it finishes loading.")
        return 1
    if args.list_only:
        print("No images downloaded (--list-only).")
        return 0

    base = args.output or args.source.parent / "Facebook_Photos_Extracted"
    folder = base
    counter = 2
    while folder.exists() or folder.with_suffix(".zip").exists():
        folder = Path(str(base) + f"_{counter}")
        counter += 1
    folder.mkdir(parents=True)
    records: list[dict] = []

    print(f"Downloading into {folder} ...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_one, n, link, folder): n
            for n, link in enumerate(urls, start=1)
        }
        for done, future in enumerate(as_completed(futures), start=1):
            record = future.result()
            records.append(record)
            if done % 10 == 0 or done == len(urls):
                ok = sum(x["status"] == "ok" for x in records)
                print(f"  {done}/{len(urls)} attempted · {ok} downloaded", flush=True)

    records.sort(key=lambda item: item["number"])
    successful = sum(item["status"] == "ok" for item in records)
    summary = {
        "source_file": args.source.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "found_urls": len(urls),
        "downloaded": successful,
        "failed": len(urls) - successful,
        "records": records,
        "notice": "Only HTML-embedded, accessible CDN images. "
                  "Use clinic/patient photos only with permission.",
    }
    (folder / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (folder / "README.txt").write_text(
        "Facebook photos downloaded from a locally saved HTML file.\n"
        "Some files might be thumbnails, staff avatars, or gallery previews.\n"
        "Failed/expired files are listed in manifest.json.\n"
        "Please obtain the owner’s approval before reusing photos on a website.\n",
        encoding="utf-8",
    )
    zip_path = folder.with_suffix(".zip")
    with ZipFile(zip_path, "w", compression=ZIP_STORED, allowZip64=True) as archive:
        for image in sorted(folder.iterdir()):
            if image.is_file():
                archive.write(image, arcname=f"{folder.name}/{image.name}")
    print(f"\nFinished: {successful} photos downloaded, {len(urls)-successful} unavailable.")
    print(f"Folder: {folder}")
    print(f"ZIP:    {zip_path}")
    return 0 if successful else 2


if __name__ == "__main__":
    sys.exit(main())
