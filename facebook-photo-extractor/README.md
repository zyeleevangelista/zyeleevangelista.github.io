# Facebook Page Photo Collector

A stand-alone tool at `/facebook-photo-extractor/` in Kyle's GitHub Pages portfolio. No changes to the portfolio homepage are required.

**Important limitation:** Pasting any arbitrary Facebook URL cannot retrieve all its images without the applicable Meta permissions. This project does not bypass Facebook login, privacy settings, rate limits, or API review.

## Higher-resolution workflow (optional; no Meta API)

**Why:** When Chrome/Brave saves a Facebook Photos grid as "Webpage, Complete", the sibling `_files` directory usually stores **grid previews**. Original camera files are not embedded in the saved HTML. ZIP compression or resizing cannot restore missing image detail.

For the highest-quality rendition Facebook makes available to your account, use the separate **Photo Viewer Quality** workflow. It opens each Page photo **post** in its full Facebook viewer using a local Chromium browser and saves the largest matching viewer image it finds. This requires the [Playwright Python library](https://playwright.dev/python/docs/intro), not a Meta API token.

> **No guarantee of original uploads:** Facebook may resize or recompress photos and may withhold larger renditions. The script never invents image pixels, never bypasses Facebook permissions, and skips images it cannot match to the correct post. If you need actual original camera files, ask the Page owner to supply originals or an authorized high-quality Page export.

### Install once on Windows

Install Python 3 if needed. Open a Windows Terminal in this tool's folder and run:

```powershell
py -3 -m pip install playwright
py -3 -m playwright install chromium
```

Download **viewer_quality.py** and **RUN_VIEWER_QUALITY_WINDOWS.bat** into the same directory. Drag your saved Facebook Photos `.html` file onto **RUN_VIEWER_QUALITY_WINDOWS.bat**. Choose how many photo posts to process (default 20; the captured BK gallery has 84 posts). A separate Chromium browser opens, so sign in to Facebook yourself if prompted, then press Enter in the terminal after the first photo becomes visible.

The script tries to match images strictly using each post's photo ID and saved thumbnail filename prefix, and refuses to download unrelated profile photos. It emits a **Facebook_Photo_Viewer_Quality/** directory and ZIP with:

- photos saved from the larger Facebook viewer when matched;
- `manifest.json` listing dimensions and reasons for skipped downloads;
- `PHOTO_POST_LINKS.html` containing Facebook photo-post links for manual downloads if automatic capture fails.

Your Facebook session is held only in a dedicated local Chromium profile folder, `%USERPROFILE%\.facebook-photo-viewer-capture`. You can delete that folder after your work is done to clear the saved login session. Never upload the profile, browser cookies, or saved Page HTML to a public repository.

To generate **only the photo-post links** without Playwright or automation:

```powershell
py -3 viewer_quality.py "C:\path\to\saved-gallery.html" --manual-only --limit 100
```

Open the generated `PHOTO_POST_LINKS.html` and use Facebook's own available Download control in each photo viewer.

### Quality verification

Open an exported photo and check its image dimensions (Windows Properties → Details). Compare it with the saved grid thumbnail. A larger pixel resolution may improve the quality available for your website, but it still does not prove the photo is an uncompressed original. Obtain the owner's permission before republishing clinic/customer/patient photos.

---

## Gallery-only filtering and two supported source formats

Both import methods explicitly identify Page photo-grid posts, rather than all images in the Facebook document. Friend suggestions, avatars and unrelated sidebar images are excluded.

**1. Browser saved-page HTML ("Webpage, Complete").** This format contains photo links and relative image paths. For the supplied `(1) Blanka Kallyntika Aesthetics Zamboanga _ Facebook.html`, the tool identifies **84 Page gallery images**, all associated with the same Page photo set. The photos themselves are stored in the sibling `(1) Blanka Kallyntika Aesthetics Zamboanga _ Facebook_files` folder created by Chrome/Brave, **not embedded in the HTML**.

For Windows, keep the HTML and its `_files` folder together in Downloads, update `offline_extract.py` to the latest copy and drag the HTML onto `RUN_ON_WINDOWS.bat`. The downloader copies the matching existing image files and packages them in one ZIP without API credentials, fetching nothing online. The exported images may be webpage-resolution thumbnails, not original uploads.

For the website, open the **Saved HTML** tab, select the HTML file, then select the matching `_files` folder with the new **Saved webpage image folder** picker and click **Scan local file**. This permits entirely local ZIP exports without Vercel or a Meta token. Chrome/Brave may ask for permission to open the folder.

**2. Older "View Source" saved HTML / TXT.** Earlier file `New Text Document.txt` contains serialized JSON Page photo-grid records rather than browser-saved images. The strict parser identified **8 Page gallery entries** there. These entries reference Facebook CDN image links and may expire; the API-free local folder approach does not apply unless you also have their actual image files.

If no local images are found in saved-page HTML, confirm that the matching `_files` directory is present **beside** the HTML, not moved or renamed. Uploading the HTML alone does not transfer its companion images. Do not commit HTML or session-containing data to your public GitHub repository.

---

## No Meta API required — recommended for saved Facebook HTML

**Works directly from the Facebook page source you already saved.** No developer app, access token, Vercel backend, or paid service. You need Python 3 on your PC.

### Windows (easiest)

1. Download **offline_extract.py** and **RUN_ON_WINDOWS.bat** from this folder into the same Windows folder.
2. While viewing the Facebook photo gallery in your own browser, scroll through photos you need to load and save its HTML/page source as a .html or .txt file. The previously saved `New Text Document.txt` is a valid example.
3. For Chrome/Brave saved-page HTML, keep the matching `_files` directory next to the HTML. Drag the HTML/TXT file onto **RUN_ON_WINDOWS.bat**. Alternatively double-click the BAT and paste the file's full path.
4. The script creates a **Facebook_Photos_Extracted** folder *beside your HTML input file* and a matching **Facebook_Photos_Extracted.zip** containing any accessible downloaded photos plus a manifest of failures.

### Terminal / macOS / Linux

```bash
python3 offline_extract.py "/path/to/saved-facebook-page.html"
```

To check the number of unique referenced CDN photos **without downloading**, run:

```bash
python3 offline_extract.py "/path/to/saved-facebook-page.html" --list-only
```

The offline downloader uses only Python's standard library and limits parallel downloads to avoid overwhelming Facebook. It deliberately does not download unrelated profile photos. You may need to save fresh HTML if Facebook's time-limited CDN links have expired.

**Important distinction:** Pasting a Facebook URL into a GitHub Pages website alone does not give that site permission to read Facebook's page source, because of browser cross-origin restrictions. The offline script instead reads HTML that you saved locally in your browser and downloads accessible images from those links.

The HTML can contain session identifiers. Keep it on your PC and do not upload it to GitHub, your public site, or a public issue tracker. Get permission before republishing business, customer, or medical images.

---

## Features

- **Facebook Page URL mode:** lists uploaded Page photos using the official Meta Graph API through a server-side function. Supports pagination.
- **Saved HTML mode:** scans a locally uploaded Facebook photo-gallery .html or .txt file for Facebook CDN images. The HTML **never leaves the browser**. It only includes photos already present in the saved document, not necessarily the entire Page gallery.
- Preview up to 90 photo thumbnails.
- ZIP export, 75 photos per ZIP. On large galleries, click **Download next ZIP** to collect subsequent parts.
- A `manifest.json` inside every ZIP lists exported and failed images.
- No tracking, no database, no browser storage of keys.

## Deployment: static front-end on GitHub Pages

Merge the pull request into `main`. The UI will be available at:

https://zyeleevangelista.github.io/facebook-photo-extractor/

The front-end works as a local gallery scanner without the backend. However, browser CORS restrictions generally block direct downloads of Facebook CDN image files. Configure a backend to enable reliable ZIP download of accessible images.

## Backend: deploy repository to Vercel

Vercel automatically detects Node functions in the root `api/` folder. Create a Vercel project connected to this GitHub repository, with root directory at the repository root.

Set the following **server-side environment variables** on the Vercel project:

| Variable | Required | Purpose |
| --- | --- | --- |
| `EXTRACTOR_ACCESS_KEY` | Yes | Long random passphrase protecting the backend from unauthorized use. |
| `EXTRACTOR_ALLOWED_ORIGIN` | Recommended | `https://zyeleevangelista.github.io` (or comma-separated authorized origins). |
| `META_PAGE_ACCESS_TOKEN` | For URL mode | Token for a Page the connected Meta app is authorized to read. |

Do not put the Meta token, the private access key, or the saved Facebook HTML into GitHub source code, Vercel build output, or a URL query string.

Copy the Vercel deployment's HTTPS URL into **Vercel API URL** on the tool page. Enter your private `EXTRACTOR_ACCESS_KEY` in its password field (no permanent storage).

The imported HTML media download endpoint requires only `EXTRACTOR_ACCESS_KEY`; it does not require a Meta Page token. It sends **only individual Facebook CDN image URLs** to the backend, not the uploaded HTML or session cookies.

## Meta Graph API setup (Page URL mode)

1. Create or use an appropriately configured Meta developer app.
2. Obtain a Page access token for a Page you manage, with the applicable `pages_read_engagement` and `pages_show_list` permissions.
3. If accessing unrelated Pages, Meta may require approval for **Page Public Content Access**. Possession of a Page URL does not grant access.
4. Add the Page access token to the Vercel environment as `META_PAGE_ACCESS_TOKEN`, and redeploy if required.
5. Paste a valid Page URL, enter your backend URL and access key, then click **Find Page photos**.

The tool requests the documented `/{page-id}/photos?type=uploaded` edge using Graph API `v26.0`. The returned data depends on Meta access controls and does not promise all photos, including albums that are private, posts by others, or photos Meta does not expose.

Official documentation: https://developers.facebook.com/docs/graph-api/reference/page/photos/

## Import a saved Facebook gallery file (without Meta developer access)

1. In your own browser, open a Facebook Page photo gallery you are entitled to access.
2. Scroll to load the photos you need and save the page HTML locally.
3. Use **Saved HTML** on the collector page and select the .html/.txt file.
4. Review the discovered images. Fresh Facebook CDN links may expire quickly.
5. Configure the Vercel backend and extractor key, then click **Download ZIP**. Repeat **Download next ZIP** until all loaded photos are processed.

Saved HTML may contain cookies, session data, internal tokens, or identifiers. Keep it local; never check it into source control, post it in an issue, or share it as a public link.

## Limitations and safeguards

- Extracts images *referenced in the uploaded HTML*, not every item in an entire Facebook Page history.
- External image URLs can expire or be inaccessible. The ZIP manifest reports failures.
- Import mode restricts URLs to HTTPS `scontent.*.fbcdn.net` image files. The backend never fetches arbitrary URLs, Facebook account pages, or private sessions.
- No credential bypass or automatic session login is implemented.
- ZIP parts are produced in batches to avoid large single-browser memory allocations. Each photo is capped at 25 MB; ZIP batch bytes are capped at 180 MB.
- Only download and publish images with the copyright holder's permission, including special consent considerations for patient or treatment photos.

## Project files

`facebook-photo-extractor/index.html` — UI

`facebook-photo-extractor/app.js` — local parser, preview, browser ZIP generator

`api/facebook-photos.js` — authorized Page API listing

`api/facebook-image.js` — fetch permitted Page image IDs

`api/imported-image.js` — restricted Meta CDN image forwarding for imported local HTML

`lib/facebook-photo-utils.js` — validation, auth, CORS, API helper

`package.json` — configures the Node ESM runtime for Vercel functions
