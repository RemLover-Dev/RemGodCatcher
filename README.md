<div align="center">

# Rem God Catcher

**A modern, cross-platform image & video downloader with a glass-morphism web UI.**

Supports Rule34, Safebooru, Gelbooru, Zerochan, Waifu.im, Nekos.best, Nekos.life, and Yande.re with real-time logging, a built-in discovery engine, advanced tag filtering, and anti-ban protections.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)
[![Version](https://img.shields.io/badge/Version-3.2.0-ff9ff3.svg)](CHANGELOG.md)

[English](README.md) | [فارسی](README_fa.md)

</div>

---

## Features

- **Multi-Platform** -- Built-in modules for 8 imageboard APIs
- **Modern Web UI** -- Glass-morphism dark theme, opens in your default browser
- **Discovery Engine & Archives** -- Live extraction of tags and artists from downloaded media, displayed in a dedicated Image Archive tab.
- **Favorites & Search History** -- Add tags to your favorites list for one-click search automation, and maintain a log of your search history.
- **Video & GIF Support** -- Exclusively target `.mp4`, `.webm`, or GIF files via format filtering.
- **GIFs Only Filter** -- Rule34 supports a dedicated GIFs Only mode alongside Images/Videos/All.
- **Real-Time Logs** -- Live console output via WebSocket (Socket.IO)
- **Advanced Search** -- AND/OR tag queries, exclusions (`-video`, `-image`), custom sorting, category-based browsing
- **Anti-Ban Engine** -- Tactical delays, retry loops, rate-limit handling
- **Proxy Support** -- Full proxy configuration from the UI (v2rayN, Clash, etc.)
- **API Key Management** -- Manage Rule34 credentials directly from the Web UI
- **Tag Auto-Suggest** -- Live autocomplete for all platforms
- **Persistent Settings** -- Proxy, API keys, and download settings saved in `.env`

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/callmedark44/RemGodCatcher.git
cd RemGodCatcher
```

### 2. Install Dependencies

```bash
pip install flask flask-socketio requests urllib3 python-dotenv rule34Py
```

### 3. Configure (Optional)

Edit `.env` or use the **Options** tab in the Web UI:

```env
RULE34_API_KEY=your_api_key_here
RULE34_USER_ID=your_user_id_here
USE_PROXY=false
PROXY_URL=http://127.0.0.1:10808
VERIFY_TLS=false
API_TIMEOUT=10
RETRY_WAIT=5
ANTI_BAN_PAUSE=3.0
```

### 4. Run

```bash
python Rem_catcher.py
```

The Web UI opens automatically at `http://127.0.0.1:5000`.

---

## Project Structure

```
Rem God Catcher/
├── Rem_catcher.py          # Python backend (Flask + Socket.IO)
├── shared.py               # Core utilities, tag handler, and logging bridge
├── workers/                # API-specific download modules
├── tags.json               # Waifu.im tag database (name -> slug mapping)
├── safe_tag_names.json     # Safebooru offline tag database
├── yande_tag_names.json    # Yande.re offline tag database
├── tag_history.json        # Search history database (git-ignored)
├── fav_tags.json           # User favorites database (git-ignored)
├── image_history.json      # Per-image tag archive (git-ignored)
├── .env                    # API keys & proxy config (git-ignored)
├── .gitignore
├── LICENSE
├── README.md
├── README_fa.md            # Persian documentation
├── CHANGELOG.md
└── web/
    ├── index.html           # Main HTML (tabs, forms, archives, settings)
    ├── script.js            # Frontend logic (Socket.IO + fetch API)
    ├── style.css            # Glass-morphism dark theme (Inter font)
    ├── Fonts/               # Offline fonts (Playfair, MonoLisa)
    └── wallpaper/           # Background images per tab
```

---

## Supported Platforms

| Platform | Tags | NSFW | Notes |
|----------|------|------|-------|
| **Rule34** | Full search with AND/OR, exclusions, sorting, video format support | Yes | Requires API key for best results |
| **Safebooru** | Standard tag search, video format support, artist extraction | No | May require proxy (Cloudflare) |
| **Gelbooru** | Full search, format exclusions, video format support | Yes | Requires API key for best results |
| **Zerochan** | Tag search with live suggestions | No | Built-in retry & rate limiting |
| **Waifu.im** | Name-to-slug conversion, NSFW toggle | Yes | Uses local `tags.json` for suggestions |
| **Nekos.best** | Category-based (PNG / GIF) | No | Multiple format support |
| **Nekos.life** | Category-based with type indicators (GIF/Static/Mixed) | Yes | Animated neko, hug, pat, cuddle, and more |
| **Yande.re** | Full tag search, rating filter, artist extraction, local tag DB | Yes | Moebooru API, images only, sorts into Safe/Moderate/NSFW folders |

---

## Getting Rule34 API Key

1. Register at [rule34.xxx](https://rule34.xxx)
2. Go to **My Account** -> **Settings**
3. Find the **API Key** section -> **Generate API Key**
4. Copy your **User ID** from the profile URL
5. Enter both in the **Options** tab of the Web UI

> Never share your API keys publicly.

---

## Disclaimer

This software is provided for **educational and archiving purposes only**. Some supported APIs index NSFW content -- users must be of legal age in their jurisdiction. Please respect API rate limits and do not aggressively spam requests.

---

## License

[MIT License](LICENSE)
