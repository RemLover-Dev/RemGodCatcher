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

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# تنظیم مسیرها برای زمانی که فایل .exe می‌شود
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    STATIC_FOLDER = os.path.join(sys._MEIPASS, "web")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_FOLDER = "web"

load_dotenv(os.path.join(BASE_DIR, ".env"))

import shared 
from workers.rule34 import worker_rule34
from workers.safebooru import worker_safebooru
from workers.zerochan import worker_zerochan
from workers.waifu_im import worker_waifu
from workers.nekos_best import worker_nekos_best
from workers.gelbooru import worker_gelbooru
from workers.nekos_life import worker_nekos_life
from workers.yande import worker_yande
from workers.konachan import worker_konachan

STOP_EVENTS = {}
SAFE_TAGS_DB = []
YANDE_TAGS_DB = []
KONA_TAGS_DB = []
WAIFU_TAGS_DB = []
WAIFU_TAG_MAP = {}
MASTER_FOLDER = os.path.join(BASE_DIR, "Rem God")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
HISTORY_LOCK = threading.Lock()

STARTUP_CONFIG = {
    "use_proxy": os.getenv("USE_PROXY", "false").lower() == "true",
    "proxy_url": os.getenv("PROXY_URL", "http://127.0.0.1:10808"),
    "verify_tls": os.getenv("VERIFY_TLS", "false").lower() == "true",
    "api_timeout": int(os.getenv("API_TIMEOUT", "10")),
    "retry_wait": int(os.getenv("RETRY_WAIT", "5")),
    "anti_ban_pause": float(os.getenv("ANTI_BAN_PAUSE", "3.0")),
    "download_retries": int(os.getenv("DOWNLOAD_RETRIES", "3"))
}

app = Flask(__name__, static_folder=STATIC_FOLDER)
socketio = SocketIO(app, cors_allowed_origins="*")

# متغیر کنترل‌کننده زمان بسته شدن
shutdown_timer = None

def load_history(site_root):
    hist_path = os.path.join(site_root, "download_history.json")
    with HISTORY_LOCK:
        if os.path.exists(hist_path):
            try:
                with open(hist_path, "r", encoding="utf-8") as f: return set(json.load(f))
            except Exception: return set()
        return set()

def save_history(site_root, history_set):
    hist_path = os.path.join(site_root, "download_history.json")
    with HISTORY_LOCK:
        try:
            with open(hist_path, "w", encoding="utf-8") as f: json.dump(list(history_set), f, indent=4)
        except Exception: pass

def log_msg(worker_name, msg):
    try: socketio.emit("python_log", {"worker": worker_name, "msg": msg})
    except Exception: print(f"[{worker_name.upper()}] {msg}")

shared.log_callback = log_msg

def socketio_tag_handler(worker_name, filename, tags_list, artist_list):
    try:
        hist = load_json_db(IMAGE_HISTORY_FILE)
        entry = {
            "site": worker_name,
            "filename": filename,
            "tags": [t.strip() for t in tags_list if t.strip()],
            "artists": [a.strip() for a in artist_list if a.strip()]
        }
        hist.insert(0, entry)
        hist = hist[:100]
        save_json_db(IMAGE_HISTORY_FILE, hist)
        socketio.emit("update_history")
    except Exception as e:
        print("Image Tag Save Error:", e)

shared.tag_callback = socketio_tag_handler
# ❌ خط بازنویسی STOP_EVENTS را کاملاً حذف کردیم تا ارتباط قطع نشود!
shared.MASTER_FOLDER = MASTER_FOLDER

def load_waifu_tags():
    global WAIFU_TAGS_DB, WAIFU_TAG_MAP
    tags_path = os.path.join(BASE_DIR, "tags.json")
    if os.path.exists(tags_path):
        try:
            with open(tags_path, "r", encoding="utf-8") as f: WAIFU_TAGS_DB = json.load(f)
            WAIFU_TAG_MAP = {t["name"].lower(): t["slug"] for t in WAIFU_TAGS_DB}
        except Exception: pass

