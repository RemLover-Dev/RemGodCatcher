import os
import time
import threading
import random
import re

import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session

def worker_gelbooru(tag, amount, exclusions, net_config):
    name = "gelbooru"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    tag = tag.strip().lower()
    log_msg(name, f"Initializing worker for tag: '{tag}'")

    site_root = os.path.join(shared.MASTER_FOLDER, "Gelbooru")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)
    session = get_session("gelbooru", net_config)
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))

    clean_tag = " ".join(t for t in tag.split() if not t.startswith('-'))
    safe_tag = re.sub(r'[\\/*?:"<>|]', "", clean_tag).replace(' ', '_')
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)

    api_key = os.getenv("GELBOORU_API_KEY", "")
    user_id = os.getenv("GELBOORU_USER_ID", "")

    downloaded = 0
    pid = 0

    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        try:
            log_msg(name, f"Scanning API... (Page {pid})")
            limit_val = min(100, amount - downloaded if amount > 0 else 100)

            params = {
                "page": "dapi",
                "s": "post",
                "q": "index",
                "tags": tag,
                "pid": pid,
                "limit": limit_val,
                "json": 1
            }
            if api_key and user_id:
                params["api_key"] = api_key
                params["user_id"] = user_id

            resp = session.get("https://gelbooru.com/index.php", params=params, timeout=15)
            if resp.status_code == 401:
                log_msg(name, "❌ ERROR 401: Unauthorized! Gelbooru blocked this request.")
                log_msg(name, "💡 FIX: You MUST enter a valid Gelbooru API Key & User ID in the Options Tab!")
                break
            elif resp.status_code in [403, 429]:
                log_msg(name, f"ERROR {resp.status_code}. Change proxy or slow down.")
                break
                
            resp.raise_for_status()
            data = resp.json()

            posts = data.get("post", [])
            if not posts:
                if pid == 0: log_msg(name, f"0 images found for '{tag}'.")
                else: log_msg(name, "End of database reached.")
                break

        except Exception as e:
            err_str = str(e)
            if "403" in err_str: log_msg(name, "ERROR 403: Cloudflare/ISP block. You need a VPN.")
            else: log_msg(name, f"API Error: {e}")
            time.sleep(5)
            continue

        page_downloaded = 0
        skipped = 0
        for post in posts:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
            if not isinstance(post, dict): continue

            file_url = post.get("file_url", "")
            if not file_url: continue

            ext = file_url.split('.')[-1].lower()
            
            # --- VIDEO/IMAGE FILTERING LOGIC ---
            if ext in ["mp4", "webm", "zip"] and "-video" in exclusions: continue
            if ext in ["jpg", "jpeg", "png", "webp"] and "-image" in exclusions: continue
            if ext == "gif" and "-gif" in exclusions: continue

            filename = file_url.split('/')[-1].split('?')[0]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath):
                skipped += 1
                continue

            success = False
            for dl_attempt in range(dl_retries):
                try:
                    r = session.get(file_url, stream=True, timeout=20, headers={"Referer": "https://gelbooru.com/"})
                    r.raise_for_status()

                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(8192):
                            if stop_event.is_set(): break
                            f.write(chunk)
                    if stop_event.is_set():
                        os.remove(filepath)
                        break

                    downloaded += 1
                    page_downloaded += 1
                    dl_history.add(filename)
                    save_history(site_root, dl_history)

                    tags_raw = post.get("tags", "")
                    tags_list = [t.strip() for t in tags_raw.split() if t.strip()]

                    log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                    shared.send_tags(name, filename, tags_list, [])
                    time.sleep(random.uniform(0.5, 1.5))
                    success = True
                    break
                except Exception as e:
                    if dl_attempt < 2:
                        log_msg(name, f"[RETRY {dl_attempt+1}/{dl_retries}] {filename}: {e}")
                        time.sleep(2)
                    else:
                        log_msg(name, f"[FAILED] {filename}: {e}")
            if not success:
                continue

        if skipped: log_msg(name, f"Skipped {skipped} images (already in history/disk)")

        pid += 1
        if page_downloaded > 0 and not stop_event.is_set() and (amount == 0 or downloaded < amount):
            log_msg(name, f"Anti-ban pause... ({anti_ban_pause:.1f}s)")
            time.sleep(anti_ban_pause)

    log_msg(name, "--- Worker Terminated ---")