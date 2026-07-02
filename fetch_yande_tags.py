import os
import sys
import json
import time
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:10808")
VERIFY_TLS = os.getenv("VERIFY_TLS", "false").lower() == "true"

session = requests.Session()
session.verify = VERIFY_TLS
session.headers.update({"User-Agent": "RemGodCatcher/3.0", "Accept": "application/json"})
if USE_PROXY:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
else:
    session.proxies = {"http": "", "https": "", "no_proxy": "*"}

all_tags = set()
page = 1
empty_count = 0

print("Fetching all tags from yande.re...")
while True:
    try:
        resp = session.get(
            "https://yande.re/tag.json",
            params={"limit": 5000, "page": page},
            timeout=30
        )
        if resp.status_code in [403, 429]:
            print(f"Rate limited/blocked (HTTP {resp.status_code}). Use a proxy or wait.")
            sys.exit(1)
        resp.raise_for_status()

        data = resp.json()
        if not data or len(data) == 0:
            empty_count += 1
            if empty_count >= 3:
                print("No more pages.")
                break
        else:
            empty_count = 0
            for tag in data:
                if isinstance(tag, dict) and "name" in tag:
                    all_tags.add(tag["name"])
            print(f"Page {page}: {len(data)} tags (total unique: {len(all_tags)})")

        page += 1
        time.sleep(0.5)

    except Exception as e:
        print(f"Error on page {page}: {e}")
        time.sleep(5)
        continue

tag_list = sorted(all_tags)
output_path = os.path.join(BASE_DIR, "yande_tag_names.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(tag_list, f, indent=2)

print(f"\nDone! {len(tag_list)} unique tags saved to yande_tag_names.json")
