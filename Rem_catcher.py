import os
import sys
import time
import threading
import requests
import urllib3
import urllib.parse
import random
import re
import json
import webbrowser
import xml.etree.ElementTree as ET

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load .env file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==========================================
# === GLOBAL VARIABLES ===
# ==========================================
STOP_EVENTS = {}
SAFE_TAGS_DB = []
WAIFU_TAGS_DB = []
WAIFU_TAG_MAP = {}
MASTER_FOLDER = os.path.join(os.getcwd(), "Rem God")
HISTORY_LOCK = threading.Lock()

STARTUP_CONFIG = {
    "use_proxy": os.getenv("USE_PROXY", "false").lower() == "true",
    "proxy_url": os.getenv("PROXY_URL", "http://127.0.0.1:10808"),
    "verify_tls": os.getenv("VERIFY_TLS", "false").lower() == "true",
    "api_timeout": int(os.getenv("API_TIMEOUT", "10")),
    "retry_wait": int(os.getenv("RETRY_WAIT", "5")),
    "anti_ban_pause": float(os.getenv("ANTI_BAN_PAUSE", "3.0"))
}

# ==========================================
# === FLASK + SOCKETIO SETUP ===
# ==========================================
app = Flask(__name__, static_folder="web")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ==========================================
# === JSON HISTORY MANAGEMENT ===
# ==========================================
def load_history(site_root):
    hist_path = os.path.join(site_root, "download_history.json")
    with HISTORY_LOCK:
        if os.path.exists(hist_path):
            try:
                with open(hist_path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

def save_history(site_root, history_set):
    hist_path = os.path.join(site_root, "download_history.json")
    with HISTORY_LOCK:
        try:
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(list(history_set), f, indent=4)
        except Exception as e:
            print(f"Error saving history: {e}")

# ==========================================
# === LOGGING (via Socket.IO) ===
# ==========================================
def log_msg(worker_name, msg):
    try:
        socketio.emit("python_log", {"worker": worker_name, "msg": msg})
    except Exception:
        print(f"[{worker_name.upper()}] {msg}")

def load_waifu_tags():
    global WAIFU_TAGS_DB, WAIFU_TAG_MAP
    tags_path = os.path.join(BASE_DIR, "tags.json")
    if os.path.exists(tags_path):
        try:
            with open(tags_path, "r", encoding="utf-8") as f:
                WAIFU_TAGS_DB = json.load(f)
            WAIFU_TAG_MAP = {t["name"].lower(): t["slug"] for t in WAIFU_TAGS_DB}
            print(f"[SYSTEM] Loaded {len(WAIFU_TAGS_DB)} Waifu.im tags from tags.json.")
        except Exception as e:
            print(f"[SYSTEM] Error loading tags.json: {e}")

def waifu_name_to_slug(name):
    name_lower = name.lower().strip()
    if name_lower in WAIFU_TAG_MAP:
        return WAIFU_TAG_MAP[name_lower]
    return name_lower

# ==========================================
# === SESSION MANAGER ===
# ==========================================
def get_session(site, net_config):
    session = requests.Session()
    if net_config.get("use_proxy"):
        p = net_config.get("proxy_url")
        session.proxies = {"http": p, "https": p}
    else:
        session.proxies = {"http": "", "https": "", "no_proxy": "*"}

    session.verify = net_config.get("verify_tls", False)

    if site == "safe":
        session.headers.update({"User-Agent": "RemGodCatcher/2.0", "Accept": "application/json"})
    elif site == "zero":
        session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/json,*/*"})
        retry_strategy = Retry(total=3, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    elif site in ["waifu", "neko"]:
        session.headers.update({"Accept": "application/json"})
    return session

# ==========================================
# === SAFEBOoru TAG DB ===
# ==========================================
def load_safe_db():
    global SAFE_TAGS_DB
    db_path = os.path.join(BASE_DIR, "safe_tag_names.json")
    if not os.path.exists(db_path):
        db_path = os.path.join(BASE_DIR, "tag_names.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                SAFE_TAGS_DB = json.load(f)
            print(f"[SYSTEM] Loaded {len(SAFE_TAGS_DB)} offline tags for Safebooru.")
        except Exception as e:
            print(f"[SYSTEM] Error parsing JSON: {e}")

# ==========================================
# === FLASK ROUTES (STATIC + API) ===
# ==========================================
@app.route("/")
def index():
    return send_from_directory("web", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("web", path)

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(STARTUP_CONFIG)

@app.route("/api/config", methods=["POST"])
def set_config():
    global STARTUP_CONFIG
    data = request.json
    STARTUP_CONFIG["use_proxy"] = data.get("use_proxy", False)
    STARTUP_CONFIG["proxy_url"] = data.get("proxy_url", "http://127.0.0.1:10808")
    STARTUP_CONFIG["verify_tls"] = data.get("verify_tls", False)
    STARTUP_CONFIG["api_timeout"] = int(data.get("api_timeout", 10))
    STARTUP_CONFIG["retry_wait"] = int(data.get("retry_wait", 5))
    STARTUP_CONFIG["anti_ban_pause"] = float(data.get("anti_ban_pause", 3.0))

    # Save all settings to .env
    env_path = os.path.join(BASE_DIR, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    env_keys = {
        "USE_PROXY": str(STARTUP_CONFIG['use_proxy']).lower(),
        "PROXY_URL": STARTUP_CONFIG['proxy_url'],
        "VERIFY_TLS": str(STARTUP_CONFIG['verify_tls']).lower(),
        "API_TIMEOUT": str(STARTUP_CONFIG['api_timeout']),
        "RETRY_WAIT": str(STARTUP_CONFIG['retry_wait']),
        "ANTI_BAN_PAUSE": str(STARTUP_CONFIG['anti_ban_pause'])
    }

    new_lines = []
    found = {k: False for k in env_keys}
    for line in lines:
        stripped = line.strip()
        matched = False
        for key, val in env_keys.items():
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={val}\n")
                found[key] = True
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for key, val in env_keys.items():
        if not found[key]:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return jsonify({"success": True})

@app.route("/api/folder", methods=["GET"])
def get_folder():
    return jsonify({"folder": MASTER_FOLDER})

@app.route("/api/folder", methods=["POST"])
def set_folder():
    global MASTER_FOLDER
    data = request.json
    folder = data.get("folder", "")
    if folder:
        MASTER_FOLDER = os.path.join(folder, "Rem God")
        return jsonify({"folder": MASTER_FOLDER})
    return jsonify({"error": "No folder provided"}), 400

@app.route("/api/api-settings", methods=["GET"])
def get_api_settings():
    env_path = os.path.join(BASE_DIR, ".env")
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    return jsonify({
        "rule34_api_key": config.get("RULE34_API_KEY", ""),
        "rule34_user_id": config.get("RULE34_USER_ID", "")
    })

@app.route("/api/api-settings", methods=["POST"])
def save_api_settings():
    data = request.json
    api_key = data.get("rule34_api_key", "")
    user_id = data.get("rule34_user_id", "")
    env_path = os.path.join(BASE_DIR, ".env")

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    found_api = False
    found_uid = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("RULE34_API_KEY="):
            new_lines.append(f"RULE34_API_KEY={api_key}\n")
            found_api = True
        elif stripped.startswith("RULE34_USER_ID="):
            new_lines.append(f"RULE34_USER_ID={user_id}\n")
            found_uid = True
        else:
            new_lines.append(line)

    if not found_api:
        new_lines.append(f"RULE34_API_KEY={api_key}\n")
    if not found_uid:
        new_lines.append(f"RULE34_USER_ID={user_id}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    os.environ["RULE34_API_KEY"] = api_key
    os.environ["RULE34_USER_ID"] = user_id

    return jsonify({"success": True, "message": "API settings saved to .env successfully!"})

# ==========================================
# === TAG SUGGESTION ROUTES ===
# ==========================================
@app.route("/api/tags/waifu", methods=["POST"])
def get_waifu_tags():
    if WAIFU_TAGS_DB:
        return jsonify([t["name"] for t in WAIFU_TAGS_DB])
    # Fallback to API
    net_config = request.json
    try:
        session = get_session("waifu", net_config)
        resp = session.get("https://api.waifu.im/tags", timeout=10)
        data = resp.json()
        tags = [t.get("name", t.get("slug")) for t in data.get("items", [])]
        return jsonify(sorted(list(set([t for t in tags if t]))))
    except Exception:
        return jsonify(sorted(['maid', 'waifu', 'marin-kitagawa', 'mori-calliope', 'raiden-shogun', 'oppai', 'selfies', 'uniform', 'kamisato-ayaka', 'ero', 'ass', 'hentai', 'milf', 'oral', 'paizuri', 'ecchi']))

@app.route("/api/tags/neko", methods=["POST"])
def get_neko_tags():
    net_config = request.json
    try:
        session = get_session("neko", net_config)
        resp = session.get("https://nekos.best/api/v2/endpoints", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        images = sorted([cat for cat, d in data.items() if d.get("format") == "png"])
        gifs = sorted([cat for cat, d in data.items() if d.get("format") == "gif"])
        return jsonify({"image": images, "gif": gifs})
    except Exception:
        return jsonify({"image": [], "gif": []})

@app.route("/api/tags/zerochan", methods=["POST"])
def get_zerochan_suggestions():
    data = request.json
    query = data.get("query", "")
    net_config = data.get("net_config", {})
    try:
        session = get_session("zero", net_config)
        session.headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.zerochan.net/"})
        resp = session.get(f"https://www.zerochan.net/suggest?q={urllib.parse.quote_plus(query)}", timeout=5)
        if resp.status_code == 200:
            sugs = resp.json() if "{" in resp.text or "[" in resp.text else [s.strip() for s in resp.text.split('\n') if s.strip()]
            return jsonify(list(dict.fromkeys([s.split('|')[0].strip() for s in sugs])))
    except Exception:
        pass
    return jsonify([])

@app.route("/api/tags/safe", methods=["POST"])
def get_safe_suggestions():
    data = request.json
    query = data.get("query", "").lower()
    if not SAFE_TAGS_DB:
        return jsonify([])
    return jsonify([t for t in SAFE_TAGS_DB if t.startswith(query)][:50])

@app.route("/api/tags/rule34", methods=["POST"])
def get_rule34_suggestions():
    data = request.json
    query = data.get("query", "")
    net_config = data.get("net_config", {})
    if len(query) < 2:
        return jsonify([])
    try:
        session = get_session("rule34", net_config)
        url = f"https://api.rule34.xxx/autocomplete.php?q={urllib.parse.quote(query)}"
        resp = session.get(url, timeout=3)
        if resp.status_code == 200:
            d = resp.json()
            return jsonify([item.get("value") for item in d if isinstance(item, dict) and "value" in item])
    except Exception:
        pass
    try:
        session = get_session("rule34", net_config)
        url = f"https://gelbooru.com/index.php?page=autocomplete2&term={urllib.parse.quote(query)}&type=tag_query&limit=20"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200:
            d = resp.json()
            return jsonify([item.get("value") for item in d if isinstance(item, dict) and "value" in item])
    except Exception:
        pass
    return jsonify([])

# ==========================================
# === WORKER START/STOP (Socket.IO) ===
# ==========================================
@socketio.on("start_worker")
def handle_start_worker(data):
    worker = data.get("worker")
    if worker == "zero":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        net_config = data.get("net_config", {})
        threading.Thread(target=worker_zerochan, args=(tag, limit, net_config), daemon=True).start()
    elif worker == "waifu":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 30))
        nsfw = data.get("nsfw", False)
        net_config = data.get("net_config", {})
        threading.Thread(target=worker_waifu, args=(tag, limit, nsfw, net_config), daemon=True).start()
    elif worker == "neko":
        category = data.get("category", "")
        limit = int(data.get("limit", 20))
        net_config = data.get("net_config", {})
        threading.Thread(target=worker_nekos_best, args=(category, limit, net_config), daemon=True).start()
    elif worker == "safe":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        net_config = data.get("net_config", {})
        threading.Thread(target=worker_safebooru, args=(tag, limit, net_config), daemon=True).start()
    elif worker == "rule34":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        method = data.get("method", "and")
        sort_type = data.get("sort_type", "id")
        sort_order = data.get("sort_order", "desc")
        exclusions = data.get("exclusions", [])
        net_config = data.get("net_config", {})
        threading.Thread(target=worker_rule34, args=(tag, limit, method, sort_type, sort_order, exclusions, net_config), daemon=True).start()

@socketio.on("stop_worker")
def handle_stop_worker(data):
    name = data.get("worker")
    log_msg(name, ">>> STOP SIGNAL RECEIVED! Terminating connections immediately... <<<")
    if name in STOP_EVENTS:
        STOP_EVENTS[name].set()

# ==========================================
# === WORKER FUNCTIONS ===
# ==========================================

# ----------------- RULE34 WORKER -----------------
def worker_rule34(tag, amount, method, sort_type, sort_order, exclusions, net_config):
    name = "rule34"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    log_msg(name, "Initializing worker... [RULE34PY LIBRARY MODE]")

    tag_list = [t.strip() for t in tag.strip().lower().split() if t.strip()]

    if len(tag_list) > 10:
        log_msg(name, "Warning: Max 10 tags allowed! Truncating your list...")
        tag_list = tag_list[:10]

    TAGS = []
    if method == "or":
        if any(t.startswith('-') for t in tag_list):
            log_msg(name, "Error: Cannot use negative (-tag) in OR method.")
            log_msg(name, "Auto-switching to AND method...")
            TAGS.extend(tag_list)
        else:
            TAGS.append(" ~ ".join(tag_list))
    else:
        TAGS.extend(tag_list)

    if sort_order == "desc":
        TAGS.append(f"sort:{sort_type}")
    else:
        TAGS.append(f"sort:{sort_type}:{sort_order}")

    if exclusions:
        TAGS.extend(exclusions)

    log_msg(name, f"Final Payload sent to rule34Py: {TAGS}")

    site_root = os.path.join(MASTER_FOLDER, "Rule34")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    clean_folder_name = " ".join([t for t in tag_list if not t.startswith('-')])
    safe_tag_dir = re.sub(r'[\\/*?:"<>|~]', "", clean_folder_name).strip().replace(' ', '_')
    if not safe_tag_dir:
        safe_tag_dir = "mixed_tags"

    tag_dir = os.path.join(site_root, safe_tag_dir)
    os.makedirs(tag_dir, exist_ok=True)

    try:
        from rule34Py import rule34Py
        client = rule34Py()

        api_key = os.getenv("RULE34_API_KEY", "")
        user_id = int(os.getenv("RULE34_USER_ID", "0"))

        if api_key and user_id:
            client.api_key = api_key
            client.user_id = user_id
            log_msg(name, "API credentials loaded from .env")
        else:
            log_msg(name, "No API credentials found. Running in anonymous mode.")

        # Inject proxy into rule34Py session
        if net_config.get("use_proxy"):
            p = net_config.get("proxy_url")
            client.session.proxies = {"http": p, "https": p}
            client.session.verify = net_config.get("verify_tls", False)
            log_msg(name, f"Proxy enabled: {p}")
        else:
            client.session.proxies = {"http": "", "https": "", "no_proxy": "*"}
            client.session.verify = False

        downloaded = 0
        page = 0

        while not stop_event.is_set() and (amount == 0 or downloaded < amount):
            log_msg(name, f"Scanning via rule34Py... (Page {page})")

            chunk_limit = min(1000, amount - downloaded if amount > 0 else 100)

            results = None
            max_retries = 5

            for attempt in range(max_retries):
                try:
                    results = client.search(TAGS, page_id=page, limit=chunk_limit)
                    break
                except TypeError as e:
                    if "string indices must be integers" in str(e):
                        results = []
                        break
                    else:
                        raise e
                except Exception as e:
                    error_msg = str(e)
                    if "timeout" in error_msg.lower() or "read timed out" in error_msg.lower():
                        log_msg(name, f"Network Timeout (Attempt {attempt+1}/{max_retries}). Retrying in 3s...")
                        time.sleep(3)
                    else:
                        raise e

            if results is None:
                log_msg(name, "Failed to connect to Rule34 after 5 attempts. Check your VPN/Proxy.")
                break

            if not results:
                if page == 0:
                    log_msg(name, f"0 images found for {TAGS}.")
                else:
                    log_msg(name, "End of database reached.")
                break

            for result in results:
                if stop_event.is_set() or (amount > 0 and downloaded >= amount):
                    break

                file_url = result.image
                if not file_url:
                    continue

                ext = file_url.split('.')[-1].lower()

                if ext in ["mp4", "webm", "zip"] and "-video" in exclusions:
                    continue
                if ext == "gif" and "-gif" in exclusions:
                    continue

                post_id = getattr(result, 'id', random.randint(1000, 99999))
                filename = f"{post_id}.{ext}"
                filepath = os.path.join(tag_dir, filename)

                if filename in dl_history or os.path.exists(filepath):
                    log_msg(name, f"[SKIP] {filename} (Already in history/disk)")
                    continue

                try:
                    resp = client.session.get(file_url, stream=True, timeout=30)
                    resp.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in resp.iter_content(8192):
                            if stop_event.is_set():
                                break
                            f.write(chunk)

                    if stop_event.is_set():
                        os.remove(filepath)
                        break

                    downloaded += 1
                    dl_history.add(filename)
                    save_history(site_root, dl_history)

                    log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                    time.sleep(random.uniform(0.6, 1.2))
                except Exception as e:
                    log_msg(name, f"[FAILED] {filename}: {e}")

            page += 1
            if not stop_event.is_set() and (amount == 0 or downloaded < amount):
                delay = random.uniform(3.0, 5.0)
                log_msg(name, f"Tactical pause... ({delay:.1f}s)")
                time.sleep(delay)

    except Exception as e:
        log_msg(name, f"Unexpected Error: {str(e)}")

    log_msg(name, "--- Worker Terminated ---")


# ----------------- SAFEBOORU WORKER -----------------
def worker_safebooru(tag, amount, net_config):
    name = "safe"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    tag = tag.strip().lower()
    log_msg(name, f"Initializing worker for tag: '{tag}'")

    site_root = os.path.join(MASTER_FOLDER, "Safebooru")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)
    session = get_session("safe", net_config)

    safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).replace(' ', '_')
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)

    downloaded = 0
    page = 1
    empty_pages = 0
    max_empty = 3
    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        try:
            log_msg(name, f"Scanning API... (Page {page})")
            limit_val = min(100, amount - downloaded if amount > 0 else 100)

            resp = session.get("https://safebooru.donmai.us/posts.json", params={"tags": tag, "page": page, "limit": limit_val}, timeout=15)
            if resp.status_code in [403, 429]:
                log_msg(name, f"ERROR {resp.status_code}. Change proxy.")
                break
            resp.raise_for_status()

            text_resp = resp.text.strip()
            if not text_resp or text_resp == "[]":
                if page == 1:
                    log_msg(name, f"ZERO images found for '{tag}'.")
                break

            raw_data = resp.json()
            if isinstance(raw_data, dict):
                if "success" in raw_data and not raw_data["success"]:
                    log_msg(name, f"API Alert: {raw_data.get('message', 'Unknown Error')}")
                    break
                posts = [raw_data]
            elif isinstance(raw_data, list):
                posts = raw_data
            else:
                break

            if not posts:
                break

        except Exception as e:
            err_str = str(e)
            if "403" in err_str:
                log_msg(name, "ERROR 403: Cloudflare/ISP block. You need a VPN or proxy to access Safebooru.")
            else:
                log_msg(name, f"API Error: {e}")
            time.sleep(5)
            continue

        page_downloaded = 0
        for post in posts:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount):
                break
            if not isinstance(post, dict):
                continue

            url = post.get("file_url") or post.get("large_file_url")
            if not url:
                continue
            if url.startswith("https://"):
                url = url.replace("https://", "http://")

            ext = (post.get("file_ext") or "").lower()
            if ext in ["mp4", "webm", "zip", "gif"]:
                continue

            filename = f"{post.get('id')}.{ext}"
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath):
                continue

            try:
                r = session.get(url, stream=True, timeout=20)
                r.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if stop_event.is_set():
                            break
                        f.write(chunk)
                if stop_event.is_set():
                    os.remove(filepath)
                    break

                downloaded += 1
                page_downloaded += 1
                dl_history.add(filename)
                save_history(site_root, dl_history)

                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                time.sleep(random.uniform(0.5, 2.0))
            except Exception as e:
                log_msg(name, f"[FAILED] {filename}: {e}")

        if page_downloaded == 0:
            empty_pages += 1
            if empty_pages >= max_empty:
                log_msg(name, f"No downloadable images found after {empty_pages} pages. Stopping.")
                break
        else:
            empty_pages = 0

        page += 1
        if not stop_event.is_set() and (amount == 0 or downloaded < amount):
            delay = random.uniform(3.0, 5.0)
            log_msg(name, f"Anti-ban pause... ({delay:.1f}s)")
            time.sleep(delay)

    log_msg(name, "--- Worker Terminated ---")


# ----------------- ZEROCHAN WORKER -----------------
def worker_zerochan(tag, amount, net_config):
    name = "zero"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    tag = tag.split('|')[0].strip()
    log_msg(name, f"Initializing worker for tag: '{tag}'")
    session = get_session("zero", net_config)

    site_root = os.path.join(MASTER_FOLDER, "Zerochan")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    try:
        r_resp = session.get(f"https://www.zerochan.net/{urllib.parse.quote_plus(tag)}", timeout=10, allow_redirects=True)
        if r_resp.url and "/search?q=" not in r_resp.url:
            real_tag = urllib.parse.unquote(r_resp.url.split('/')[-1]).replace('+', ' ')
            if real_tag and real_tag.lower() != tag.lower():
                tag = real_tag
    except Exception:
        pass

    safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).replace(' ', '_')
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)
    encoded_tag = urllib.parse.quote_plus(tag)

    downloaded = 0
    page = 1
    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        try:
            log_msg(name, f"Scanning API... (Page {page})")
            resp = session.get(f"https://www.zerochan.net/{encoded_tag}?json", params={"p": page, "l": 48}, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                log_msg(name, "End of database reached.")
                break
        except Exception as e:
            log_msg(name, f"Network/Limit: {e}")
            break

        for item in items:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount):
                break
            try:
                det_resp = session.get(f"https://www.zerochan.net/{item.get('id')}?json", timeout=10)
                img_url = det_resp.json().get("full") or det_resp.json().get("large")
            except Exception:
                continue
            if not img_url:
                continue

            filename = img_url.split('/')[-1]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath):
                continue

            try:
                r = session.get(img_url, stream=True, timeout=20)
                r.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if stop_event.is_set():
                            break
                        f.write(chunk)
                if stop_event.is_set():
                    os.remove(filepath)
                    break

                downloaded += 1
                dl_history.add(filename)
                save_history(site_root, dl_history)

                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                time.sleep(random.uniform(0.3, 1.2))
            except Exception as e:
                log_msg(name, f"[FAILED] {filename}")

        page += 1
        if not stop_event.is_set() and (amount == 0 or downloaded < amount):
            delay = random.uniform(3.0, 6.0)
            log_msg(name, f"Stealth delay... ({delay:.1f}s)")
            time.sleep(delay)

    log_msg(name, "--- Worker Terminated ---")


# ----------------- WAIFU WORKER -----------------
def worker_waifu(tag, amount, is_nsfw, net_config):
    name = "waifu"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    api_timeout = int(net_config.get("api_timeout", 10))
    retry_wait = int(net_config.get("retry_wait", 5))
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))

    tag = tag.lower()
    slug = waifu_name_to_slug(tag)
    log_msg(name, f"Initializing worker for tag: '{tag}' -> slug: '{slug}' (NSFW: {is_nsfw})")

    site_root = os.path.join(MASTER_FOLDER, "Waifu.im")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).replace(' ', '_')
    tag_dir = os.path.join(site_root, "nsfw_" + safe_tag if is_nsfw else safe_tag)
    os.makedirs(tag_dir, exist_ok=True)
    session = get_session("waifu", net_config)

    downloaded = 0
    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        params = {"IncludedTags": slug}
        if is_nsfw:
            params["IsNsfw"] = "true"

        try:
            log_msg(name, "Scanning API...")
            resp = session.get("https://api.waifu.im/images", params=params, timeout=api_timeout)
            if resp.status_code == 404:
                log_msg(name, "ERROR 404: Tag not found!")
                break
            elif resp.status_code == 403:
                log_msg(name, "ERROR 403: Adult tag detected. Check NSFW box.")
                break
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            total = data.get("totalCount", 0)
            if not items or total == 0:
                if is_nsfw:
                    log_msg(name, f"No NSFW images found for '{tag}'. Tag may not exist on Waifu.im.")
                    log_msg(name, "Available NSFW tags: ero, ecchi, hentai, milf, oppai, oral, ass, paizuri")
                else:
                    log_msg(name, f"No images found for '{tag}'. Tag may not exist on Waifu.im.")
                break
        except Exception as e:
            log_msg(name, f"API Error: {e}. Retrying in {retry_wait}s...")
            time.sleep(retry_wait)
            continue

        for img in items:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount):
                break
            url = img.get("url")
            if not url:
                continue

            filename = url.split('/')[-1]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath):
                continue

            try:
                r = session.get(url, stream=True, timeout=api_timeout)
                r.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if stop_event.is_set():
                            break
                        f.write(chunk)
                if stop_event.is_set():
                    os.remove(filepath)
                    break

                downloaded += 1
                dl_history.add(filename)
                save_history(site_root, dl_history)

                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
            except Exception as e:
                log_msg(name, f"[FAILED] {filename}: {e}")

        if not stop_event.is_set() and (amount == 0 or downloaded < amount):
            time.sleep(anti_ban_pause)

    log_msg(name, "--- Worker Terminated ---")


# ----------------- NEKO WORKER -----------------
def worker_nekos_best(category, amount, net_config):
    name = "neko"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    log_msg(name, f"Initializing worker for category: '{category}'")

    site_root = os.path.join(MASTER_FOLDER, "Nekos.best")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    cat_dir = os.path.join(site_root, category)
    os.makedirs(cat_dir, exist_ok=True)
    session = get_session("neko", net_config)

    downloaded = 0
    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        fetch_url = f"https://nekos.best/api/v2/{category}?amount={min(20, amount - downloaded if amount > 0 else 20)}"
        try:
            log_msg(name, "Scanning API...")
            resp = session.get(fetch_url, timeout=10)
            if resp.status_code in [403, 429]:
                log_msg(name, f"API BAN ({resp.status_code}). Change VPN node.")
                break
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                log_msg(name, "End of database reached.")
                break
        except Exception as e:
            log_msg(name, f"Network delay, retrying... ({e})")
            time.sleep(5)
            continue

        for item in results:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount):
                break
            url = item.get("url")
            if not url:
                continue

            filename = url.split('/')[-1]
            filepath = os.path.join(cat_dir, filename)

            if filename in dl_history or os.path.exists(filepath):
                continue

            try:
                r = session.get(url, stream=True, timeout=15)
                r.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if stop_event.is_set():
                            break
                        f.write(chunk)
                if stop_event.is_set():
                    os.remove(filepath)
                    break

                downloaded += 1
                dl_history.add(filename)
                save_history(site_root, dl_history)

                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                time.sleep(random.uniform(0.3, 1.2))
            except Exception as e:
                log_msg(name, f"[FAILED] {filename}: {e}")

        if not stop_event.is_set() and (amount == 0 or downloaded < amount):
            delay = random.uniform(3.5, 6.5)
            log_msg(name, f"Tactical pause... ({delay:.1f}s)")
            time.sleep(delay)

    log_msg(name, "--- Worker Terminated ---")


# ==========================================
# === MAIN ENTRY POINT ===
# ==========================================
if __name__ == "__main__":
    load_safe_db()
    load_waifu_tags()
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print(f"Starting Rem God Catcher Web UI on {url} ...")
    webbrowser.open(url)
    socketio.run(app, host="127.0.0.1", port=port, debug=False, allow_unsafe_werkzeug=True)
