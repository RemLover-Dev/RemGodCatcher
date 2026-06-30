import os
import time
import threading
import random
import re
import urllib.parse

from shared import log_msg, STOP_EVENTS, MASTER_FOLDER, load_history, save_history, get_session

def worker_zerochan(tag, amount, net_config):
    name = "zero"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    tag = tag.split('|')[0].strip()
    log_msg(name, f"Initializing worker for tag: '{tag}'")
    session = get_session("zero", net_config)

    site_root = os.path.join(MASTER_FOLDER, "Zerochan")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    try:
        r_resp = session.get(f"https://www.zerochan.net/{urllib.parse.quote_plus(tag)}", timeout=10, allow_redirects=True)
        if r_resp.url and "/search?q=" not in r_resp.url:
            real_tag = urllib.parse.unquote(r_resp.url.split('/')[-1]).replace('+', ' ')
            if real_tag and real_tag.lower() != tag.lower():
                tag = real_tag
    except Exception:
        pass

    safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).replace(' ', '_')
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)
    encoded_tag = urllib.parse.quote_plus(tag)

    downloaded = 0
    page = 1
    
    while not stop_event.is_set() and (amount == 0 or downloaded < amount):
        try:
            log_msg(name, f"Scanning API... (Page {page})")
            resp = session.get(f"https://www.zerochan.net/{encoded_tag}?json", params={"p": page, "l": 48}, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                log_msg(name, "End of database reached.")
                break
        except Exception as e:
            log_msg(name, f"Network/Limit: {e}")
            break

        page_downloaded = 0
        for item in items:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
            try:
                det_resp = session.get(f"https://www.zerochan.net/{item.get('id')}?json", timeout=10)
                img_url = det_resp.json().get("full") or det_resp.json().get("large")
            except Exception: continue
            
            if not img_url: continue

            filename = img_url.split('/')[-1]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath): continue

            try:
                r = session.get(img_url, stream=True, timeout=20)
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
                log_msg(name, f"[FAILED] {filename}")

        page += 1
        if page_downloaded > 0 and not stop_event.is_set() and (amount == 0 or downloaded < amount):
            delay = random.uniform(3.0, 6.0)
            log_msg(name, f"Stealth delay... ({delay:.1f}s)")
            time.sleep(delay)

    log_msg(name, "--- Worker Terminated ---")