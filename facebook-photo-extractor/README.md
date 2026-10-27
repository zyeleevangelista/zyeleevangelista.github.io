# Facebook Page Photo Collector

A stand-alone tool at \`/facebook-photo-extractor/\` in Kyle's GitHub Pages portfolio. No changes to the portfolio homepage are required.

**Important limitation:** Pasting any arbitrary Facebook URL cannot retrieve all its images without the applicable Meta permissions. This project does not bypass Facebook login, privacy settings, rate limits, or API review.

## Features

- **Facebook Page URL mode:** lists uploaded Page photos using the official Meta Graph API through a server-side function. Supports pagination.
- **Saved HTML mode:** scans a locally uploaded Facebook photo-gallery .html or .txt file for Facebook CDN images. The HTML **never leaves the browser**. It only includes photos already present in the saved document, not necessarily the entire Page gallery.
- Preview up to 90 photo thumbnails.
- ZIP export, 75 photos per ZIP. On large galleries, click **Download next ZIP** to collect subsequent parts.
- A \`manifest.json\` inside every ZIP lists exported and failed images.
- No tracking, no database, no browser storage of keys.

## Deployment: static front-end on GitHub Pages

Merge the pull request into \`main\`. The UI will be available at:

https://zyeleevangelista.github.io/facebook-photo-extractor/

The front-end works as a local gallery scanner without the backend. However, browser CORS restrictions generally block direct downloads of Facebook CDN image files. Configure a backend to enable reliable ZIP download of accessible images.

## Backend: deploy repository to Vercel

Vercel automatically detects Node functions in the root \`api/\` folder. Create a Vercel project connected to this GitHub repository, with root directory at the repository root.

Set the following **server-side environment variables** on the Vercel project:

| Variable | Required | Purpose |
| --- | --- | --- |
| \`EXTRACTOR_ACCESS_KEY\` | Yes | Long random passphrase protecting the backend from unauthorized use. |
| \`EXTRACTOR_ALLOWED_ORIGIN\` | Recommended | \`https://zyeleevangelista.github.io\` (or comma-separated authorized origins). |
| \`META_PAGE_ACCESS_TOKEN\` | For URL mode | Token for a Page the connected Meta app is authorized to read. |

Do not put the Meta token, the private access key, or the saved Facebook HTML into GitHub source code, Vercel build output, or a URL query string.

Copy the Vercel deployment's HTTPS URL into **Vercel API URL** on the tool page. Enter your private \`EXTRACTOR_ACCESS_KEY\` in its password field (no permanent storage).

The imported HTML media download endpoint requires only \`EXTRACTOR_ACCESS_KEY\`; it does not require a Meta Page token. It sends **only individual Facebook CDN image URLs** to the backend, not the uploaded HTML or session cookies.

## Meta Graph API setup (Page URL mode)

1. Create or use an appropriately configured Meta developer app.
2. Obtain a Page access token for a Page you manage, with the applicable \`pages_read_engagement\` and \`pages_show_list\` permissions.
3. If accessing unrelated Pages, Meta may require approval for **Page Public Content Access**. Possession of a Page URL does not grant access.
4. Add the Page access token to the Vercel environment as \`META_PAGE_ACCESS_TOKEN\`, and redeploy if required.
5. Paste a valid Page URL, enter your backend URL and access key, then click **Find Page photos**.

The tool requests the documented \`/{page-id}/photos?type=uploaded\` edge using Graph API \`v26.0\`. The returned data depends on Meta access controls and does not promise all photos, including albums that are private, posts by others, or photos Meta does not expose.

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
- Import mode restricts URLs to HTTPS \`scontent.*.fbcdn.net\` image files. The backend never fetches arbitrary URLs, Facebook account pages, or private sessions.
- No credential bypass or automatic session login is implemented.
- ZIP parts are produced in batches to avoid large single-browser memory allocations. Each photo is capped at 25 MB; ZIP batch bytes are capped at 180 MB.
- Only download and publish images with the copyright holder's permission, including special consent considerations for patient or treatment photos.

## Project files

\`facebook-photo-extractor/index.html\` — UI

\`facebook-photo-extractor/app.js\` — local parser, preview, browser ZIP generator

\`api/facebook-photos.js\` — authorized Page API listing

\`api/facebook-image.js\` — fetch permitted Page image IDs

\`api/imported-image.js\` — restricted Meta CDN image forwarding for imported local HTML

\`lib/facebook-photo-utils.js\` — validation, auth, CORS, API helper
