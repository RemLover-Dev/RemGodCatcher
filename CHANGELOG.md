# Changelog

All notable changes to Rem God Catcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
- **Input Focus States** -- Added focus ring animations on input fields.
- **Checkbox Styling** -- Checkboxes now use the cyan accent color.

### Fixed

- **Font Path Mismatch** -- CSS referenced wrong font filename. Both CSS and Python paths corrected.
- **Input Border Color Bug** -- CSS had wrong RGB value. Fixed.
- **Console Log XSS** -- Replaced `innerHTML +=` with `document.createElement()` to prevent injection.
- **Hardcoded API Keys** -- Removed from source code. Moved to `.env` file.
- **Waifu.im NSFW Parameter** -- Lowercase fix.

### Changed

- **Font**: Replaced Playfair with **Inter** (Google Fonts). Console uses **Source Code Pro**.
- **CSS**: Complete rewrite with glass-morphism improvements.
- **JavaScript**: Full rewrite -- `eel.xxx()` replaced with `fetch()` + `socket.emit()`.
- **Python**: Removed `eel`, `customtkinter`. Added `flask`, `flask-socketio`.
- **README**: Rewritten with badges, project structure, and setup instructions.

### Removed

- **CustomTkinter Startup Window** -- All settings now in Web UI.
- **`eel` dependency** -- Replaced by Flask + Socket.IO.
- **`customtkinter` dependency** -- No longer required.

---

## [1.0.0] - 2024-12-01

### Added

- Initial release with Eel-based Web UI.
- Support for Rule34, Safebooru, Zerochan, Waifu.im, and Nekos.best.
- CustomTkinter startup configuration window.
- Glass-morphism dark theme with tabbed navigation.
- Tag auto-suggestion for all platforms.
- AND/OR tag query support with exclusions.
- Anti-ban engine with tactical delays and retry loops.
- Download history tracking via JSON files.
