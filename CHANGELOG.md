# Changelog

All notable changes to Rem God Catcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [3.2.0] - 2026-07-02

### Added
- **Yande.re Platform** -- New worker for yande.re (Moebooru API) with tag autocomplete, rating-based folder sorting (Safe/Moderate/NSFW), and local tag database (135k+ tags).
- **Download Retries Configuration** -- Retry count is now configurable in Options tab, saved to `.env` as `DOWNLOAD_RETRIES`.
- **Anti-Spam Pause** -- After 10 consecutive pages with no new downloads, a 5-second anti-spam pause triggers instead of flying through silently.
- **Rating Filter** -- Yande.re tab has a rating dropdown (All/Safe/Moderate/NSFW) that filters server-side and sorts into per-rating subfolders.
- **History Jump Button** -- Each search history entry now has a ➡️ button to navigate directly to the site's tab with the tag filled in.

### Changed
- **All Workers** -- Failed downloads are now retried up to N times (configurable) without stopping the queue.
- **Anti-Ban Pause** -- Pages with 0 new downloads skip the anti-ban pause, flying through already-downloaded content instantly.
- **Empty Page Limit Removed** -- Workers no longer stop after 3 empty pages; they continue until the API returns nothing.
- **Yande.re Anti-Ban** -- Uses the exact configured pause value (no random jitter).

---

## [3.1.0] - 2026-07-02

### Added
- **Nekos.life Category Type Indicators**: Categories are now visually grouped (GIF Only, Static Only, Mixed, Other) in the UI with a live type badge showing [GIF], [STATIC], or [MIXED] next to the dropdown.
- **Rule34 GIFs Only Filter**: New "GIFs Only" option in the Rule34 format dropdown to exclusively search for animated GIFs.
- **Favorite Item Remove Button**: Each favorite tag now has an "✕" button to quickly remove it without navigating to the site.
- **Jump-To-Site for All Platforms**: `jumpToSite()` now supports Zerochan, Waifu.im, Neko, and Nekos.life in addition to the original three booru sites.
- **Live Net Config Passing**: `startWorker()` now sends fresh values from the input fields for `api_timeout`, `retry_wait`, and `anti_ban_pause` instead of relying solely on the cached `globalNetConfig` object.

### Changed
- **Nekos.life Category Reorganization**: Dropdown options are now organized into `<optgroup>` sections for clearer browsing.
- **Tab Button Visibility**: Tab text color brightened from `rgba(255,255,255,0.7)` to `rgba(255,255,255,0.9)` and hover state improved for better readability.
- **Favorite Tags UI**: The entire favorite card is no longer a single click target — only the tag/site text area triggers the jump, preventing accidental navigation when trying to remove a favorite.

### Removed
- **GIF Exclude Checkboxes**: Removed the separate "Exclude GIF" checkboxes from Safebooru and Gelbooru tabs. GIF filtering is now handled exclusively through the Format dropdown selector.

### Fixed
- **Image History Refresh**: `renderImageHistory()` is now called after toggling favorites, ensuring the Image Archive UI stays in sync.

---

## [3.0.0] - Rem 3: The Discovery & Archive Update - 2026-07-02

### Added
- **Image Archive System**: A completely new UI in the frontend that creates individual cards for every downloaded image, displaying its filename, source site, clickable tags, and extracted artist names.
- **Favorites System**: Users can now heart tags in the History or Image Archive. These favorite tags appear in the Main Tab. Clicking a favorite tag instantly jumps to the corresponding site's tab and auto-fills the search input.
- **Search History Tracking**: Added a dedicated "History" tab with its own customizable wallpaper. It automatically records the latest searched tags across all sites (Rule34, Gelbooru, Safebooru, Zerochan, etc.) and limits the database to 500 entries to maintain high performance.
- **Background Tag Extraction**: Workers now intelligently parse massive tag lists and artist names directly from the APIs (`tag_string`, `tag_string_artist`, etc.) and send them to the backend without freezing the app.
- **Video & Format Filtering**: Implemented dedicated filters to exclusively search for Video formats (`.mp4`, `.webm`) or restrict searches to Images only across supported platforms.
- **Image History API**: New REST endpoints (`/api/image_history`, `/api/image_history/clear`, `/api/image_history/remove`) for managing the per-image tag archive.

### Changed
- **Cleaner Console Logs**: Removed verbose tag strings from the real-time console log. Logs now remain clean and readable, while tags are silently routed to the new Image Archive UI.
- **Safebooru Tag Parsing**: Fixed an issue where Safebooru hid its primary tags inside a `tag_string` variable instead of the standard `tags` array, ensuring accurate tag extraction.
- **Duplicate Tag Handling**: Improved backend logic to accurately differentiate between similar character tags and prevent duplicate entries in the JSON databases.
- **Scroll-Preserving History**: The History tab now preserves scroll position when new tags are added in real-time, preventing jarring jumps.
- **`.gitignore` Refined**: Replaced blanket `*.json` exclusion with specific filenames (`tag_history.json`, `fav_tags.json`, `image_history.json`) so project JSON files like `tags.json` are not ignored.

