import os
import time
import threading
import random
import re

import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history

def worker_rule34(tag, amount, method, sort_type, sort_order, exclusions, net_config):
    name = "rule34"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))
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

    if sort_order == "desc": TAGS.append(f"sort:{sort_type}")
    else: TAGS.append(f"sort:{sort_type}:{sort_order}")

    if exclusions: TAGS.extend(exclusions)

    log_msg(name, f"Final Payload sent to rule34Py: {TAGS}")

    site_root = os.path.join(shared.MASTER_FOLDER, "Rule34")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    clean_folder_name = " ".join([t for t in tag_list if not t.startswith('-')])
    safe_tag_dir = re.sub(r'[\\/*?:"<>|~]', "", clean_folder_name).strip().replace(' ', '_')
    if not safe_tag_dir: safe_tag_dir = "mixed_tags"

    tag_dir = os.path.join(site_root, safe_tag_dir)
    os.makedirs(tag_dir, exist_ok=True)

    try:
        from rule34Py import rule34Py
        client = rule34Py()

        api_key = os.getenv("RULE34_API_KEY", "")
        user_id_raw = os.getenv("RULE34_USER_ID", "0")
        user_id = int(user_id_raw) if user_id_raw.isdigit() else 0

        if api_key and user_id:
            client.api_key = api_key
            client.user_id = user_id
            log_msg(name, "API credentials loaded from .env")
        else:
            log_msg(name, "No API credentials found. Running in anonymous mode.")

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
        empty_pages = 0

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
                    else: raise e
                except Exception as e:
                    error_msg = str(e)
                    if "timeout" in error_msg.lower() or "read timed out" in error_msg.lower():
                        log_msg(name, f"Network Timeout (Attempt {attempt+1}/{max_retries}). Retrying in 3s...")
                        time.sleep(3)
                    else: raise e

            if results is None:
                log_msg(name, "Failed to connect to Rule34 after 5 attempts. Check your VPN/Proxy.")
                break

            if not results:
                if page == 0: log_msg(name, f"0 images found for {TAGS}.")
                else: log_msg(name, "End of database reached.")
                break

            page_downloaded = 0
            for result in results:
                if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
                file_url = result.image
                if not file_url: continue
                
                ext = file_url.split('.')[-1].lower()
                
                # --- VIDEO/IMAGE FILTERING LOGIC ---
                if ext in ["mp4", "webm", "zip"] and "-video" in exclusions: continue
                if ext in ["jpg", "jpeg", "png", "webp"] and "-image" in exclusions: continue
                if ext == "gif" and "-gif" in exclusions: continue

                post_id = getattr(result, 'id', random.randint(1000, 99999))
                filename = f"{post_id}.{ext}"
                filepath = os.path.join(tag_dir, filename)

                if filename in dl_history or os.path.exists(filepath):
                    log_msg(name, f"[SKIP] {filename} (Already in history/disk)")
                    continue

                success = False
                for dl_attempt in range(dl_retries):
                    try:
                        resp = client.session.get(file_url, stream=True, timeout=30)
                        resp.raise_for_status()
                        with open(filepath, 'wb') as f:
                            for chunk in resp.iter_content(8192):
                                if stop_event.is_set(): break
                                f.write(chunk)

                        if stop_event.is_set():
                            os.remove(filepath)
                            break

                        downloaded += 1
                        page_downloaded += 1
                        dl_history.add(filename)
                        save_history(site_root, dl_history)

                        tags_raw = getattr(result, 'tags', "")
                        if isinstance(tags_raw, str): tags_list = [t.strip() for t in tags_raw.split() if t.strip()]
                        else: tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]

                        log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                        shared.send_tags(name, filename, tags_list, [])
                        time.sleep(random.uniform(0.6, 1.2))
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

            page += 1
            if not stop_event.is_set() and (amount == 0 or downloaded < amount):
                if page_downloaded > 0:
                    empty_pages = 0
                    delay = random.uniform(anti_ban_pause, anti_ban_pause + 2.0)
                    log_msg(name, f"Anti-ban pause... ({delay:.1f}s)")
                    time.sleep(delay)
                else:
                    empty_pages += 1
                    if empty_pages >= 10:
                        empty_pages = 0
                        log_msg(name, "10 skipped pages, anti-spam pause... (5.0s)")
                        time.sleep(5.0)

    except Exception as e:
        log_msg(name, f"Unexpected Error: {str(e)}")

    log_msg(name, "--- Worker Terminated ---")