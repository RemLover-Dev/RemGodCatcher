import os, time, threading, random, re, urllib.parse
import shared
from shared import log_msg, STOP_EVENTS, load_history, save_history, get_session

def _derive_img_url(item):
    keys = ["full", "large", "file_url", "source", "src", "url", "image"]
    for k in keys:
        v = item.get(k)
        if v:
            return v
    thumb = item.get("thumb", "")
    if thumb:
        no_thumb = thumb.replace(".thumb.", ".")
        if no_thumb != thumb:
            return no_thumb
    return None

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
    session = get_session("zero", net_config)

    clean_tag = " ".join(t for t in tag.split() if not t.startswith('-'))
    safe_tag = re.sub(r'[\\/*?"<>|]', "", clean_tag)
    tag_dir = os.path.join(site_root, safe_tag)
    os.makedirs(tag_dir, exist_ok=True)
    encoded_tag = urllib.parse.quote_plus(tag)

    collected_ids = []
    page = 1
    downloaded = 0
    api_exhausted = False
    first_page = True

    while not stop_event.is_set() and (amount == 0 or downloaded < amount) and not api_exhausted:
        if not collected_ids:
            try:
                log_msg(name, f"Scanning API... (Page {page})")
                resp = session.get(f"https://www.zerochan.net/{encoded_tag}?json", params={"p": page, "l": 48}, timeout=15)
                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    log_msg(name, "End of database reached.")
                    api_exhausted = True
                    break
                for item in items:
                    post_id = item.get("id")
                    if post_id:
                        collected_ids.append(post_id)
                page += 1
                if not first_page:
                    delay = random.uniform(anti_ban_pause, anti_ban_pause + 3.0)
                    log_msg(name, f"Anti-ban pause... ({delay:.1f}s)")
                    time.sleep(delay)
                first_page = False
            except Exception as e:
                log_msg(name, f"Network/Limit: {e}")
                break

        if not collected_ids:
            continue

        post_id = collected_ids.pop(0)

        try:
            det_resp = session.get(f"https://www.zerochan.net/{post_id}?json", timeout=10)
            json_data = det_resp.json()
        except Exception as e:
            log_msg(name, f"Failed to get details for post {post_id}: {e}")
            continue

        img_url = _derive_img_url(json_data)
        if not img_url:
            log_msg(name, f"No image URL found for post {post_id} (keys: {list(json_data.keys())}), skipping.")
            continue

        tags_raw = json_data.get("tags", [])
        if isinstance(tags_raw, str):
            tags_list = [t.strip() for t in tags_raw.replace(",", " ").split() if t.strip()]
        else:
            tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]

        filename = urllib.parse.unquote(img_url.split('/')[-1])
        filepath = os.path.join(tag_dir, filename)

        if filename in dl_history or os.path.exists(filepath):
            log_msg(name, f"Skipping {filename} (already downloaded), searching for more...")
            continue

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

    log_msg(name, "--- Worker Terminated ---")