---

## [2.1.0] - 2026-06-26

### Added
- **Options Tab** -- Renamed "API Keys" to "Options". Added configurable download settings (API Timeout, Retry Wait, Anti-Ban Pause) directly in the Web UI.
- **Waifu.im Tag Database (`tags.json`)** -- Local tag database with name-to-slug conversion. Typing "Genshin Impact" now correctly sends "genshin-impact" to the API.
- **Download Settings in `.env`** -- Added `API_TIMEOUT`, `RETRY_WAIT`, `ANTI_BAN_PAUSE` fields. All settings persist across restarts.
- **Safebooru Empty Page Breaker** -- Worker now stops after 3 consecutive pages with no downloads, preventing infinite loops on slow networks.
- **Rule34 Proxy Injection** -- Proxy settings are now injected into `rule34Py`'s internal session (`client.session.proxies`), so image downloads also go through the proxy.
- **Safebooru Parentheses Support** -- Parentheses in tag names (e.g., `rem_(re:zero)`) are now handled correctly via URL params instead of stripping them.

### Fixed
- **Rule34 API Key Format** -- Fixed `client.api_key` format. The library expects raw key string, not `&api_key=...` prefix.
- **Rule34 Image Download Proxy** -- Changed `requests.get()` to `client.session.get()` for image downloads, so proxy settings are applied.
- **Waifu.im NSFW Parameter** -- Changed `"True"` to `"true"` for `IsNsfw` parameter (API requires lowercase).
- **Waifu.im Empty Results** -- Now shows available tags when a tag doesn't exist, instead of generic "End of database reached".
- **Safebooru Cloudflare Handling** -- Improved error messaging for 403 responses.
- **Console Log Scrolling** -- Fixed flex layout so only the terminal area scrolls, not the entire page.
- **Options Tab Scrolling** -- Options tab content is now scrollable when it overflows.
- **Tab Display Mode** -- Changed from `display: block` to `display: flex` for proper height distribution.

### Changed
- **Console Font** -- Replaced JetBrains Mono with **Source Code Pro** (Google Fonts) for softer, eye-friendly terminal text.
- **Tab Name** -- "API Keys" renamed to **"Options"**.
- **Safebooru Worker** -- Added `page_downloaded` counter and `empty_pages` tracker to prevent infinite loops.
- **All Workers** -- Now read `api_timeout`, `retry_wait`, `anti_ban_pause` from `net_config` for configurable behavior.

### Removed
- **"Resting..." Log Message** -- Removed from Waifu.im worker to reduce log noise.
- **Parentheses Stripping** -- No longer removes `()` from Safebooru tags (they are valid and required).

---

## [2.0.0] - 2026-06-25

### Major Changes
- **Migrated from Eel to Flask + Socket.IO** -- The Web UI no longer requires Chrome/Chromium. It now opens in your default browser via a local Flask server.
- **Added Web-based Proxy Configuration** -- Proxy settings are now configurable directly from the Web UI's Main tab.

### Added
- **Options Tab** -- New tab in the Web UI to manage Rule34 API credentials and download settings.
- **Socket.IO Real-Time Logging** -- Console logs are pushed to the browser via WebSocket for instant feedback.
- **Persistent Proxy Settings** -- Proxy configuration is saved to `.env` and restored on restart.
- **Google Fonts Integration** -- Inter font loaded from Google Fonts CDN.
- **Custom Scrollbar Styling** -- Scrollbar appearance customized for the console log panels.

### Fixed
- **Font Path Mismatch** -- CSS referenced wrong font filename. Both CSS and Python paths corrected.
- **Console Log XSS** -- Replaced `innerHTML +=` with `document.createElement()` to prevent injection.
- **Hardcoded API Keys** -- Removed from source code. Moved to `.env` file.

### Changed
- **Font**: Replaced Playfair with **Inter** (Google Fonts). Console uses **Source Code Pro**.
- **CSS**: Complete rewrite with glass-morphism improvements.
- **JavaScript**: Full rewrite -- `eel.xxx()` replaced with `fetch()` + `socket.emit()`.
- **Python**: Removed `eel`, `customtkinter`. Added `flask`, `flask-socketio`.

### Removed
- **CustomTkinter Startup Window** -- All settings now in Web UI.
- **`eel` dependency** -- Replaced by Flask + Socket.IO.

---

## [1.0.0] - 2026-06-20

### Added
- Initial release with Eel-based Web UI.
- Support for Rule34, Safebooru, Zerochan, Waifu.im, and Nekos.best.
- CustomTkinter startup configuration window.
- Glass-morphism dark theme with tabbed navigation.
- Tag auto-suggestion for all platforms.
- AND/OR tag query support with exclusions.
- Anti-ban engine with tactical delays and retry loops.
- Download history tracking via JSON files.
