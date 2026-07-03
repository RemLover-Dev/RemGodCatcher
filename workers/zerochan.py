import os
import time
import threading
import random
import re
import urllib.parse

import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session

def worker_zerochan(tag, amount, net_config):
    name = "zero"
    STOP_EVENTS[name] = threading.Event()
    stop_event = STOP_EVENTS[name]

    anti_ban_pause = float(net_config.get("anti_ban_pause", 3.0))
    dl_retries = int(net_config.get("download_retries", 3))
    tag = tag.strip().lower()
    log_msg(name, f"Initializing worker for tag: '{tag}'")

    site_root = os.path.join(shared.MASTER_FOLDER, "Zerochan")
    os.makedirs(site_root, exist_ok=True)
    dl_history = load_history(site_root)

    try:
        r_resp = session.get(f"https://www.zerochan.net/{urllib.parse.quote_plus(tag)}", timeout=10, allow_redirects=True)
        if r_resp.url and "/search?q=" not in r_resp.url:
            parsed_path = urllib.parse.urlparse(r_resp.url).path
            real_tag = urllib.parse.unquote(parsed_path.split('/')[-1]).replace('+', ' ')
            if real_tag and real_tag.lower() != tag.lower():
                tag = real_tag
    except Exception:
        pass

    clean_tag = " ".join(t for t in tag.split() if not t.startswith('-'))
    safe_tag = re.sub(r'[\\/*?:"<>|]', "", clean_tag).replace(' ', '_')
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

        for item in items:
            if stop_event.is_set() or (amount > 0 and downloaded >= amount): break
            try:
                det_resp = session.get(f"https://www.zerochan.net/{item.get('id')}?json", timeout=10)
                json_data = det_resp.json()
                img_url = json_data.get("full") or json_data.get("large")
                
                # --- استخراج تگهای عکس ---
                tags_raw = json_data.get("tags", [])
                if isinstance(tags_raw, str): tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
                else: tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]
            except Exception: continue
            
            if not img_url: continue

            filename = img_url.split('/')[-1]
            filepath = os.path.join(tag_dir, filename)

            if filename in dl_history or os.path.exists(filepath): continue

            success = False
            for dl_attempt in range(dl_retries):
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
                    tags_raw = det_resp.json().get("tags", []) if 'det_resp' in locals() else []
                    if isinstance(tags_raw, str): tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
                    else: tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]

                    dl_history.add(filename)
                    save_history(site_root, dl_history)

                    log_msg(name, f"[SUCCESS] Downloaded {filename} ({downloaded}/{amount})")
                    shared.send_tags(name, filename, tags_list, [])
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

        page += 1
        if not stop_event.is_set() and (amount == 0 or downloaded < amount):
            delay = random.uniform(anti_ban_pause, anti_ban_pause + 3.0)
            log_msg(name, f"Anti-ban pause... ({delay:.1f}s)")
            time.sleep(delay)

    log_msg(name, "--- Worker Terminated ---")