#!/usr/bin/python3

import requests
import hashlib
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# --- Configuration ---
USER_NAME = 'yourusername'
PASSWORD = 'yourpassword' 
BASE_URL = 'https://json.schedulesdirect.org/20141201'
OUTPUT_DIR = "/mnt/user/appdata/schedulesdirect"
OUTPUT_FILE = f"{OUTPUT_DIR}/guide.xml"

def lprint(text):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}", flush=True)

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_token():
    password_hash = hashlib.sha1(PASSWORD.encode('utf-8')).hexdigest()
    try:
        res = requests.post(f"{BASE_URL}/token", json={"username": USER_NAME, "password": password_hash})
        res.raise_for_status()
        return res.json().get('token')
    except Exception as e:
        lprint(f"Auth failed: {e}")
        return None

def format_xmltv_date(date_str):
    clean = date_str.replace("-","").replace(":","").replace("T","").replace("Z","").split(".")[0]
    return f"{clean} +0000"

def main():
    lprint("--- Starting Multi-Lineup EPG Download ---")
    token = get_token()
    if not token: return
    headers = {'token': token}

    # 1. Fetch account lineups
    lineups_res = requests.get(f"{BASE_URL}/lineups", headers=headers)
    lineups_data = lineups_res.json()
    
    if 'lineups' not in lineups_data or not lineups_data['lineups']:
        lprint("No lineups found! Ensure you have added lineups to your SD account on their website.")
        return

    # 2. Collect ALL stations across ALL 3 lineups
    master_stations_map = {}
    for entry in lineups_data['lineups']:
        l_id = entry['lineup']
        lprint(f"Fetching station list for lineup: {l_id}")
        
        m_res = requests.get(f"{BASE_URL}/lineups/{l_id}", headers=headers)
        if m_res.status_code == 200:
            m_data = m_res.json()
            for s in m_data.get('stations', []):
                # Use stationID as key to prevent duplicates if a station is in multiple lineups
                master_stations_map[s['stationID']] = s

    stations = list(master_stations_map.values())
    lprint(f"Total unique stations found across all lineups: {len(stations)}")

    # 3. Get Schedules for every station identified
    station_ids = list(master_stations_map.keys())
    schedules_raw = []
    
    # SD allows requesting up to 500 stations at once for schedules
    for i in range(0, len(station_ids), 500):
        batch_ids = [{"stationID": sid} for sid in station_ids[i:i+500]]
        lprint(f"Requesting schedules for batch {i//500 + 1}...")
        sched_res = requests.post(f"{BASE_URL}/schedules", headers=headers, json=batch_ids)
        if sched_res.status_code == 200:
            schedules_raw.extend(sched_res.json())

    # 4. Fetch Metadata (Program details)
    all_prog_ids = list(set(p['programID'] for s in schedules_raw for p in s.get('programs', [])))
    programs_data = {}
    lprint(f"Fetching metadata for {len(all_prog_ids)} unique programs...")
    
    for i in range(0, len(all_prog_ids), 5000):
        batch = all_prog_ids[i:i+5000]
        prog_res = requests.post(f"{BASE_URL}/programs", headers=headers, json=batch)
        if prog_res.status_code == 200:
            for p in prog_res.json():
                programs_data[p['programID']] = p

    # 5. Build XMLTV
    root = ET.Element("tv", {"generator-info-name": "Jellyfin-MultiLineup-Script"})
    
    for s_id, s_info in master_stations_map.items():
        callsign = s_info.get('callsign', 'Unknown')
        ch = ET.SubElement(root, "channel", id=s_id)
        ET.SubElement(ch, "display-name").text = callsign
        ET.SubElement(ch, "display-name").text = f"{callsign} (SD:{s_id})"
        if 'logo' in s_info: 
            ET.SubElement(ch, "icon", src=s_info['logo']['URL'])

    for s_map in schedules_raw:
        xml_id = s_map['stationID']
        for p in s_map.get('programs', []):
            details = programs_data.get(p['programID'], {})
            
            start_dt = datetime.strptime(p['airDateTime'].replace("Z","").split(".")[0], "%Y-%m-%dT%H:%M:%S")
            stop_dt = start_dt + timedelta(seconds=p.get('duration', 0))
            
            prog = ET.SubElement(root, "programme", 
                                 start=format_xmltv_date(p['airDateTime']), 
                                 stop=stop_dt.strftime("%Y%m%d%H%M%S +0000"),
                                 channel=xml_id)
            
            ET.SubElement(prog, "title").text = details.get('titles', [{}])[0].get('title120', 'No Title')
            
            # Description processing
            desc_text = ""
            if 'descriptions' in details:
                d_obj = details['descriptions']
                desc_list = d_obj.get('description1000') or d_obj.get('description100')
                if desc_list: desc_text = desc_list[0].get('description', '')
            if desc_text: ET.SubElement(prog, "desc").text = desc_text

            # S/E Data
            if 'metadata' in details:
                for meta in details['metadata']:
                    if 'Gracenote' in meta:
                        s_n, e_n = meta['Gracenote'].get('season'), meta['Gracenote'].get('episode')
                        if s_n and e_n:
                            ET.SubElement(prog, "episode-num", system="xmltv_ns").text = f"{int(s_n)-1}.{int(e_n)-1}.0/1"

    # 6. Final Save
    tree = ET.ElementTree(root)
    with open(OUTPUT_FILE, "wb") as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    os.chmod(OUTPUT_FILE, 0o666) 
    lprint(f"--- SUCCESS: All lineups merged. {len(master_stations_map)} channels written. ---")

if __name__ == "__main__":
    main()
