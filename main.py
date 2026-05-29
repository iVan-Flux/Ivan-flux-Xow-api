import requests
import json
import base64
import os
import datetime
import binascii
from collections import OrderedDict
from Crypto.Cipher import AES

# 🔐 GitHub Secrets
AES_SECRET = os.getenv("AES_SECRET")
TARGET_URL = os.getenv("LIVXOW_URL")

def get_token():
    """Generates the security token based on current UTC time."""
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        encoded_bytes = base64.b64encode(current_time.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        reversed_b64 = encoded_str[::-1]
        hex_str = binascii.hexlify(reversed_b64.encode('utf-8')).decode('utf-8')
        return hex_str[::-1]
    except: return None

def format_match_date(date_str):
    """Converts date format from DD/MM/YYYY to YYYY/MM/DD."""
    try:
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3: return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except: pass
    return date_str

def process_links(links_input):
    """Processes branding rules, domain fixes, and specific link replacements."""
    final_list = []
    if isinstance(links_input, str):
        try: links_input = json.loads(links_input)
        except: return []
    if not isinstance(links_input, list): return []

    for link_obj in links_input:
        name = link_obj.get("name", "").strip()
        link_val = link_obj.get("link", "") or link_obj.get("url", "")

        # Logic 3: Replace 'Link 1' with specific fallback stream
        if name == "Link 1" and "file.genoads.com/ch1.m3u8" in link_val:
            link_obj["name"] = "Ivan-FluX"
            link_obj["link"] = "https://fallback-video.ivan-flux.workers.dev/video/index.m3u8"
            link_obj["url"] = "https://fallback-video.ivan-flux.workers.dev/video/index.m3u8"
        else:
            # Original 'SPORTIFy' Branding logic
            bare_qualities = ["AQ", "LQ", "SD", "HD", "FHD", "4K", "AD", "LOW", "MED", "HIGH"]
            if name.upper() in bare_qualities:
                link_obj["name"] = f"SPORTIFy {name}"
            elif "CricZ" in name or "cricz" in name:
                link_obj["name"] = name.replace("CricZ", "SPORTIFy").replace("cricz", "SPORTIFy")
            
            # Original Domain Fix logic (.fly. -> .cf.)
            if "otte.live.fly.ww.aiv-cdn.net" in link_val:
                new_url = link_val.replace(".fly.", ".cf.")
                link_obj["link"] = new_url
                link_obj["url"] = new_url

        final_list.append(link_obj)
    return final_list

def encrypt_json(data_dict):
    """Encrypts the JSON data using AES-EAX mode."""
    key = AES_SECRET.strip().encode()[:32]
    cipher = AES.new(key, AES.MODE_EAX)
    json_text = json.dumps(data_dict, ensure_ascii=False)
    ciphertext, tag = cipher.encrypt_and_digest(json_text.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def run():
    if not AES_SECRET or not TARGET_URL:
        print("Error: Secrets missing!")
        exit(1)

    token = get_token()
    payload = json.dumps({"requestData": token, "from": "events"}, separators=(',', ':'))
    headers = {"User-Agent": "okhttp/4.9.0", "Content-Type": "application/json"}

    try:
        r = requests.post(TARGET_URL, data=payload, headers=headers, timeout=30)
        r.raise_for_status()
        raw_data = r.json()
        
        # Determine Current Time in IST
        now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
        
        events_list = []
        live_count = 0
        upcoming_count = 0
        finish_count = 0

        for item in raw_data:
            event_info = json.loads(item.get("event", "{}"))
            processed_channels = process_links(item.get("links", "[]"))
            match_title = event_info.get("eventName") or event_info.get("seriesName") or "Unknown"

            # Parse Start and End times for Status logic
            start_str = f"{format_match_date(event_info.get('date', ''))} {event_info.get('time', '')}"
            end_str = f"{format_match_date(event_info.get('end_date', ''))} {event_info.get('end_time', '')}"
            
            status = "Upcoming"
            try:
                start_dt = datetime.datetime.strptime(start_str, "%Y/%m/%d %H:%M:%S")
                end_dt = datetime.datetime.strptime(end_str, "%Y/%m/%d %H:%M:%S")
                
                if now_ist < start_dt:
                    status = "Upcoming"
                    upcoming_count += 1
                elif start_dt <= now_ist <= end_dt:
                    status = "Live"
                    live_count += 1
                else:
                    status = "Finish"
                    finish_count += 1
            except:
                upcoming_count += 1 # Default to Upcoming if time parse fails

            # Building the Match Object with the new Hierarchy
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
                    ("Status", status), # Added Status key under isHot
                    ("startTime", f"{start_str} +0000"),
                    ("endTime", f"{end_str} +0000")
                ])),
                ("channels_data", processed_channels) # Renamed from Stream links
            ])
            events_list.append(match_obj)

        # Logic for Shortlisting (Sorting): Live > Upcoming > Finish
        status_priority = {"Live": 1, "Upcoming": 2, "Finish": 3}
        events_list.sort(key=lambda x: status_priority.get(x["eventInfo"]["Status"], 4))

        # Top Header Setup
        update_time_str = now_ist.strftime("%I:%M:%S %p %d-%m-%Y")
        
        final_wrapped = OrderedDict([
            (" NAME ", "FluX-oW Live event ( Auto updated)"),
            ("AUTHOR", "iVan_FluX"),
            ("CONTACT (OWNER)", "https://t.me/iVan_flux"),
            ("TELEGRAM CHANNEL", "https://t.me/api_hub_by_ivan"),
            ("Last update time", update_time_str),
            ("Live", str(live_count).zfill(2)),
            ("Upcoming", str(upcoming_count).zfill(2)),
            ("Finish", str(finish_count).zfill(2)),
            ("events", events_list)
        ])

        # Encrypt and Save to File
        encrypted_data = encrypt_json(final_wrapped)
        with open("Ivan-FluX.json", "w", encoding="utf-8") as f:
            json.dump({"data": encrypted_data}, f, indent=4)
        
        print(f"Done: Ivan-FluX.json generated. Live: {live_count}, Upcoming: {upcoming_count}, Finish: {finish_count}")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    run()
