#!/usr/bin/env python3

import sqlite3
import shutil
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# ================= ADJUSTABLE FIELDS =================
# Set your local timezone offset here (e.g., "-0600" for Central Time)
TIMEZONE_OFFSET = "-0600"

PLEX_DB_PATH = r"/mnt/user/appdata/Plex-Media-Server/Library/Application Support/Plex Media Server/Plug-in Support/Databases/tv.plex.providers.epg.cloud-729b9c07-3c68-4ac0-b803-d228ee6b59c1.db"
OUTPUT_XML = "/mnt/user/appdata/schedulesdirect/plex_guide.xml"
TEMP_DIR = "/mnt/user/appdata/schedulesdirect/plex_EPG/"
# =====================================================

def create_xmltv():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    db_name = os.path.basename(PLEX_DB_PATH)
    temp_db = os.path.join(TEMP_DIR, db_name)
    
    print(f"--- Starting Sync ---")
    try:
        shutil.copy2(PLEX_DB_PATH, temp_db)
        for suffix in ["-shm", "-wal"]:
            if os.path.exists(PLEX_DB_PATH + suffix):
                shutil.copy2(PLEX_DB_PATH + suffix, temp_db + suffix)
    except FileNotFoundError:
        print(f"Error: Plex DB not found at: {PLEX_DB_PATH}")
        return

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    root = ET.Element("tv", {"generator-info-name": "PlexToJellyfin-Final-Adjustable"})

    query = """
    SELECT 
        tv.tag AS channel_name,
        tv.id AS channel_id,
        show.title AS show_title,
        episode.title AS ep_title,
        episode.summary AS description,
        items.begins_at AS start_unix,
        items.ends_at AS end_unix,
        show.content_rating AS rating,
        season."index" AS season_num,
        episode."index" AS episode_num,
        tv.user_thumb_url AS logo_url
    FROM metadata_items AS show
    JOIN metadata_items AS season ON show.id = season.parent_id
    JOIN metadata_items AS episode ON season.id = episode.parent_id
    JOIN media_items AS items ON episode.id = items.metadata_item_id
    JOIN tags AS tv ON items.channel_id = tv.id
    ORDER BY items.begins_at;
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        print("Warning: No program data found.")
        return

    # Time Correction Logic (Moves Jan 21 data to Jan 10)
    first_start = rows[0][5]
    now_unix = datetime.now().timestamp()
    time_shift = 0
    if first_start > now_unix:
        time_shift = now_unix - first_start
        print(f"Applying date shift: Moving programs back to match today.")

    # Process Channels
    channel_map = {}
    for row in rows:
        full_name, p_id, logo = row[0], row[1], row[10]
        if p_id not in channel_map:
            match = re.match(r'^(\d+\.\d+|\d+)', full_name)
            clean_id = match.group(1) if match else str(p_id)
            channel_map[p_id] = {"name": full_name, "logo": logo, "clean_id": clean_id}

    for p_id, info in channel_map.items():
        c_node = ET.SubElement(root, "channel", id=info['clean_id'])
        ET.SubElement(c_node, "display-name").text = info['name']
        ET.SubElement(c_node, "display-name").text = info['clean_id']
        if info['logo']:
            ET.SubElement(c_node, "icon", src=info['logo'])

    # Process Programmes
    for row in rows:
        p_id, s_title, e_title, desc, start, end, rating, s_num, e_num = row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]
        
        c_id = channel_map[p_id]['clean_id']
        
        # Applying the TIMEZONE_OFFSET variable here
        t_format = f"%Y%m%d%H%M%S {TIMEZONE_OFFSET}"
        t_start = datetime.fromtimestamp(start + time_shift).strftime(t_format)
        t_end = datetime.fromtimestamp(end + time_shift).strftime(t_format)

        prog_node = ET.SubElement(root, "programme", {
            "start": t_start, "stop": t_end, "channel": c_id
        })
        
        ET.SubElement(prog_node, "title", lang="en").text = s_title
        if e_title and e_title != s_title:
            ET.SubElement(prog_node, "sub-title", lang="en").text = e_title
        
        ET.SubElement(prog_node, "desc", lang="en").text = desc if desc else ""
        
        if rating:
            r_node = ET.SubElement(prog_node, "rating", system="VCHIP")
            ET.SubElement(r_node, "value").text = rating

        if s_num is not None and e_num is not None:
            ns_val = f"{max(0, s_num - 1)}.{max(0, e_num - 1)}.0"
            ET.SubElement(prog_node, "episode-num", system="xmltv_ns").text = ns_val

    tree = ET.ElementTree(root)
    if hasattr(ET, 'indent'): 
        ET.indent(tree, space="  ", level=0)
    tree.write(OUTPUT_XML, encoding="utf-8", xml_declaration=True)

    conn.close()
    print(f"--- Success! ---")
    print(f"File created: {OUTPUT_XML}")
    print(f"Current Offset: {TIMEZONE_OFFSET}")

if __name__ == "__main__":
    create_xmltv()
