import os
import threading
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FOLDER = os.path.join(os.getcwd(), "Rem God")
HISTORY_LOCK = threading.Lock()
STOP_EVENTS = {}

SAFE_TAGS_DB = []
WAIFU_TAGS_DB = []
WAIFU_TAG_MAP = {}

# --- LOGGING SYSTEM ---
def default_logger(worker_name, msg):
    print(f"[{worker_name.upper()}] {msg}")

log_callback = default_logger

def log_msg(worker_name, msg):
    log_callback(worker_name, msg)

# --- TAG HANDLER SYSTEM ---
def default_tag_handler(worker_name, filename, tags_list, artist_list):
    pass

tag_callback = default_tag_handler

def send_tags(worker_name, filename, tags_list, artist_list=[]):
    tag_callback(worker_name, filename, tags_list, artist_list)

# --- UTILITIES ---
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
    elif site in ["gelbooru", "rule34"]:
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"})
    elif site == "zero":
        session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/json,*/*"})
        retry_strategy = Retry(total=3, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    elif site in ["waifu", "neko"]:
        session.headers.update({"Accept": "application/json"})
    elif site == "yande":
        session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    return session