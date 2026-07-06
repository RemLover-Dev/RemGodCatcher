import os, time, threading, random, re
import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session

def worker_konachan(tag, amount, rating, exclusions, net_config):
    name = "kona"
    if name in STOP_EVENTS and STOP_EVENTS[name] is not None:
        STOP_EVENTS[name].set()

    my_stop_event = threading.Event()
    STOP_EVENTS[name] = my_stop_event
    stop_event = my_stop_event

    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))
    tag = tag.strip().lower()
    original_tag = tag

    if rating:
        tag = (tag + " " + rating).strip()
    log_msg(name, f"Initializing worker for tag: '{tag}'")

    site_root = os.path.join(shared.MASTER_FOLDER, "Konachan")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)
    session = get_session("kona", net_config)

    clean_tag = " ".join(t for t in original_tag.split() if not t.startswith('-'))
    safe_tag = re.sub(r'[\\/*?"<>|]', "", clean_tag)
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)

    rating_map = {"s": "Safe", "q": "Moderate", "e": "Explicit"}

    collected = []
    page = 1

    while not stop_event.is_set() and (amount == 0 or len(collected) < amount):
        try:
            log_msg(name, f"Scanning API... (Page {page})")
            limit_val = min(100, amount - len(collected) if amount > 0 else 100)

            resp = session.get("https://konachan.com/post.json", params={"tags": tag, "page": page, "limit": limit_val}, timeout=15)
            if resp.status_code in [403, 429]:
                log_msg(name, f"ERROR {resp.status_code}. Change proxy.")
                break
            resp.raise_for_status()

            text_resp = resp.text.strip()
            if not text_resp or text_resp == "[]" or text_resp == "null":
                if page == 1: log_msg(name, f"ZERO images found for '{tag}'.")
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

        except Exception as e:
            err_str = str(e)
            if "403" in err_str:
                log_msg(name, "ERROR 403: Cloudflare/ISP block. You need a proxy.")
            else:
                log_msg(name, f"API Error: {e}")
            time.sleep(5)
            continue

        had_valid = False
        for post in posts:
            if stop_event.is_set() or (amount > 0 and len(collected) >= amount):
                break
            if not isinstance(post, dict):
                continue

            post_rating = post.get("rating", "")
            if rating:
                filter_rating = rating.split(":")[-1]
                if post_rating != filter_rating:
                    continue

            url = post.get("file_url") or post.get("large_file_url")
            if not url:
                continue

            ext = (post.get("file_ext") or "").lower()
            if ext in ["mp4", "webm", "zip"] and "-video" in exclusions:
                continue
            if ext in ["jpg", "jpeg", "png", "webp"] and "-image" in exclusions:
                continue
            if ext == "gif" and "-gif" in exclusions:
                continue
            if ext not in ["jpg", "jpeg", "png", "gif", "webp", "mp4", "webm"]:
                continue

            filename = f"{post.get('id')}.{ext}"
            if filename in dl_history:
                continue

            rating_label = rating_map.get(post_rating, "Unknown")
            rating_dir = os.path.join(tag_dir, rating_label)
            filepath = os.path.join(rating_dir, filename)
            if os.path.exists(filepath):
                continue

            tags_raw = post.get("tags", "")
            tags_list = [t.strip() for t in tags_raw.split() if t.strip()]
            artists = []
            for t in tags_list:
                if t.startswith("artist:"):
                    artists.append(t.replace("artist:", "", 1))
            tags_list = [t for t in tags_list if not t.startswith("artist:")]

            collected.append((url, filename, rating_label, tags_list, artists))
            had_valid = True

        page += 1
        if not stop_event.is_set() and (amount == 0 or len(collected) < amount):
            if had_valid:
                log_msg(name, f"Anti-ban pause... ({anti_ban_pause:.1f}s)")
                time.sleep(anti_ban_pause)
            else:
                log_msg(name, f"All posts on page {page-1} filtered or in history. Continuing...")
                time.sleep(1.0)

    if not collected:
        log_msg(name, "No new images to download.")
        log_msg(name, "--- Worker Terminated ---")
        return

    log_msg(name, f"Collected {len(collected)} new images. Starting download...")

    downloaded = 0
    for url, filename, rating_label, tags_list, artists in collected:
        if stop_event.is_set():
            break

        rating_dir = os.path.join(tag_dir, rating_label)
        os.makedirs(rating_dir, exist_ok=True)
        filepath = os.path.join(rating_dir, filename)

        success = False
        for dl_attempt in range(dl_retries):
            try:
                r = session.get(url, stream=True, timeout=60)
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
                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                shared.send_tags(name, filename, tags_list, artists)
                time.sleep(random.uniform(0.5, 2.0))
                success = True
                break
            except Exception as e:
                if stop_event.is_set():
                    break
                if dl_attempt < dl_retries - 1:
                    log_msg(name, f"[RETRY {dl_attempt+1}/{dl_retries}] {filename}: {e}")
                    for _ in range(20):
                        if stop_event.is_set(): break
                        time.sleep(0.1)
                else:
                    log_msg(name, f"[FAILED] {filename}: {e}")

        if stop_event.is_set():
            break

    log_msg(name, "--- Worker Terminated ---")
