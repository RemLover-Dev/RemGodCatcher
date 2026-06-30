import os
import time
import threading
import random
import re

from shared import log_msg, STOP_EVENTS, MASTER_FOLDER, load_history, save_history, get_session

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
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))

    safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).replace(' ', '_')
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)

    limit = min(200, amount) if amount > 0 else 200
    page = 1
    pending = []

    log_msg(name, "Phase 1: Scanning pages for new files...")

    while not stop_event.is_set() and (amount == 0 or len(pending) < amount):
        try:
            log_msg(name, f"Scanning API... (Page {page}, collected {len(pending)} so far)")
            resp = session.get("https://safebooru.donmai.us/posts.json", params={"tags": tag, "page": page, "limit": limit}, timeout=15)
            if resp.status_code in [403, 429]:
                log_msg(name, f"ERROR {resp.status_code}. Change proxy.")
                break
            resp.raise_for_status()

            text_resp = resp.text.strip()
            if not text_resp or text_resp == "[]":
                if page == 1:
                    log_msg(name, f"ZERO images found for '{tag}'.")
                else:
                    log_msg(name, "End of results reached.")
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

            found_on_page = 0
            for post in posts:
                if stop_event.is_set() or (amount > 0 and len(pending) >= amount):
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

                post_id = post.get("id")
                if not post_id:
                    continue

                filename = f"{post_id}.{ext}"
                filepath = os.path.join(tag_dir, filename)

                if filename in dl_history or os.path.exists(filepath):
                    continue

                pending.append((url, filename, filepath))
                found_on_page += 1

            if found_on_page == 0 and posts:
                log_msg(name, f"No new files on page {page} (all in history or filtered).")

        except Exception as e:
            err_str = str(e)
            if "403" in err_str:
                log_msg(name, "ERROR 403: Cloudflare/ISP block. You need a VPN or proxy to access Safebooru.")
            else:
                log_msg(name, f"API Error: {e}")
            time.sleep(5)
            continue

        page += 1
        if not stop_event.is_set() and (amount == 0 or len(pending) < amount):
            time.sleep(anti_ban_pause)

    if stop_event.is_set() or not pending:
        if not pending:
            log_msg(name, "No new files to download.")
        log_msg(name, "--- Worker Terminated ---")
        return

    if amount > 0:
        pending = pending[:amount]

    log_msg(name, f"Phase 2: Downloading {len(pending)} files...")

    downloaded = 0
    for url, filename, filepath in pending:
        if stop_event.is_set() or (amount > 0 and downloaded >= amount):
            break

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
            dl_history.add(filename)
            save_history(site_root, dl_history)

            log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{len(pending)})")
            time.sleep(random.uniform(0.5, 2.0))
        except Exception as e:
            log_msg(name, f"[FAILED] {filename}: {e}")

    log_msg(name, "--- Worker Terminated ---")