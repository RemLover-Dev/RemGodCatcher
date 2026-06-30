import os
import sys
import time
import threading
import json
import webbrowser
import urllib.parse
import urllib3

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO
from dotenv import load_dotenv

import shared  # هسته مرکزی و به اشتراک‌گذاری شده پروژه

# --- ورود توابع دانلود از ماژول‌های مجزا ---
from workers.rule34 import worker_rule34
from workers.safebooru import worker_safebooru
from workers.zerochan import worker_zerochan
from workers.waifu_im import worker_waifu
from workers.nekos_best import worker_nekos_best
from workers.nekos_life import worker_nekos_life
from workers.gelbooru import worker_gelbooru

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(os.path.join(shared.BASE_DIR, ".env"))

# --- تنظیمات اولیه ---
STARTUP_CONFIG = {
    "use_proxy": os.getenv("USE_PROXY", "false").lower() == "true",
    "proxy_url": os.getenv("PROXY_URL", "http://127.0.0.1:10808"),
    "verify_tls": os.getenv("VERIFY_TLS", "false").lower() == "true",
    "api_timeout": int(os.getenv("API_TIMEOUT", "10")),
    "retry_wait": int(os.getenv("RETRY_WAIT", "5")),
    "anti_ban_pause": float(os.getenv("ANTI_BAN_PAUSE", "3.0"))
}

app = Flask(__name__, static_folder="web")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# --- اتصال سیستم لاگ کارگران به وب‌سوکت فرانت‌اند ---
def socketio_logger(worker_name, msg):
    try:
        socketio.emit("python_log", {"worker": worker_name, "msg": msg})
    except Exception:
        print(f"[{worker_name.upper()}] {msg}")

shared.log_callback = socketio_logger

