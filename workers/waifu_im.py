import os
import time
import threading
import random
import re

from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session
import shared

def waifu_name_to_slug(name):
    name_lower = name.lower().strip()
    if name_lower in shared.WAIFU_TAG_MAP:
        return shared.WAIFU_TAG_MAP[name_lower]
    return name_lower

def worker_waifu(tag, amount, is_nsfw, net_config):
    name = "waifu"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    api_timeout = int(net_config.get("api_timeout", 10))
    retry_wait = int(net_config.get("retry_wait", 5))
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))

    tag = tag.lower()
    slug = waifu_name_to_slug(tag)
    log_msg(name, f"Initializing worker for tag: '{tag}' -> slug: '{slug}' (NSFW: {is_nsfw})")

    site_root = os.path.join(shared.MASTER_FOLDER, "Waifu.im")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    clean_tag = " ".join(t for t in tag.split() if not t.startswith('-'))
    safe_tag = re.sub(r'[\\/*?:"<>|]', "", clean_tag).replace(' ', '_')
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
            if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
            url = img.get("url")
            if not url: continue

            filename = url.split('/')[-1]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath): continue

            success = False
            for dl_attempt in range(dl_retries):
                try:
                    r = session.get(url, stream=True, timeout=api_timeout)
                    r.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(8192):
                            if stop_event.is_set(): break
                            f.write(chunk)
                    if stop_event.is_set():
                        os.remove(filepath)
                        break

                    downloaded += 1
                    dl_history.add(filename)
                    save_history(site_root, dl_history)

                    log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
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

        if not stop_event.is_set() and (amount == 0 or downloaded < amount):
            time.sleep(anti_ban_pause)

    log_msg(name, "--- Worker Terminated ---")