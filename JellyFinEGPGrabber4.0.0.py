#!/usr/bin/python3
# Version 4.0.0 - Added TVDB Lookup Fallback & Episode Caching

import os
import sys
import subprocess
import json
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pwd
import grp

# --- CONFIGURATION ---
USER_NAME = "user"
PASSWORD_HASH = "password" 
TVDB_API_KEY = "YOUR_TVDB_API_KEY" # Get one at thetvdb.com
BASE_URL = "https://json.schedulesdirect.org/20141201"
OUTPUT_DIR = "/mnt/user/appdata/schedulesdirect"
LOGO_DIR = os.path.join(OUTPUT_DIR, "logos")
XML_OUTPUT = os.path.join(OUTPUT_DIR, "guide.xml")
CACHE_FILE = os.path.join(OUTPUT_DIR, "tvdb_cache.json")

# The path Jellyfin sees inside its container
JELLYFIN_LOGOS_PATH = "/xmltv/logos"
USER_AGENT = "JellyfinEPGGrabberV3.8.0/Unraid"
DAYS_TO_FETCH = 7 

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

class TVDBAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.token = self.get_token()
        self.cache = self.load_cache()
        if self.token:
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def get_token(self):
        try:
            r = requests.post("https://api4.thetvdb.com/v4/login", json={"apikey": self.api_key}, timeout=10)
            return r.json().get('data', {}).get('token')
        except: return None

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f: return json.load(f)
        return {}

    def save_cache(self):
        with open(CACHE_FILE, 'w') as f: json.dump(self.cache, f)

    def get_episode_data(self, show_title, ep_title):
        if not self.token or not ep_title: return None
        cache_key = f"{show_title}|{ep_title}".lower()
        if cache_key in self.cache: return self.cache[cache_key]

        try:
            # 1. Search for the series
            search = self.session.get(f"https://api4.thetvdb.com/v4/search?query={show_title}&type=series", timeout=10).json()
            if not search.get('data'): return None
            series_id = search['data'][0]['tvdb_id']

            # 2. Search for the episode name within that series
            ep_search = self.session.get(f"https://api4.thetvdb.com/v4/search?query={ep_title}&seriesId={series_id}&type=episode", timeout=10).json()
            if ep_search.get('data'):
                ep_info = ep_search['data'][0]
                res = {"s": ep_info.get('season_number'), "e": ep_info.get('number')}
                self.cache[cache_key] = res
                return res
        except: pass
        return None

class SchedulesDirectAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.token = self.get_token()
        if self.token:
            self.session.headers.update({'token': self.token})

    def get_token(self):
        payload = {"username": USER_NAME, "password": PASSWORD_HASH}
        r = self.session.post(f"{BASE_URL}/token", json=payload)
        return r.json().get('token')

    def post_request(self, endpoint, data):
        r = self.session.post(f"{BASE_URL}/{endpoint}", json=data)
        return r.json()

def format_date(sd_date):
    clean = sd_date.replace("-", "").replace(":", "").replace("T", "").replace("Z", "")
    return f"{clean[:14]} +0000"

def set_permissions(path):
    try:
        uid, gid = pwd.getpwnam("nobody").pw_uid, grp.getgrnam("users").gr_gid
        os.chown(path, uid, gid)
        os.chmod(path, 0o777)
    except: pass

def generate_xml():
    api = SchedulesDirectAPI()
    tvdb = TVDBAPI(TVDB_API_KEY)
    if not api.token: return

    os.makedirs(LOGO_DIR, exist_ok=True)
    
    lineup_resp = api.session.get(f"{BASE_URL}/lineups").json()
    lineup_id = lineup_resp['lineups'][0]['lineup']
    stations_data = api.session.get(f"{BASE_URL}/lineups/{lineup_id}").json()
    
    root = ET.Element("tv", {"generator-info-name": "Jellyfin-SD-TVDB-Grabber"})

    # Channel processing... (kept same as your script)
    id_map = {}
    station_ids = [s['stationID'] for s in stations_data['stations']]
    for s in stations_data['stations']:
        sid = s['stationID']
        display_number = sid # Simplified for example
        id_map[sid] = display_number
        chan_node = ET.SubElement(root, "channel", id=display_number)
        ET.SubElement(chan_node, "display-name").text = s.get('callsign', sid)

    # Fetch Schedules & Metadata
    today = datetime.date.today()
    dates = [(today + datetime.timedelta(days=x)).isoformat() for x in range(DAYS_TO_FETCH)]
    schedules = api.post_request("schedules", [{"stationID": sid, "date": dates} for sid in station_ids])
    
    unique_prog_ids = {p['programID'] for sched in schedules for p in sched.get('programs', [])}
    meta_cache = {}
    prog_list = list(unique_prog_ids)
    for i in range(0, len(prog_list), 5000):
        m_resp = api.post_request("programs", prog_list[i:i + 5000])
        for m in m_resp: meta_cache[m['programID']] = m

    # Build Programmes
    for sched in schedules:
        xml_chan_id = id_map.get(sched['stationID'])
        for prog in sched.get('programs', []):
            meta = meta_cache.get(prog['programID'], {})
            p_id = prog['programID']
            start_dt = datetime.datetime.strptime(prog['airDateTime'].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            end_dt = start_dt + datetime.timedelta(seconds=prog['duration'])
            
            p_node = ET.SubElement(root, "programme", start=format_date(prog['airDateTime']), stop=format_date(end_dt.isoformat()), channel=xml_chan_id)

            title = meta.get('titles', [{}])[0].get('title120', "To Be Announced")
            subtitle = meta.get('episodeTitle', "")
            ET.SubElement(p_node, "title").text = title
            if subtitle: ET.SubElement(p_node, "sub-title").text = subtitle

            # --- ADVANCED EPISODE LOGIC ---
            s_num, e_num = None, None
            if p_id.startswith("EP"):
                s_num, e_num = int(p_id[2:6]), int(p_id[6:10])
            elif p_id.startswith("SH") and subtitle:
                # Fallback to TVDB lookup
                res = tvdb.get_episode_data(title, subtitle)
                if res: s_num, e_num = res['s'], res['e']

            if s_num and e_num:
                ET.SubElement(p_node, "episode-num", system="xmltv_ns").text = f"{s_num-1}.{e_num-1}.0"
                ET.SubElement(p_node, "episode-num", system="onscreen").text = f"S{s_num:02d}E{e_num:02d}"

            # New/Repeat Flags
            if prog.get('new'): ET.SubElement(p_node, "new")
            else: ET.SubElement(p_node, "previously-shown")

    tvdb.save_cache()
    xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")
    with open(XML_OUTPUT, "w", encoding="utf-8") as f: f.write(xml_str)
    set_permissions(XML_OUTPUT)
    print(f"[INFO] Guide generated with TVDB lookups.")

if __name__ == "__main__":
    generate_xml()
