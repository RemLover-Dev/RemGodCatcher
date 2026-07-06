import os, time, threading, random
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session
import shared

def worker_nekos_best(category, amount, net_config):
    name = "neko"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))
    log_msg(name, f"Initializing worker for category: '{category}'")

    site_root = os.path.join(shared.MASTER_FOLDER, "Nekos.best")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    cat_dir = os.path.join(site_root, category)
    os.makedirs(cat_dir, exist_ok=True)
    session = get_session("neko", net_config)

    collected = []

    while not stop_event.is_set() and (amount == 0 or len(collected) < amount):
        batch_size = min(20, amount - len(collected) if amount > 0 else 20)
        fetch_url = f"https://nekos.best/api/v2/{category}?amount={batch_size}"

        try:
            log_msg(name, "Scanning API...")
            resp = session.get(fetch_url, timeout=10)
            if resp.status_code in [403, 429]:
                log_msg(name, f"API BAN ({resp.status_code}). Change VPN node.")
                break
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                log_msg(name, "End of database reached.")
                break
        except Exception as e:
            log_msg(name, f"Network delay, retrying... ({e})")
            time.sleep(5)
            continue

        for item in results:
            if stop_event.is_set() or (amount > 0 and len(collected) >= amount): break
            url = item.get("url")
            if not url: continue

            filename = url.split('/')[-1]
            if filename in dl_history:
                continue

            filepath = os.path.join(cat_dir, filename)
            if os.path.exists(filepath):
                continue

            collected.append(url)

        if stop_event.is_set() or (amount > 0 and len(collected) >= amount):
            break
        delay = random.uniform(anti_ban_pause, anti_ban_pause + 3.0)
        log_msg(name, f"Anti-ban pause... ({delay:.1f}s)")
        time.sleep(delay)

    if not collected:
        log_msg(name, "No new images to download.")
        log_msg(name, "--- Worker Terminated ---")
        return

    log_msg(name, f"Collected {len(collected)} images. Starting download...")

    downloaded = 0
    for url in collected:
        if stop_event.is_set(): break

        filename = url.split('/')[-1]
        filepath = os.path.join(cat_dir, filename)

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
                time.sleep(random.uniform(0.3, 1.2))
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
