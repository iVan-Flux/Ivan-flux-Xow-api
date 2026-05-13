import requests
import json
import base64
import os
import gzip
import datetime
import binascii
from collections import OrderedDict
from Crypto.Cipher import AES

# 🔐 Load Secrets from GitHub
AES_SECRET = os.getenv("AES_SECRET")
TARGET_URL = os.getenv("LIVXOW_URL")

def get_token():
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        encoded_bytes = base64.b64encode(current_time.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        reversed_b64 = encoded_str[::-1]
        hex_str = binascii.hexlify(reversed_b64.encode('utf-8')).decode('utf-8')
        return hex_str[::-1]
    except: return None

def format_match_date(date_str):
    try:
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3: return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except: pass
    return date_str

def process_links(links_input):
    final_list = []
    if isinstance(links_input, str):
        try: links_input = json.loads(links_input)
        except: return []
    if not isinstance(links_input, list): return []

    for link_obj in links_input:
        name = link_obj.get("name", "").strip()
        bare_qualities = ["AQ", "LQ", "SD", "HD", "FHD", "4K", "AD", "LOW", "MED", "HIGH"]
        if name.upper() in bare_qualities:
            link_obj["name"] = f"SPORTIFy {name}"
        elif "CricZ" in name or "cricz" in name:
            link_obj["name"] = name.replace("CricZ", "SPORTIFy").replace("cricz", "SPORTIFy")
        
        url_val = link_obj.get("link", "") or link_obj.get("url", "")
        if "otte.live.fly.ww.aiv-cdn.net" in url_val:
            new_url = url_val.replace(".fly.", ".cf.")
            link_obj["link"] = new_url
            link_obj["url"] = new_url
        final_list.append(link_obj)
    return final_list

def encrypt_json(data_dict):
    key = AES_SECRET.encode()[:32]
    cipher = AES.new(key, AES.MODE_EAX)
    json_text = json.dumps(data_dict, ensure_ascii=False)
    ciphertext, tag = cipher.encrypt_and_digest(json_text.encode('utf-8'))
    # Nonce + Tag + Ciphertext মিলিয়ে এনক্রিপ্ট ডেটা তৈরি
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def run():
    if not AES_SECRET or not TARGET_URL:
        print("Missing Secrets!")
        return

    token = get_token()
    payload = json.dumps({"requestData": token, "from": "events"}, separators=(',', ':')).encode('utf-8')
    headers = {"User-Agent": "okhttp/4.9.0", "Content-Type": "application/json", "Accept-Encoding": "gzip"}

    try:
        r = requests.post(TARGET_URL, data=payload, headers=headers, timeout=20)
        raw_res = r.content
        if r.headers.get('Content-Encoding') == 'gzip':
            raw_res = gzip.decompress(raw_res)
        
        raw_data = json.loads(raw_res.decode('utf-8'))
        events_list = []

        for item in raw_data:
            event_info = json.loads(item.get("event", "{}"))
            processed_streams = process_links(item.get("links", "[]"))
            match_title = event_info.get("eventName") or event_info.get("seriesName") or "Unknown"

            match_obj = OrderedDict([
                ("id", str(item.get("id", ""))),
                ("title", match_title),
                ("Title image", event_info.get("eventLogo", "")),
                ("cat", event_info.get("category", "Sports")),
                ("eventInfo", OrderedDict([
                    ("teamA", event_info.get("teamAName", "Team A")),
                    ("teamB", event_info.get("teamBName", "Team B")),
                    ("teamAFlag", event_info.get("teamAFlag", "")),
                    ("teamBFlag", event_info.get("teamBFlag", "")),
                    ("isHot", "0"),
                    ("startTime", f"{format_match_date(event_info.get('date', ''))} {event_info.get('time', '')} +0000"),
                    ("endTime", f"{format_match_date(event_info.get('end_date', ''))} {event_info.get('end_time', '')} +0000")
                ])),
                ("Stream links", processed_streams)
            ])
            events_list.append(match_obj)

        update_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).strftime("%I:%M:%S %p %d-%m-%Y")
        
        final_wrapped = OrderedDict([
            ("AUTHOR", "iVan_FLUx"),
            ("TELEGRAM", "https://t.me/iVan_flux"),
            ("Last update time", update_time),
            ("events", events_list)
        ])

        # এনক্রিপ্ট করে ফাইলে সেভ করা
        encrypted_result = {"data": encrypt_json(final_wrapped)}
        with open("Sportzx.json", "w", encoding="utf-8") as f:
            json.dump(encrypted_result, f, indent=4)
        print("Sportzx.json generated and encrypted!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