def get_session(site, net_config):
    session = requests.Session()
    if net_config.get("use_proxy"):
        p = net_config.get("proxy_url")
        session.proxies = {"http": p, "https": p}
    else:
        session.proxies = {"http": "", "https": "", "no_proxy": "*"}
    session.verify = net_config.get("verify_tls", False)

    if site == "safe": session.headers.update({"User-Agent": "RemGodCatcher/2.0", "Accept": "application/json"})
    elif site == "zero":
        session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/json,*/*"})
        adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"]))
        session.mount("https://", adapter); session.mount("http://", adapter)
    elif site in ["waifu", "neko"]: session.headers.update({"Accept": "application/json"})
    elif site == "yande": session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    return session

def load_safe_db():
    global SAFE_TAGS_DB
    db_path = os.path.join(DATABASE_DIR, "safe_tag_names.json")
    if not os.path.exists(db_path): db_path = os.path.join(DATABASE_DIR, "tag_names.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f: SAFE_TAGS_DB = json.load(f)
        except Exception: pass

def load_yande_db():
    global YANDE_TAGS_DB
    db_path = os.path.join(DATABASE_DIR, "yande_tag_names.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f: YANDE_TAGS_DB = json.load(f)
        except Exception: pass

def load_kona_db():
    global KONA_TAGS_DB
    db_path = os.path.join(DATABASE_DIR, "kona_tag_names.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f: KONA_TAGS_DB = json.load(f)
        except Exception: pass

@app.route("/")
def index(): return send_from_directory(STATIC_FOLDER, "index.html")

@app.route("/user_wallpapers/<path:filename>")
def custom_wallpaper(filename):
    custom_dir = os.path.join(BASE_DIR, "user_wallpapers")
    if os.path.exists(os.path.join(custom_dir, filename)):
        return send_from_directory(custom_dir, filename)
    return send_from_directory(os.path.join(STATIC_FOLDER, "wallpaper"), filename)

@app.route("/api/upload_wallpaper", methods=["POST"])
def upload_wallpaper():
    if "file" not in request.files: return jsonify({"success": False, "error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "": return jsonify({"success": False, "error": "No selected file"}), 400
    
    custom_dir = os.path.join(BASE_DIR, "user_wallpapers")
    os.makedirs(custom_dir, exist_ok=True)
    
    filename = "".join([c for c in file.filename if c.isalpha() or c.isdigit() or c in " ._-"]).rstrip()
    if not filename: filename = f"wallpaper_{random.randint(1000, 9999)}.png"
        
    file.save(os.path.join(custom_dir, filename))
    return jsonify({"success": True, "filename": filename})

@app.route("/<path:path>")
def static_files(path): return send_from_directory(STATIC_FOLDER, path)

@app.route("/api/config", methods=["GET", "POST"])
def config_manager():
    global STARTUP_CONFIG
    if request.method == "POST":
        data = request.json
        for key in data:
            if key in STARTUP_CONFIG: STARTUP_CONFIG[key] = data[key]

        env_path = os.path.join(BASE_DIR, ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f: lines = f.readlines()
        if lines and not lines[-1].endswith("\n"): lines[-1] += "\n"

        env_keys = {
            "USE_PROXY": str(STARTUP_CONFIG['use_proxy']).lower(),
            "PROXY_URL": STARTUP_CONFIG['proxy_url'],
            "VERIFY_TLS": str(STARTUP_CONFIG['verify_tls']).lower(),
            "API_TIMEOUT": str(STARTUP_CONFIG['api_timeout']),
            "RETRY_WAIT": str(STARTUP_CONFIG['retry_wait']),
            "ANTI_BAN_PAUSE": str(STARTUP_CONFIG['anti_ban_pause']),
            "DOWNLOAD_RETRIES": str(STARTUP_CONFIG['download_retries'])
        }

        new_lines = []
        found = {k: False for k in env_keys}
        for line in lines:
            stripped = line.strip()
            matched = False
            for key, val in env_keys.items():
                if stripped.startswith(f"{key}="):
                    new_lines.append(f"{key}={val}\n")
                    found[key] = True; matched = True; break
            if not matched: new_lines.append(line)

        for key, val in env_keys.items():
            if not found[key]: new_lines.append(f"{key}={val}\n")

        with open(env_path, "w", encoding="utf-8") as f: f.writelines(new_lines)
        return jsonify({"success": True})
    return jsonify(STARTUP_CONFIG)

@app.route("/api/folder", methods=["GET", "POST"])
def folder_manager():
    if request.method == "POST":
        folder = request.json.get("folder", "")
        if folder:
            shared.MASTER_FOLDER = os.path.join(folder, "Rem God")
            return jsonify({"folder": shared.MASTER_FOLDER})
    return jsonify({"folder": shared.MASTER_FOLDER})

@app.route("/api/api-settings", methods=["GET", "POST"])
def api_settings_manager():
    env_path = os.path.join(BASE_DIR, ".env")
    if request.method == "POST":
        data = request.json
        keys_to_save = {
            "RULE34_API_KEY": data.get("rule34_api_key", ""),
            "RULE34_USER_ID": data.get("rule34_user_id", ""),
            "GELBOORU_API_KEY": data.get("gelbooru_api_key", ""),
            "GELBOORU_USER_ID": data.get("gelbooru_user_id", "")
        }
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f: lines = f.readlines()
        if lines and not lines[-1].endswith("\n"): lines[-1] += "\n"

        new_lines = []
        found_keys = {k: False for k in keys_to_save}
        for line in lines:
            stripped = line.strip()
            matched = False
            for key, val in keys_to_save.items():
                if stripped.startswith(f"{key}="):
                    new_lines.append(f"{key}={val}\n")
                    found_keys[key] = True; matched = True; break
            if not matched: new_lines.append(line)

        for key, val in keys_to_save.items():
            if not found_keys[key]: new_lines.append(f"{key}={val}\n")

        with open(env_path, "w", encoding="utf-8") as f: f.writelines(new_lines)
        for k, v in keys_to_save.items(): os.environ[k] = v
        return jsonify({"success": True, "message": "All API keys saved successfully!"})

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
        "gelbooru_user_id": config.get("GELBOORU_USER_ID", "")
    })

@app.route("/api/tags/waifu", methods=["POST"])
def get_waifu_tags():
    if WAIFU_TAGS_DB: return jsonify([t["name"] for t in WAIFU_TAGS_DB])
    net_config = request.json
    try:
        session = get_session("waifu", net_config)
        resp = session.get("https://api.waifu.im/tags", timeout=10)
        return jsonify(sorted(list(set([t.get("name", t.get("slug")) for t in resp.json().get("items", []) if t]))))
    except Exception: return jsonify(['maid', 'waifu', 'oppai', 'ero', 'ass', 'hentai', 'milf', 'paizuri', 'ecchi'])

@app.route("/api/tags/zerochan", methods=["POST"])
def get_zerochan_suggestions():
    data = request.json
    query = data.get("query", "")
    try:
        session = get_session("zero", data.get("net_config", {}))
        session.headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.zerochan.net/"})
        resp = session.get(f"https://www.zerochan.net/suggest?q={urllib.parse.quote_plus(query)}", timeout=5)
        if resp.status_code == 200:
            sugs = resp.json() if "{" in resp.text or "[" in resp.text else [s.strip() for s in resp.text.split('\n') if s.strip()]
            return jsonify(list(dict.fromkeys([s.split('|')[0].strip() for s in sugs])))
    except Exception: pass
    return jsonify([])

@app.route("/api/tags/safe", methods=["POST"])
def get_safe_suggestions():
    query = request.json.get("query", "").lower()
    if not SAFE_TAGS_DB: return jsonify([])
    return jsonify([t for t in SAFE_TAGS_DB if t.startswith(query)][:50])

@app.route("/api/tags/rule34", methods=["POST"])
def get_rule34_suggestions():
    data = request.json
    query = data.get("query", "")
    if len(query) < 2: return jsonify([])
    try:
        session = get_session("rule34", data.get("net_config", {}))
        url = f"https://api.rule34.xxx/autocomplete.php?q={urllib.parse.quote(query)}"
        resp = session.get(url, timeout=3)
        if resp.status_code == 200: return jsonify([item.get("value") for item in resp.json() if isinstance(item, dict) and "value" in item])
    except Exception: pass
    try:
        session = get_session("rule34", data.get("net_config", {}))
        url = f"https://gelbooru.com/index.php?page=autocomplete2&term={urllib.parse.quote(query)}&type=tag_query&limit=20"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200: return jsonify([item.get("value") for item in resp.json() if isinstance(item, dict) and "value" in item])
    except Exception: pass
    return jsonify([])

@app.route("/api/tags/yande", methods=["POST"])
def get_yande_suggestions():
    query = request.json.get("query", "").lower()
    if not YANDE_TAGS_DB: return jsonify([])
    return jsonify([t for t in YANDE_TAGS_DB if t.startswith(query)][:50])

@app.route("/api/tags/kona", methods=["POST"])
def get_kona_suggestions():
    query = request.json.get("query", "").lower()
    if not KONA_TAGS_DB: return jsonify([])
    return jsonify([t for t in KONA_TAGS_DB if t.startswith(query)][:50])

# --- TAG HISTORY & FAVORITES API ---
TAG_HISTORY_FILE = os.path.join(DATABASE_DIR, "tag_history.json")
FAV_TAGS_FILE = os.path.join(DATABASE_DIR, "fav_tags.json")
IMAGE_HISTORY_FILE = os.path.join(DATABASE_DIR, "image_history.json")
UI_CONFIG_FILE = os.path.join(DATABASE_DIR, "ui_config.json")

def load_json_db(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

def save_json_db(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f)

@app.route("/api/history", methods=["GET"])
def get_tag_history(): return jsonify(load_json_db(TAG_HISTORY_FILE))

@app.route("/api/history/clear", methods=["POST"])
def clear_tag_history():
    save_json_db(TAG_HISTORY_FILE, [])
    return jsonify({"success": True})

@app.route("/api/history/remove", methods=["POST"])
def remove_tag_history():
    data = request.json
    hist = load_json_db(TAG_HISTORY_FILE)
    hist = [x for x in hist if not (x["site"] == data["site"] and x["tag"] == data["tag"])]
    save_json_db(TAG_HISTORY_FILE, hist)
    return jsonify({"success": True})

@app.route("/api/image_history", methods=["GET"])
def get_image_history(): return jsonify(load_json_db(IMAGE_HISTORY_FILE))

@app.route("/api/image_history/clear", methods=["POST"])
def clear_image_history():
    save_json_db(IMAGE_HISTORY_FILE, [])
    return jsonify({"success": True})

@app.route("/api/image_history/remove", methods=["POST"])
def remove_image_history():
    data = request.json
    hist = [x for x in load_json_db(IMAGE_HISTORY_FILE) if x.get("filename") != data.get("filename")]
    save_json_db(IMAGE_HISTORY_FILE, hist)
    return jsonify({"success": True})

@app.route("/api/favorites", methods=["GET", "POST"])
def manage_favorites():
    favs = load_json_db(FAV_TAGS_FILE)
    if request.method == "POST":
        data = request.json
        action = data.get("action")
        entry = {"site": data.get("site"), "tag": data.get("tag")}
        if action == "add" and entry not in favs: favs.append(entry)
        elif action == "remove" and entry in favs: favs.remove(entry)
        save_json_db(FAV_TAGS_FILE, favs)
        return jsonify({"success": True, "favorites": favs})
    return jsonify(favs)


@app.route("/api/ui_config", methods=["GET", "POST"])
def manage_ui_config():
    default_config = {
        "theme_mode": "dark",
        "wallpapers": {
            "Main": {"dark": "Rem_main_d.png", "light": "Rem_main_l.png"},
            "Neko": {"dark": "Rem_neko_d.png", "light": "Rem_neko_l.png"},
            "NekosLife": {"dark": "Rem_nekolife_d.png", "light": "Rem_nekolife_l.png"},
            "Zero": {"dark": "Rem_zero_d.png", "light": "Rem_zero_l.png"},
            "Waifu": {"dark": "Rem_waifu_d.png", "light": "Rem_waifu_l.png"},
            "Safe": {"dark": "Rem_safe_d.png", "light": "Rem_safe_l.png"},
            "Gelbooru": {"dark": "Rem_gelbooru_d.png", "light": "Rem_gelbooru_l.png"},
            "Rule34": {"dark": "Rem_rule34_d.png", "light": "Rem_rule34_l.png"},
            "Yande": {"dark": "Rem_yande_d.png", "light": "Rem_yande_l.png"},
            "Kona": {"dark": "Rem_kona_d.png", "light": "Rem_kona_l.png"},
            "History": {"dark": "Rem_history_d.png", "light": "Rem_history_l.png"},
            "Options": {"dark": "Rem_option_d.png", "light": "Rem_option_l.png"},
            "Customize": {"dark": "Rem_custom_d.png", "light": "Rem_custom_l.png"}
        },
        "colors": {
            "dark": {
                "title": "#00d2d3", "text": "#ffffff", "accent": "#ff9ff3", "tab_text": "#ffffff",
                "btn_start_bg": "#00d2d3", "btn_start_text": "#0a0a0a",
                "btn_stop_bg": "#ff9ff3", "btn_stop_text": "#1a0a1a"
            },
            "light": {
                "title": "#0097e6", "text": "#2f3640", "accent": "#8c7ae6", "tab_text": "#1a1a2e",
                "btn_start_bg": "#0097e6", "btn_start_text": "#ffffff",
                "btn_stop_bg": "#8c7ae6", "btn_stop_text": "#ffffff"
            }
        }
    }

    if request.method == "POST":
        data = request.json
        save_json_db(UI_CONFIG_FILE, data)
        return jsonify({"success": True})

    config = load_json_db(UI_CONFIG_FILE)
    if not config:
        config = default_config
        save_json_db(UI_CONFIG_FILE, config)
    return jsonify(config)


# ==========================================
# === AUTO-SHUTDOWN SYSTEM ===
# ==========================================
@socketio.on("connect")
def handle_connect():
    global shutdown_timer
    if shutdown_timer:
        shutdown_timer.cancel()
        shutdown_timer = None
    print("Browser Tab Connected!")

@socketio.on("disconnect")
def handle_disconnect():
    global shutdown_timer
    print("Browser Tab Closed! Shutting down in 3 seconds if not reconnected...")

    def shutdown_server():
        print(">>> No active tabs. Killing Rem God Catcher Server... <<<")
        os._exit(0)  # این دستور کل فرآیند پایتون را بلافاصله نابود می‌کند

    shutdown_timer = threading.Timer(3.0, shutdown_server)
    shutdown_timer.start()
# ==========================================

@socketio.on("start_worker")
def handle_start_worker(data):
    worker = data.get("worker")
    net_config = data.get("net_config", {})
    
    # گرفتن تگ (در بعضی سایتها اسمش tag است و در بعضی category)
    tag = data.get("tag", data.get("category", "")).strip()

    # ذخیره اتوماتیک هیستوری برای *همه* سایتها (بدون استثنا)
    if tag:
        try:
            hist = load_json_db(TAG_HISTORY_FILE)
            entry = {"site": worker, "tag": tag}
            if entry not in hist:
                hist.insert(0, entry) # اضافه کردن به اول لیست
                save_json_db(TAG_HISTORY_FILE, hist)
        except Exception as e:
            print("History Save Error:", e)

    # استارت کارگرها
    if worker == "zero": threading.Thread(target=worker_zerochan, args=(data.get("tag", ""), int(data.get("limit", 50)), net_config), daemon=True).start()
    elif worker == "waifu": threading.Thread(target=worker_waifu, args=(data.get("tag", ""), int(data.get("limit", 30)), data.get("nsfw", False), net_config), daemon=True).start()
    elif worker == "neko": threading.Thread(target=worker_nekos_best, args=(data.get("category", ""), int(data.get("limit", 20)), net_config), daemon=True).start()
    elif worker == "safe": threading.Thread(target=worker_safebooru, args=(data.get("tag", ""), int(data.get("limit", 50)), data.get("exclusions", []), net_config), daemon=True).start()
    elif worker == "rule34": threading.Thread(target=worker_rule34, args=(data.get("tag", ""), int(data.get("limit", 50)), data.get("method", "and"), data.get("sort_type", "id"), data.get("sort_order", "desc"), data.get("exclusions", []), net_config), daemon=True).start()
    elif worker == "gelbooru": threading.Thread(target=worker_gelbooru, args=(data.get("tag", ""), int(data.get("limit", 50)), data.get("exclusions", []), net_config), daemon=True).start()
    elif worker == "nekos_life": threading.Thread(target=worker_nekos_life, args=(data.get("category", ""), int(data.get("limit", 20)), net_config), daemon=True).start()
    elif worker == "yande": threading.Thread(target=worker_yande, args=(data.get("tag", ""), int(data.get("limit", 50)), data.get("rating", ""), net_config), daemon=True).start()
    elif worker == "kona": threading.Thread(target=worker_konachan, args=(data.get("tag", ""), int(data.get("limit", 50)), data.get("rating", ""), data.get("exclusions", []), net_config), daemon=True).start()

@socketio.on("stop_worker")
def handle_stop_worker(data):
    name = data.get("worker")
    shared.log_msg(name, ">>> STOP SIGNAL RECEIVED! Terminating connections... <<<")
    if name in shared.STOP_EVENTS: shared.STOP_EVENTS[name].set()

if __name__ == "__main__":
    load_safe_db()
    load_waifu_tags()
    load_yande_db()
    load_kona_db()
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print(f"Starting Rem God Catcher Web UI on {url} ...")
    webbrowser.open(url)
    socketio.run(app, host="127.0.0.1", port=port, debug=False, allow_unsafe_werkzeug=True)