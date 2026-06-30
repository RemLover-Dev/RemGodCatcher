import os
import time
import threading
import random

from shared import log_msg, STOP_EVENTS, MASTER_FOLDER, load_history, save_history, get_session

def worker_nekos_best(category, amount, net_config):
    name = "neko"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    log_msg(name, f"Initializing worker for category: '{category}'")

    site_root = os.path.join(MASTER_FOLDER, "Nekos.best")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    cat_dir = os.path.join(site_root, category)
    os.makedirs(cat_dir, exist_ok=True)
    session = get_session("neko", net_config)
    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))

    downloaded = 0
    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        fetch_url = f"https://nekos.best/api/v2/{category}?amount={min(20, amount - downloaded if amount > 0 else 20)}"
        
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

        page_downloaded = 0
        for item in results:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
            url = item.get("url")
            if not url: continue

            filename = url.split('/')[-1]
            filepath = os.path.join(cat_dir, filename)

            if filename in dl_history or os.path.exists(filepath): continue

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
                page_downloaded += 1
                dl_history.add(filename)
                save_history(site_root, dl_history)

                log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                time.sleep(random.uniform(0.3, 1.2))
            except Exception as e:
                log_msg(name, f"[FAILED] {filename}: {e}")

        if page_downloaded > 0 and not stop_event.is_set() and (amount == 0 or downloaded < amount):
            log_msg(name, f"Anti-ban pause... ({anti_ban_pause:.1f}s)")
            time.sleep(anti_ban_pause)

    log_msg(name, "--- Worker Terminated ---")