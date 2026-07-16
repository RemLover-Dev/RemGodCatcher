import os
import threading
import json
import time
import requests
import asyncio
from requests.adapters import HTTPAdapter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FOLDER = os.path.join(BASE_DIR, "Rem God")
HISTORY_LOCK = threading.Lock()
STOP_EVENTS = {}

SAFE_TAGS_DB = []
WAIFU_TAGS_DB = []
WAIFU_TAG_MAP = {}

# --- LOGGING & TAG SYSTEM ---
def default_logger(worker_name, msg): print(f"[{worker_name.upper()}] {msg}")
log_callback = default_logger
def log_msg(worker_name, msg): log_callback(worker_name, msg)

def default_tag_handler(worker_name, filename, tags_list, artist_list): pass
tag_callback = default_tag_handler
def send_tags(worker_name, filename, tags_list, artist_list=None):
    if artist_list is None: artist_list = []
    tag_callback(worker_name, filename, tags_list, artist_list)

# --- HISTORY SYSTEM ---
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
        except Exception as e: print(f"Error saving history: {e}")

# ==========================================
# === OOP ASYNCIO ENGINE ===
# ==========================================
class BaseDownloader:
    def __init__(self, name, site_folder, amount, net_config):
        self.name = name
        self.site_folder = site_folder
        self.amount = int(amount)
        self.net_config = net_config

        if name in STOP_EVENTS and STOP_EVENTS[name] is not None: STOP_EVENTS[name].set()
        self.stop_event = threading.Event()
        STOP_EVENTS[name] = self.stop_event

        self.anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
        self.dl_retries = int(net_config.get("download_retries", 3))

        self.site_root = os.path.join(MASTER_FOLDER, site_folder)
        os.makedirs(self.site_root, exist_ok=True)
        self.dl_history = load_history(self.site_root)

        self.session = self._setup_session()
        self.downloaded_count = 0
        self.total_to_download = 0
        self.download_queue = None

    def _setup_session(self):
        session = requests.Session()
        if self.net_config.get("use_proxy"):
            p = self.net_config.get("proxy_url")
            session.proxies = {"http": p, "https": p}
        session.verify = self.net_config.get("verify_tls", False)

        session.headers.update({
            "User-Agent": "RemGodCatcher/4.0 (by RemLover on GitHub)",
            "Accept": "application/json"
        })
        return session

    def log(self, msg): log_msg(self.name, msg)

    def enqueue_download(self, url, filepath, filename, tags_list, artists=None):
        if artists is None: artists = []
        self.download_queue.put_nowait((url, filepath, filename, tags_list, artists))

    async def _async_download_file(self, url, filepath, filename, tags_list, artists):
        if self.stop_event.is_set(): return False
        if filename in self.dl_history or os.path.exists(filepath): return False

        for attempt in range(self.dl_retries):
            try:
                r = await asyncio.to_thread(self.session.get, url, stream=True, timeout=30, headers={"Referer": url})
                r.raise_for_status()
                def write_file():
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(65536):
                            if self.stop_event.is_set(): break
                            f.write(chunk)
                await asyncio.to_thread(write_file)

                if self.stop_event.is_set():
                    if os.path.exists(filepath): os.remove(filepath)
                    return False

                self.downloaded_count += 1
                self.dl_history.add(filename)
                save_history(self.site_root, self.dl_history)

                self.log(f"[SUCCESS] Downloaded {filename} ({self.downloaded_count}/{self.total_to_download})")
                send_tags(self.name, filename, tags_list, artists)
                return True

            except Exception as e:
                if self.stop_event.is_set(): break
                if attempt < self.dl_retries - 1: await asyncio.sleep(2)
                else: self.log(f"[FAILED] {filename}: {e}")
        return False

    async def _download_worker(self):
        while not self.stop_event.is_set():
            if self.download_queue.empty(): break
            item = await self.download_queue.get()
            try: await self._async_download_file(*item)
            finally: self.download_queue.task_done()

    async def run_async_loop(self, scraper_coroutine):
        self.download_queue = asyncio.Queue()

        self.log("Phase 1: Gathering links from API... Please wait.")
        try: await scraper_coroutine()
        except Exception as e: self.log(f"Scraper Error: {e}")

        self.total_to_download = self.download_queue.qsize()

        if self.total_to_download > 0 and not self.stop_event.is_set():
            self.log(f"Phase 2: Starting parallel download of {self.total_to_download} images...")

            num_workers = 8
            download_tasks = [asyncio.create_task(self._download_worker()) for _ in range(num_workers)]

            await self.download_queue.join()
            for t in download_tasks: t.cancel()

            self.log(f"--- All {self.downloaded_count} downloads completed successfully! ---")
        else:
            if not self.stop_event.is_set():
                self.log("Task finished. No new images to download.")
