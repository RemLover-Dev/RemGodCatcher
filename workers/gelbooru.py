import os
import time
import threading
import random
import re

from shared import log_msg, STOP_EVENTS, MASTER_FOLDER, load_history, save_history, get_session

def worker_gelbooru(tag, amount, exclusions, net_config):
    name = "gelbooru"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    tag = tag.strip().lower()
    log_msg(name, f"Initializing worker for tag: '{tag}'")

    site_root = os.path.join(MASTER_FOLDER, "Gelbooru")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)
    session = get_session("gelbooru", net_config)
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))

    safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).replace(' ', '_')
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
            if resp.status_code in [403, 429]:
                log_msg(name, f"ERROR {resp.status_code}. Change proxy.")
                break
            resp.raise_for_status()

            data = resp.json()
            if "@attributes" in data and isinstance(data["@attributes"], dict):
                attr = data["@attributes"]
                if int(attr.get("count", 0)) == 0:
                    if pid == 0:
                        log_msg(name, f"0 images found for '{tag}'.")
                    break

            posts = data.get("post", [])
            if not posts:
                if pid == 0:
                    log_msg(name, f"0 images found for '{tag}'.")
                else:
                    log_msg(name, "End of database reached.")
                break

        except Exception as e:
            err_str = str(e)
            if "403" in err_str:
                log_msg(name, "ERROR 403: Cloudflare/ISP block. You need a VPN or proxy.")
            else:
                log_msg(name, f"API Error: {e}")
            time.sleep(5)
            continue

        page_downloaded = 0
        skipped = 0
        for post in posts:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
            if not isinstance(post, dict): continue

            file_url = post.get("file_url", "")
            if not file_url:
                directory = post.get("directory", "")
                image = post.get("image", "")
                if directory and image:
                    file_url = f"https://img.gelbooru.com/images/{directory}/{image}"
            if not file_url: continue

            ext = (post.get("image", "") or file_url.split('/')[-1]).split('.')[-1].lower()
            if ext in ["mp4", "webm", "zip"] and "-video" in exclusions: continue
            if ext == "gif" and "-gif" in exclusions: continue

            filename = file_url.split('/')[-1].split('?')[0]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath):
                skipped += 1
                continue

            try:
                r = session.get(file_url, stream=True, timeout=20, headers={"Referer": "https://gelbooru.com/"})
                r.raise_for_status()

                content_type = r.headers.get("Content-Type", "").lower()
                if not content_type.startswith(("image/", "video/")):
                    log_msg(name, f"[SKIP] {filename}: Not an image/video ({content_type})")
                    continue

                actual_ext = content_type.split('/')[-1].split(';')[0].lower()
                if actual_ext in ["jpeg", "pjpeg"]:
                    actual_ext = "jpg"
                if actual_ext not in ["jpg", "jpeg", "png", "gif", "webp", "mp4", "webm"]:
                    actual_ext = ext

                base, old_ext = os.path.splitext(filename)
                if actual_ext and actual_ext != old_ext.lstrip('.'):
                    filename = f"{base}.{actual_ext}"
                    filepath = os.path.join(tag_dir, filename)

                if os.path.exists(filepath):
                    skipped += 1
                    continue

                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if stop_event.is_set(): break
                        f.write(chunk)
                if stop_event.is_set():
                    os.remove(filepath)
                    break

                if os.path.getsize(filepath) < 1024:
                    os.remove(filepath)
                    log_msg(name, f"[SKIP] {filename}: File too small, likely a placeholder")
                    continue

                downloaded += 1
                page_downloaded += 1
                dl_history.add(filename)
                save_history(site_root, dl_history)

                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                log_msg(name, f"[FAILED] {filename}: {e}")

        if skipped:
            log_msg(name, f"Skipped {skipped} images (already in history/disk)")

        pid += 1
        if page_downloaded > 0 and not stop_event.is_set() and (amount == 0 or downloaded < amount):
            log_msg(name, f"Anti-ban pause... ({anti_ban_pause:.1f}s)")
            time.sleep(anti_ban_pause)

    log_msg(name, "--- Worker Terminated ---")
