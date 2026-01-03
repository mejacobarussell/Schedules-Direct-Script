#!/usr/bin/python3

# ==========================================
# Schedules Direct to XMLTV - Version 3.0
# Author: mrjacobarussell
# Optimized for: Unraid, Jellyfin, API 20141201
# ==========================================
#
#
#!/usr/bin/python3
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
USER_NAME = "yourSchedulkesDirectusername"
PASSWORD_HASH = "yourhashed password" ## go here enter your password in plane text,then insert into the "Password Hash Field"  https://www.sha1-online.com
BASE_URL = "https://json.schedulesdirect.org/20141201"
OUTPUT_DIR = "/mnt/user/appdata/schedulesdirect" # change to what you want, i mapped this folder to jellyfin.
XML_OUTPUT = os.path.join(OUTPUT_DIR, "guide.xml") #Use what ever file name you want 
USER_AGENT = "JellyfinEPGGrabberV3.0/Unraid"
DAYS_TO_FETCH = 7 # recomend 2 days for testing and 7 for regular use, can go upto 14 days. 
VERBOSE = True 

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

class SchedulesDirectAPI:
    def __init__(self):
        self.token = self.get_token()
    def get_token(self):
        if VERBOSE: print("[DEBUG] Authenticating...")
        payload = {"username": USER_NAME, "password": PASSWORD_HASH}
        r = requests.post(f"{BASE_URL}/token", json=payload, headers={'User-Agent': USER_AGENT})
        return r.json().get('token')
    def post_request(self, endpoint, data):
        headers = {'token': self.token, 'User-Agent': USER_AGENT}
        r = requests.post(f"{BASE_URL}/{endpoint}", json=data, headers=headers)
        return r.json()

def format_date(sd_date):
    clean = sd_date.replace("-", "").replace(":", "").replace("T", "").replace("Z", "")
    return f"{clean[:14]} +0000"

def set_permissions(path):
    """Applies chown nobody:users and chmod 777 to the file."""
    try:
        uid = pwd.getpwnam("nobody").pw_uid
        gid = grp.getgrnam("users").gr_gid
        os.chown(path, uid, gid)
        os.chmod(path, 0o777)
        if VERBOSE: print(f"[DEBUG] Permissions set: nobody:users 777 for {path}")
    except Exception as e:
        print(f"[ERROR] Could not set permissions: {e}")

def generate_xml():
    api = SchedulesDirectAPI()
    if not api.token: return

    # 1. Get Stations and the specific Lineup Map
    lineup_resp = requests.get(f"{BASE_URL}/lineups", headers={'token': api.token, 'User-Agent': USER_AGENT}).json()
    lineup_id = lineup_resp['lineups'][0]['lineup']
    stations_data = requests.get(f"{BASE_URL}/lineups/{lineup_id}", headers={'token': api.token, 'User-Agent': USER_AGENT}).json()
    stations = stations_data.get('stations', [])
    map_data = stations_data.get('map', [])
    
    root = ET.Element("tv", {"generator-info-name": "Custom-Unraid-Grabber-V3"})

    id_map = {}
    station_ids = []

    # Build a lookup for virtual channel numbers (ATSC Major.Minor)
    channel_lookup = {}
    for entry in map_data:
        sid = entry.get('stationID')
        if 'atscMajor' in entry and 'atscMinor' in entry:
            channel_lookup[sid] = f"{entry['atscMajor']}.{entry['atscMinor']}"
        elif 'channel' in entry:
            channel_lookup[sid] = entry['channel'].replace('_', '.')

    for s in stations:
        sd_id = s['stationID']
        station_ids.append(sd_id)
        
        display_number = channel_lookup.get(sd_id, s.get('channel', sd_id)).replace('_', '.')
        id_map[sd_id] = display_number
        
        if VERBOSE: print(f"[DEBUG] Mapping Station {sd_id} ({s.get('callsign')}) to Virtual Channel {display_number}")
        
        channel_node = ET.SubElement(root, "channel", id=display_number)
        ET.SubElement(channel_node, "display-name").text = display_number
        ET.SubElement(channel_node, "display-name").text = s.get('callsign', sd_id)

    # 2. Fetch Schedule
    today = datetime.date.today()
    dates = [(today + datetime.timedelta(days=x)).isoformat() for x in range(DAYS_TO_FETCH)]
    batch_query = [{"stationID": sid, "date": dates} for sid in station_ids]
    schedules = api.post_request("schedules", batch_query)

    # 3. Fetch Metadata
    unique_prog_ids = {p['programID'] for sched in schedules for p in sched.get('programs', [])}
    meta_cache = {}
    prog_list = list(unique_prog_ids)
    for i in range(0, len(prog_list), 5000):
        chunk = prog_list[i:i + 5000]
        meta_response = api.post_request("programs", chunk)
        if isinstance(meta_response, list):
            for m in meta_response:
                meta_cache[m['programID']] = m

    # 4. Build Programmes
    for sched in schedules:
        current_sid = sched['stationID']
        xml_chan_id = id_map.get(current_sid)
        
        for prog in sched.get('programs', []):
            p_id = prog['programID']
            meta = meta_cache.get(p_id, {})
            start_dt = datetime.datetime.strptime(prog['airDateTime'].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            end_dt = start_dt + datetime.timedelta(seconds=prog['duration'])
            
            p_node = ET.SubElement(root, "programme", 
                                    start=format_date(prog['airDateTime']), 
                                    stop=format_date(end_dt.isoformat()), 
                                    channel=xml_chan_id)

            title = meta.get('titles', [{}])[0].get('title120', "To Be Announced")
            ET.SubElement(p_node, "title").text = title
            
            if not p_id.startswith("MV"):
                ET.SubElement(p_node, "category").text = "Series"
                ET.SubElement(p_node, "category").text = "tvshow"
            if "News" in title:
                ET.SubElement(p_node, "category").text = "News"

            # Episode Logic
            air_dt = datetime.datetime.strptime(prog['airDateTime'][:10], "%Y-%m-%d")
            if p_id.startswith("EP"):
                s_num = int(p_id[2:6])
                e_num = int(p_id[6:10])
                ET.SubElement(p_node, "episode-num", system="xmltv_ns").text = f"{s_num-1}.{e_num-1}.0"
                ET.SubElement(p_node, "episode-num", system="onscreen").text = f"S{s_num:02d}E{e_num:02d}"
            else:
                year = air_dt.year
                month_day = int(air_dt.strftime('%m%d'))
                ET.SubElement(p_node, "episode-num", system="xmltv_ns").text = f"{year-1}.{month_day-1}.0"
                ET.SubElement(p_node, "episode-num", system="onscreen").text = f"S{year}E{air_dt.strftime('%m%d')}"

            if "News" in title or prog.get('new'):
                ET.SubElement(p_node, "new")
            else:
                ET.SubElement(p_node, "previously-shown")

    # 5. Save and Set Permissions
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        set_permissions(OUTPUT_DIR)

    xml_data = ET.tostring(root, encoding='utf-8')
    reparsed = minidom.parseString(xml_data)
    with open(XML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))
    
    set_permissions(XML_OUTPUT)
    if VERBOSE: print(f"[INFO] Done. XML created at {XML_OUTPUT}")

if __name__ == "__main__":
    generate_xml()