# --- لودر دیتابیس‌های تگ آفلاین ---
def load_safe_db():
    db_path = os.path.join(shared.BASE_DIR, "safe_tag_names.json")
    if not os.path.exists(db_path):
        db_path = os.path.join(shared.BASE_DIR, "tag_names.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                shared.SAFE_TAGS_DB = json.load(f)
            print(f"[SYSTEM] Loaded {len(shared.SAFE_TAGS_DB)} offline tags for Safebooru.")
        except Exception as e:
            print(f"[SYSTEM] Error parsing JSON: {e}")

def load_waifu_tags():
    tags_path = os.path.join(shared.BASE_DIR, "tags.json")
    if os.path.exists(tags_path):
        try:
            with open(tags_path, "r", encoding="utf-8") as f:
                shared.WAIFU_TAGS_DB = json.load(f)
            shared.WAIFU_TAG_MAP = {t["name"].lower(): t["slug"] for t in shared.WAIFU_TAGS_DB}
            print(f"[SYSTEM] Loaded {len(shared.WAIFU_TAGS_DB)} Waifu.im tags.")
        except Exception as e:
            print(f"[SYSTEM] Error loading tags.json: {e}")

# ==========================================
# === FLASK ROUTING & STATIC INTERFACE ===
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
    STARTUP_CONFIG.update(data)
    
    # ذخیره در فایل .env
    env_path = os.path.join(shared.BASE_DIR, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f: lines = f.readlines()

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
        if not matched: new_lines.append(line)

    for key, val in env_keys.items():
        if not found[key]: new_lines.append(f"{key}={val}\n")

    with open(env_path, "w", encoding="utf-8") as f: f.writelines(new_lines)
    return jsonify({"success": True})

@app.route("/api/folder", methods=["GET", "POST"])
def folder_manager():
    if request.method == "POST":
        data = request.json
        folder = data.get("folder", "")
        if folder:
            shared.MASTER_FOLDER = os.path.join(folder, "Rem God")
            return jsonify({"folder": shared.MASTER_FOLDER})
    return jsonify({"folder": shared.MASTER_FOLDER})

@app.route("/api/api-settings", methods=["GET", "POST"])
def api_settings_manager():
    env_path = os.path.join(shared.BASE_DIR, ".env")
    if request.method == "POST":
        data = request.json
        api_key = data.get("rule34_api_key", "")
        user_id = data.get("rule34_user_id", "")
        gel_api_key = data.get("gelbooru_api_key", "")
        gel_user_id = data.get("gelbooru_user_id", "")
        
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f: lines = f.readlines()
        
        env_keys = {
            "RULE34_API_KEY": api_key,
            "RULE34_USER_ID": user_id,
            "GELBOORU_API_KEY": gel_api_key,
            "GELBOORU_USER_ID": gel_user_id,
        }
        new_lines = []
        found = {k: False for k in env_keys}
        for line in lines:
            matched = False
            for key in env_keys:
                if line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key}={env_keys[key]}\n")
                    found[key] = True
                    matched = True
                    break
            if not matched:
                new_lines.append(line)
        for key, val in env_keys.items():
            if not found[key]:
                new_lines.append(f"{key}={val}\n")
        
        with open(env_path, "w", encoding="utf-8") as f: f.writelines(new_lines)
        for key, val in env_keys.items():
            os.environ[key] = val
        return jsonify({"success": True, "message": "API settings saved successfully!"})
        
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    return jsonify({
        "rule34_api_key": config.get("RULE34_API_KEY", ""),
        "rule34_user_id": config.get("RULE34_USER_ID", ""),
        "gelbooru_api_key": config.get("GELBOORU_API_KEY", ""),
        "gelbooru_user_id": config.get("GELBOORU_USER_ID", ""),
    })

# ==========================================
# === 🛠️ FIXED TAG AUTO-SUGGESTION API 🛠️ ===
# ==========================================
@app.route("/api/tags/waifu", methods=["POST"])
def get_waifu_tags_route():
    if shared.WAIFU_TAGS_DB:
        return jsonify([t["name"] for t in shared.WAIFU_TAGS_DB])
    net_config = request.json
    try:
        session = shared.get_session("waifu", net_config)
        resp = session.get("https://api.waifu.im/tags", timeout=10)
        data = resp.json()
        tags = [t.get("name", t.get("slug")) for t in data.get("items", [])]
        return jsonify(sorted(list(set([t for t in tags if t]))))
    except Exception:
        return jsonify(sorted(['maid', 'waifu', 'marin-kitagawa', 'mori-calliope', 'raiden-shogun', 'oppai', 'selfies', 'uniform', 'kamisato-ayaka', 'ero', 'ass', 'hentai', 'milf', 'oral', 'paizuri', 'ecchi']))

@app.route("/api/tags/neko", methods=["POST"])
def get_neko_tags_route():
    net_config = request.json
    try:
        session = shared.get_session("neko", net_config) # استفاده از تابع متصل به فیلترشکن هاب مرکزی
        resp = session.get("https://nekos.best/api/v2/endpoints", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        images = sorted([cat for cat, d in data.items() if d.get("format") == "png"])
        gifs = sorted([cat for cat, d in data.items() if d.get("format") == "gif"])
        return jsonify({"image": images, "gif": gifs})
    except Exception:
        return jsonify({"image": [], "gif": []})

@app.route("/api/tags/zerochan", methods=["POST"])
def get_zerochan_suggestions_route():
    data = request.json
    query = data.get("query", "")
    net_config = data.get("net_config", {})
    try:
        session = shared.get_session("zero", net_config)
        session.headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.zerochan.net/"})
        resp = session.get(f"https://www.zerochan.net/suggest?q={urllib.parse.quote_plus(query)}", timeout=5)
        if resp.status_code == 200:
            sugs = resp.json() if "{" in resp.text or "[" in resp.text else [s.strip() for s in resp.text.split('\n') if s.strip()]
            return jsonify(list(dict.fromkeys([s.split('|')[0].strip() for s in sugs])))
    except Exception: pass
    return jsonify([])

@app.route("/api/tags/safe", methods=["POST"])
def get_safe_suggestions_route():
    data = request.json
    query = data.get("query", "").lower()
    if not shared.SAFE_TAGS_DB: return jsonify([])
    return jsonify([t for t in shared.SAFE_TAGS_DB if t.startswith(query)][:50])

@app.route("/api/tags/gelbooru", methods=["POST"])
def get_gelbooru_suggestions_route():
    data = request.json
    query = data.get("query", "")
    net_config = data.get("net_config", {})
    if len(query) < 2: return jsonify([])
    try:
        session = shared.get_session("gelbooru", net_config)
        url = f"https://gelbooru.com/index.php?page=autocomplete2&term={urllib.parse.quote(query)}&type=tag_query&limit=20"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200:
            d = resp.json()
            return jsonify([item.get("value") for item in d if isinstance(item, dict) and "value" in item])
    except Exception: pass
    return jsonify([])

@app.route("/api/tags/rule34", methods=["POST"])
def get_rule34_suggestions_route():
    data = request.json
    query = data.get("query", "")
    net_config = data.get("net_config", {})
    if len(query) < 2: return jsonify([])
    try:
        session = shared.get_session("rule34", net_config)
        url = f"https://api.rule34.xxx/autocomplete.php?q={urllib.parse.quote(query)}"
        resp = session.get(url, timeout=3)
        if resp.status_code == 200:
            d = resp.json()
            return jsonify([item.get("value") for item in d if isinstance(item, dict) and "value" in item])
    except Exception: pass
    try:
        session = shared.get_session("rule34", net_config)
        url = f"https://gelbooru.com/index.php?page=autocomplete2&term={urllib.parse.quote(query)}&type=tag_query&limit=20"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200:
            d = resp.json()
            return jsonify([item.get("value") for item in d if isinstance(item, dict) and "value" in item])
    except Exception: pass
    return jsonify([])

# ==========================================
# === WORKER CONTROLLERS (Socket.IO) ===
# ==========================================
@socketio.on("start_worker")
def handle_start_worker(data):
    worker = data.get("worker")
    net_config = data.get("net_config", {})
    
    if worker == "rule34":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        method = data.get("method", "and")
        sort_type = data.get("sort_type", "id")
        sort_order = data.get("sort_order", "desc")
        exclusions = data.get("exclusions", [])
        threading.Thread(target=worker_rule34, args=(tag, limit, method, sort_type, sort_order, exclusions, net_config), daemon=True).start()
    elif worker == "safe":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        threading.Thread(target=worker_safebooru, args=(tag, limit, net_config), daemon=True).start()
    elif worker == "zero":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        threading.Thread(target=worker_zerochan, args=(tag, limit, net_config), daemon=True).start()
    elif worker == "waifu":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 30))
        nsfw = data.get("nsfw", False)
        threading.Thread(target=worker_waifu, args=(tag, limit, nsfw, net_config), daemon=True).start()
    elif worker == "neko":
        category = data.get("category", "")
        limit = int(data.get("limit", 20))
        threading.Thread(target=worker_nekos_best, args=(category, limit, net_config), daemon=True).start()
    elif worker == "nekos_life":
        category = data.get("category", "")
        limit = int(data.get("limit", 20))
        threading.Thread(target=worker_nekos_life, args=(category, limit, net_config), daemon=True).start()
    elif worker == "gelbooru":
        tag = data.get("tag", "")
        limit = int(data.get("limit", 50))
        exclusions = data.get("exclusions", [])
        threading.Thread(target=worker_gelbooru, args=(tag, limit, exclusions, net_config), daemon=True).start()

@socketio.on("stop_worker")
def handle_stop_worker(data):
    name = data.get("worker")
    shared.log_msg(name, ">>> STOP SIGNAL RECEIVED! Terminating connections immediately... <<<")
    if name in shared.STOP_EVENTS:
        shared.STOP_EVENTS[name].set()

if __name__ == "__main__":
    load_safe_db()
    load_waifu_tags()
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print(f"Starting Modular Rem God Catcher Engine on {url} ...")
    webbrowser.open(url)
    socketio.run(app, host="127.0.0.1", port=port, debug=False, allow_unsafe_werkzeug=True)