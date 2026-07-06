import os, time, threading, random, re
import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session

def worker_safebooru(tag, amount, exclusions, net_config):
    name = "safe"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))
    tag = tag.strip().lower()
    log_msg(name, f"Initializing worker for tag: '{tag}'")

    site_root = os.path.join(shared.MASTER_FOLDER, "Safebooru")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)
    session = get_session("safe", net_config)

    clean_tag = " ".join(t for t in tag.split() if not t.startswith('-'))
    safe_tag = re.sub(r'[\\/*?"<>|]', "", clean_tag)
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)

    collected = []
    pid = 0

    while not stop_event.is_set() and (amount == 0 or len(collected) < amount):
        try:
            log_msg(name, f"Scanning API... (Page {pid})")
            limit_val = min(100, amount - len(collected) if amount > 0 else 100)

            resp = session.get("https://safebooru.org/index.php", params={
                "page": "dapi", "s": "post", "q": "index",
                "tags": tag, "pid": pid, "limit": limit_val, "json": 1
            }, timeout=15)
            if resp.status_code in [403, 429]:
                log_msg(name, f"ERROR {resp.status_code}. Change proxy.")
                break
            resp.raise_for_status()

            data = resp.json()
            if isinstance(data, dict):
                posts = data.get("post", [])
            elif isinstance(data, list):
                posts = data
            else:
                posts = []
            if not posts:
                if pid == 0: log_msg(name, f"ZERO images found for '{tag}'.")
                else: log_msg(name, "End of database reached.")
                break

        except Exception as e:
            err_str = str(e)
            if "403" in err_str: log_msg(name, "ERROR 403: Cloudflare/ISP block. You need a VPN.")
            else: log_msg(name, f"API Error: {e}")
            time.sleep(5)
            continue

        had_valid = False
        for post in posts:
            if stop_event.is_set() or (amount > 0 and len(collected) >= amount): break
            if not isinstance(post, dict): continue

            file_url = post.get("file_url") or post.get("large_file_url")
            if not file_url: continue

            ext = file_url.split('.')[-1].lower().split('?')[0]
            if ext in ["mp4", "webm", "zip"] and "-video" in exclusions: continue
            if ext in ["jpg", "jpeg", "png", "webp"] and "-image" in exclusions: continue
            if ext == "gif" and "-gif" in exclusions: continue

            filename = f"{post.get('id')}.{ext}"
            if filename in dl_history:
                continue

            filepath = os.path.join(tag_dir, filename)
            if os.path.exists(filepath):
                continue

            tags_raw = post.get("tag_string", post.get("tags", ""))
            tags_list = [t.strip() for t in tags_raw.split() if t.strip()]
            artists = [t.strip() for t in post.get("tag_string_artist", "").split() if t.strip()]

            collected.append((file_url, filename, tags_list, artists))
            had_valid = True

        pid += 1
        if had_valid and not stop_event.is_set() and (amount == 0 or len(collected) < amount):
            delay = random.uniform(anti_ban_pause, anti_ban_pause + 2.0)
            log_msg(name, f"Anti-ban pause... ({delay:.1f}s)")
            time.sleep(delay)

    if not collected:
        log_msg(name, "No new images to download.")
        log_msg(name, "--- Worker Terminated ---")
        return

    log_msg(name, f"Collected {len(collected)} new images. Starting download...")

    downloaded = 0
    skipped = 0
    for file_url, filename, tags_list, artists in collected:
        if stop_event.is_set(): break

        filepath = os.path.join(tag_dir, filename)
        if filename in dl_history or os.path.exists(filepath):
            skipped += 1
            continue

        success = False
        for dl_attempt in range(dl_retries):
            try:
                r = session.get(file_url, stream=True, timeout=20)
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
                shared.send_tags(name, filename, tags_list, artists)
                time.sleep(random.uniform(1.0, 2.0))
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
    log_msg(name, "--- Worker Terminated ---")
