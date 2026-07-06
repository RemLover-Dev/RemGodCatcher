import os, time, threading, random
import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session

GIF_ONLY = {"ngif", "hug", "pat", "cuddle", "tickle", "feed", "slap", "kiss", "smug"}
STATIC_ONLY = {"gecg", "meow", "neko", "lewd", "gasm", "8ball", "avatar", "woof", "fox_girl", "waifu"}
MIXED = {"goose", "wallpaper", "lizard", "span"}

def worker_nekos_life(category, amount, net_config, fmt="both"):
    name = "nekos_life"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    if category in GIF_ONLY:
        log_msg(name, f"Initializing worker for category: '{category}' [GIF ONLY]")
    elif category in STATIC_ONLY:
        log_msg(name, f"Initializing worker for category: '{category}' [STATIC ONLY]")
    elif category in MIXED:
        log_msg(name, f"Initializing worker for category: '{category}' [MIXED] [Format: {fmt}]")
    else:
        log_msg(name, f"Initializing worker for category: '{category}' [UNKNOWN TYPE]")

    site_root = os.path.join(shared.MASTER_FOLDER, "Nekos.life")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    gifs_root = os.path.join(site_root, "Gifs")
    images_root = os.path.join(site_root, "Images")
    session = get_session("neko", net_config)
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))

    api_base = "https://nekos.life/api/v2"
    fetch_url = f"{api_base}/img/{category}"

    collected = []

    while not stop_event.is_set() and (amount == 0 or len(collected) < amount):
        try:
            log_msg(name, "Scanning API...")
            resp = session.get(fetch_url, timeout=10)
            if resp.status_code in [403, 429]:
                log_msg(name, f"API BAN ({resp.status_code}). Change VPN node.")
                break
            resp.raise_for_status()
            data = resp.json()
            url = data.get("url")
            if not url:
                log_msg(name, "No URL in response.")
                break
        except Exception as e:
            log_msg(name, f"Network delay, retrying... ({e})")
            time.sleep(5)
            continue

        if stop_event.is_set(): break

        filename = url.split('/')[-1]
        is_gif = filename.lower().endswith(".gif")

        if category in MIXED:
            if fmt == "gif" and not is_gif:
                continue
            elif fmt == "image" and is_gif:
                continue

        type_dir = os.path.join(gifs_root if is_gif else images_root, category)
        os.makedirs(type_dir, exist_ok=True)
        filepath = os.path.join(type_dir, filename)

        if filename in dl_history or os.path.exists(filepath):
            continue

        collected.append((url, filename, is_gif))

        if not stop_event.is_set() and (amount == 0 or len(collected) < amount):
            log_msg(name, f"Anti-ban pause... ({anti_ban_pause:.1f}s)")
            time.sleep(anti_ban_pause)

    if not collected:
        log_msg(name, "No new images to download.")
        log_msg(name, "--- Worker Terminated ---")
        return

    log_msg(name, f"Collected {len(collected)} images. Starting download...")

    downloaded = 0
    for url, filename, is_gif in collected:
        if stop_event.is_set(): break

        type_dir = os.path.join(gifs_root if is_gif else images_root, category)
        os.makedirs(type_dir, exist_ok=True)
        filepath = os.path.join(type_dir, filename)

        success = False
        for dl_attempt in range(dl_retries):
            try:
                r = session.get(url, stream=True, timeout=15)
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
                time.sleep(anti_ban_pause)
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

    log_msg(name, "--- Worker Terminated ---")
