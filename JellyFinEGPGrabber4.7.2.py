#!/usr/bin/python3
"""
================================================================================
TITLE: Schedules Direct & TVDB & TV-API Hybrid Grabber
VERSION: 4.7.2
AUTHOR: mrjacobarussell / Gemini Thought Partner
DATE: 2026-01-06
DESCRIPTION: 
    Ultimate EPG Engine with Visual Progress Reporting, Multi-Lineup Support, 
    14-Day Depth, and Show Poster Prioritization.
================================================================================
"""

import os, sys, subprocess, json, datetime, time, logging, re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Start the timer immediately
START_TIME = time.time()

# --- CONFIGURATION ---
USER_NAME = "user"
PASSWORD_HASH = "pass" 
TVDB_API_KEY = "api key"
TVDB_PIN = "user pin" 

# Manual overrides for News/Daily shows
FORCE_NEW_KEYWORDS = ["News", "Today", "Tonight", "Morning", "Evening", "Eyewitness", "Action 4"]

USER_AGENT = "Python-Requests/SD-Grabber-v4"
OUTPUT_DIR = "/mnt/user/appdata/schedulesdirect"
XML_OUTPUT = os.path.join(OUTPUT_DIR, "guide.xml")
CACHE_FILE = os.path.join(OUTPUT_DIR, "hybrid_cache.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "grabber.log")
CHANNELS_LIST_FILE = os.path.join(OUTPUT_DIR, "sd_channels.txt")

DAYS_TO_FETCH = 14 
TIMEOUT = 25 

# --- LOGGING SETUP ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger()

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

class MetadataEngine:
    def __init__(self, session):
        self.session = session
        self.tvdb_token = self.get_tvdb_token()
        self.cache = self.load_cache()

    def get_tvdb_token(self):
        try:
            payload = {"apikey": TVDB_API_KEY, "pin": TVDB_PIN}
            r = self.session.post("https://api4.thetvdb.com/v4/login", json=payload, timeout=TIMEOUT)
            return r.json().get('data', {}).get('token')
        except: return None

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try: return json.load(open(CACHE_FILE, 'r'))
            except: return {}
        return {}

    def save_cache(self):
        with open(CACHE_FILE, 'w') as f: json.dump(self.cache, f, indent=2)

    def get_episode_info(self, title, subtitle, air_date, sd_prog_id, sd_img=None):
        cache_key = f"{title}|{subtitle}|{air_date}".lower()
        if cache_key in self.cache: return self.cache[cache_key]
        
        res = {"s": None, "e": None, "img": sd_img, "source": None}
        headers = {'Authorization': f'Bearer {self.tvdb_token}'} if self.tvdb_token else {}

        if self.tvdb_token:
            try:
                # Prioritize SERIES Search for Show Posters
                s_res = self.session.get(f"https://api4.thetvdb.com/v4/search?query={title}&type=series", headers=headers, timeout=TIMEOUT).json()
                if s_res.get('data'):
                    series_data = s_res['data'][0]
                    sid = series_data['tvdb_id']
                    res['img'] = series_data.get('image_url') or res['img']
                    
                    ep_res = self.session.get(f"https://api4.thetvdb.com/v4/series/{sid}/episodes/default?airDate={air_date}", headers=headers, timeout=TIMEOUT).json()
                    if ep_res.get('data') and ep_res['data'].get('episodes'):
                        ep = ep_res['data']['episodes'][0]
                        res.update({"s": ep.get('seasonNumber'), "e": ep.get('number'), "source": "TVDB"})
            except: pass

        if not res['s'] and sd_prog_id.startswith("EP"):
            res.update({"s": int(sd_prog_id[2:6]), "e": int(sd_prog_id[6:10]), "source": "SchedulesDirect"})

        if res['s'] or res['img']: self.cache[cache_key] = res
        return res

def format_date(sd_date):
    return sd_date.replace("-", "").replace(":", "").replace("T", "").replace("Z", "") + " +0000"

def load_clean_whitelist():
    clean_list = []
    if os.path.exists(CHANNELS_LIST_FILE):
        with open(CHANNELS_LIST_FILE, 'r') as f:
            for line in f:
                match = re.search(r'(\d+\.?\d*)', line.strip())
                if match: clean_list.append(match.group(1))
    return clean_list

def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def generate_xml():
    api_session = requests.Session()
    api_session.headers.update({'User-Agent': USER_AGENT})
    engine = MetadataEngine(api_session)
    raw_whitelist = load_clean_whitelist()
    
    # 1. SD LOGIN
    logger.info("Connecting to Schedules Direct...")
    r = api_session.post("https://json.schedulesdirect.org/20141201/token", json={"username": USER_NAME, "password": PASSWORD_HASH})
    token = r.json().get('token')
    if not token: 
        logger.error("SD Login Failed")
        return
    api_session.headers.update({'token': token})

    # 2. LINEUP DISCOVERY
    lineup_resp = api_session.get("https://json.schedulesdirect.org/20141201/lineups").json()
    all_lineups = lineup_resp.get('lineups', [])
    
    station_to_chan = {}
    master_stations = []

    for lineup in all_lineups:
        l_id = lineup['lineup']
        l_data = api_session.get(f"https://json.schedulesdirect.org/20141201/lineups/{l_id}").json()
        master_stations.extend(l_data.get('stations', []))
        for entry in l_data.get('map', []):
            sid = str(entry.get('stationID'))
            chan_num = f"{entry.get('atscMajor', '')}.{entry.get('atscMinor', '')}" if 'atscMajor' in entry else entry.get('channel', sid).replace('_', '.')
            if not raw_whitelist or (sid in raw_whitelist or chan_num in raw_whitelist):
                station_to_chan[sid] = chan_num

    root = ET.Element("tv", {"generator-info-name": "SD-Hybrid-v4.7.2"})
    
    # 3. CHANNEL MAPPING
    seen_sid = set()
    for s in master_stations:
        sid = s['stationID']
        if sid in station_to_chan and sid not in seen_sid:
            c_node = ET.SubElement(root, "channel", id=station_to_chan[sid])
            ET.SubElement(c_node, "display-name").text = station_to_chan[sid]
            ET.SubElement(c_node, "display-name").text = s.get('callsign')
            logo = s.get('stationLogo', [{}])[0].get('URL')
            if logo: ET.SubElement(c_node, "icon", src=logo)
            seen_sid.add(sid)

    # 4. FETCH SCHEDULES
    logger.info(f"Downloading {DAYS_TO_FETCH} days of schedule data...")
    today = datetime.date.today()
    dates = [(today + datetime.timedelta(days=x)).isoformat() for x in range(DAYS_TO_FETCH)]
    final_sids = list(station_to_chan.keys())
    all_schedules = []
    for i in range(0, len(final_sids), 25):
        chunk = final_sids[i:i+25]
        batch_res = api_session.post("https://json.schedulesdirect.org/20141201/schedules", json=[{"stationID": s, "date": dates} for s in chunk]).json()
        if isinstance(batch_res, list): all_schedules.extend(batch_res)

    # 5. FETCH METADATA BATCHES
    unique_ids = {p['programID'] for s in all_schedules for p in s.get('programs', []) if isinstance(s, dict)}
    meta_cache = {}
    prog_list = list(unique_ids)
    logger.info(f"Downloading metadata for {len(prog_list)} unique programs...")
    for i in range(0, len(prog_list), 5000):
        m_resp = api_session.post("https://json.schedulesdirect.org/20141201/programs", json=prog_list[i:i+5000]).json()
        if isinstance(m_resp, list):
            for m in m_resp: meta_cache[m['programID']] = m

    # 6. BUILD PROGRAMMES WITH PROGRESS INDICATOR
    count = 0
    total_to_process = sum(len(s.get('programs', [])) for s in all_schedules if isinstance(s, dict))
    logger.info(f"Building XML for {total_to_process} airings...")

    for sched in all_schedules:
        chan_id = station_to_chan.get(sched['stationID'])
        for prog in sched.get('programs', []):
            meta = meta_cache.get(prog['programID'], {})
            title = meta.get('titles', [{}])[0].get('title120', "TBA")
            subtitle = meta.get('episodeTitle', "")
            
            p_node = ET.SubElement(root, "programme", 
                                   start=format_date(prog['airDateTime']), 
                                   stop=format_date((datetime.datetime.strptime(prog['airDateTime'][:19], "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(seconds=prog['duration'])).isoformat()), 
                                   channel=chan_id)
            
            ET.SubElement(p_node, "title").text = title
            if subtitle: ET.SubElement(p_node, "sub-title").text = subtitle

            sd_img = meta.get('metadata', [{}])[0].get('logo', {}).get('URL') if meta.get('metadata') else None
            info = engine.get_episode_info(title, subtitle, meta.get('originalAirDate', prog['airDateTime'][:10]), prog['programID'], sd_img)

            prefix = f"[S{info['s']:02d}E{info['e']:02d}] " if info['s'] else ""
            raw_desc = meta.get('descriptions', {}).get('description1000', [{}])[0].get('description', "")
            ET.SubElement(p_node, "desc").text = f"{prefix}{raw_desc}"

            # Technical Tags & Categories
            for g in meta.get('genres', []): ET.SubElement(p_node, "category").text = g
            if 'HD' in (prog.get('videoProperties', []) or []):
                v_node = ET.SubElement(p_node, "video")
                ET.SubElement(v_node, "quality").text = "HDTV"
            
            # New/Premiere logic
            if prog.get('new') or any(word.lower() in title.lower() for word in FORCE_NEW_KEYWORDS):
                ET.SubElement(p_node, "new")

            # Numbering Tags
            if info['s'] and info['e']:
                ET.SubElement(p_node, "episode-num", system="onscreen").text = f"S{info['s']:02d}E{info['e']:02d}"
                ET.SubElement(p_node, "episode-num", system="xmltv_ns").text = f"{info['s']-1}.{info['e']-1}."

            if info['img']: ET.SubElement(p_node, "icon", src=info['img'])
            
            count += 1
            # PROGRESS INDICATOR: Print status every 100 entries
            if count % 100 == 0:
                print(f" > Processing Progress: {count} / {total_to_process} programmes built.", end="\r")

    # Final Save
    print() # New line after progress indicator
    engine.save_cache()
    logger.info("Saving guide.xml to Unraid appdata...")
    with open(XML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(prettify(root))
    
    logger.info(f"SUCCESS: {count} programs. Total Time: {time.time() - START_TIME:.2f}s")

if __name__ == "__main__":
    generate_xml()
