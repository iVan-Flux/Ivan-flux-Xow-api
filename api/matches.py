from flask import Flask, Response
import urllib.request
import json
import base64
import datetime
import binascii
import gzip
from collections import OrderedDict

app = Flask(__name__)

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
        if name.upper() in bare_qualities: link_obj["name"] = f"SPORTIFy {name}"
        elif "CricZ" in name or "cricz" in name: link_obj["name"] = name.replace("CricZ", "SPORTIFy").replace("cricz", "SPORTIFy")
        url_val = link_obj.get("link", "") or link_obj.get("url", "")
        if "otte.live.fly.ww.aiv-cdn.net" in url_val:
            new_url = url_val.replace(".fly.", ".cf.")
            link_obj["link"] = new_url
            link_obj["url"] = new_url
        final_list.append(link_obj)
    return final_list

@app.route('/api/matches')
def get_matches():
    token = get_token()
    url = "https://cricztvnew.cricztv.workers.dev/admin/select"
    payload = json.dumps({"requestData": token, "from": "events"}, separators=(',', ':')).encode('utf-8')
    headers = {"User-Agent": "okhttp/4.9.0", "Content-Type": "application/json", "Accept-Encoding": "gzip"}
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            raw_res = response.read()
            if response.info().get('Content-Encoding') == 'gzip': raw_res = gzip.decompress(raw_res)
            raw_data = json.loads(raw_res.decode('utf-8'))
            events_list = []
            for item in raw_data:
                event_info = json.loads(item.get("event", "{}"))
                processed_streams = process_links(item.get("links", "[]"))
                match_title = event_info.get("eventName") or event_info.get("seriesName") or "Unknown"
                start_dt = f"{format_match_date(event_info.get('date', ''))} {event_info.get('time', '')}"
                end_dt = f"{format_match_date(event_info.get('end_date', ''))} {event_info.get('end_time', '')}"
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
                        ("startTime", f"{start_dt} +0000"),
                        ("endTime", f"{end_dt} +0000")
                    ])),
                    ("Stream links", processed_streams)
                ])
                events_list.append(match_obj)
            update_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).strftime("%I:%M:%S %p %d-%m-%Y")
            final_response = OrderedDict([
                ("AUTHOR", "iVan_FLUx"),
                ("TELEGRAM", "https://t.me/iVan_flux"),
                ("Last update time", update_time),
                ("events", events_list)
            ])
            return Response(json.dumps(final_response, indent=4, ensure_ascii=False), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json')
