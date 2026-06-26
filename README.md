<div align="center">

# Rem God Catcher

**A modern, cross-platform image downloader with a glass-morphism web UI.**

Supports Rule34, Safebooru, Zerochan, Waifu.im, and Nekos.best with real-time logging, advanced tag filtering, and anti-ban protections.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)

[English](README.md) | [فارسی](README_fa.md)

</div>

---

## Features

- **Multi-Platform** -- Built-in modules for 5 imageboard APIs
- **Modern Web UI** -- Glass-morphism dark theme, opens in your default browser
- **Real-Time Logs** -- Live console output via WebSocket (Socket.IO)
- **Advanced Search** -- AND/OR tag queries, exclusions (`-video`, `-gif`), custom sorting
- **Anti-Ban Engine** -- Tactical delays, retry loops, rate-limit handling
- **Proxy Support** -- Full proxy configuration from the UI (v2rayN, Clash, etc.)
- **API Key Management** -- Manage Rule34 credentials directly from the Web UI
- **Tag Auto-Suggest** -- Live autocomplete for all platforms
- **Persistent Settings** -- Proxy, API keys, and download settings saved in `.env`

---

## Screenshots

> The UI features a glass-morphism dark panel with tabbed navigation for each platform, a real-time console log, and a settings panel for API keys and proxy configuration.

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/Rem-God-Catcher.git
cd Rem-God-Catcher
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
├── tags.json               # Waifu.im tag database (name → slug mapping)
├── safe_tag_names.json     # Safebooru offline tag database
├── .env                    # API keys & proxy config (git-ignored)
├── .gitignore
├── LICENSE
├── README.md
├── README_fa.md            # Persian documentation
├── CHANGELOG.md
└── web/
    ├── index.html           # Main HTML (tabs, forms, settings)
    ├── script.js            # Frontend logic (Socket.IO + fetch API)
    ├── style.css            # Glass-morphism dark theme (Inter font)
    ├── Fonts/               # Offline fonts (Playfair, MonoLisa)
    └── wallpaper/           # Background images per tab
        ├── Rem_main.png
        ├── Rem_neko.jpg
        ├── Rem_zero.jpg
        ├── Rem_waifu.png
        ├── Rem_safe.jpg
        └── Rem_rule34.jpg
```

---

## Supported Platforms

| Platform | Tags | NSFW | Notes |
|----------|------|------|-------|
| **Rule34** | Full search with AND/OR, exclusions, sorting | Yes | Requires API key for best results |
| **Safebooru** | Standard tag search | No | May require proxy (Cloudflare) |
| **Zerochan** | Tag search with live suggestions | No | Built-in retry & rate limiting |
| **Waifu.im** | Name-to-slug conversion, NSFW toggle | Yes | Uses local `tags.json` for suggestions |
| **Nekos.best** | Category-based (PNG / GIF) | No | Multiple format support |

---

## Customization

### Wallpapers

Replace images in `web/wallpaper/` keeping the exact filenames:

| File | Tab |
|------|-----|
| `Rem_main.png` | Main / System Setup |
| `Rem_neko.jpg` | Nekos.best |
| `Rem_zero.jpg` | Zerochan |
| `Rem_waifu.png` | Waifu.im |
| `Rem_safe.jpg` | Safebooru |
| `Rem_rule34.jpg` | Rule34 |

### Fonts

The UI uses **Inter** (Google Fonts) for the interface and **Source Code Pro** for the console log. Fonts are loaded from CDN with local fallbacks in `web/Fonts/`.

---

## Getting Rule34 API Key

1. Register at [rule34.xxx](https://rule34.xxx)
2. Go to **My Account** -> **Settings**
3. Find the **API Key** section -> **Generate API Key**
4. Copy your **User ID** from the profile URL
5. Enter both in the **Options** tab of the Web UI

> Never share your API keys publicly.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | 3.x | Web server |
| `flask-socketio` | 5.x | WebSocket real-time communication |
| `requests` | 2.x | HTTP client |
| `urllib3` | 2.x | Retry strategies |
| `python-dotenv` | 1.x | `.env` file loading |
| `rule34Py` | latest | Rule34 API wrapper |

---

## Disclaimer

This software is provided for **educational and archiving purposes only**. Some supported APIs index NSFW content -- users must be of legal age in their jurisdiction. Please respect API rate limits and do not aggressively spam requests.

---

## License

[MIT License](LICENSE)
