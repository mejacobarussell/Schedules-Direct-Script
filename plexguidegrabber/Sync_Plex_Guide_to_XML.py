#!/usr/bin/env python3
# Description: Converts Plex EPG database to XMLTV for Jellyfin (Arlington/Central Time)

import sqlite3
import shutil
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
#!/usr/bin/env python3
# Description: Converts Plex EPG database to XMLTV for Jellyfin (Arlington/Central Time)

import sqlite3
import shutil
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================================================================
#                               CONFIGURATION
# ==============================================================================
# TIMEZONE_OFFSET: Sets the local time difference from UTC (GMT).
#   - If your guide is 6 hours AHEAD of current time, use a negative (-) offset.
#   - If your guide is 6 hours BEHIND current time, use a positive (+) offset.
#
# US TIME ZONE REFERENCE (Standard Time):
#   - Eastern Standard Time (EST)  : "-0500"
#   - Central Standard Time (CST)  : "-0600" (Arlington, TX)
#   - Mountain Standard Time (MST) : "-0700"
#   - Pacific Standard Time (PST)  : "-0800"
#   - Alaska Standard Time (AKST)  : "-0900"
#   - Hawaii Standard Time (HST)   : "-1000"
#
# GMT/UTC REFERENCE:
#   - London / GMT (Standard)      : "+0000"
#   - Western Europe (CET)         : "+0100"
#   - Australia (AEDT)             : "+1100"
#
# Note: During Daylight Saving Time (Summer), subtract 1 hour (e.g., CST becomes -0500).
TIMEZONE_OFFSET = "-0600"

# PLEX_DB_PATH: Path to your Plex EPG database file.
PLEX_DB_PATH = r"/mnt/user/appdata/Plex-Media-Server/Library/Application Support/Plex Media Server/Plug-in Support/Databases/tv.plex.providers.epg.cloud-729b9c07-3c68-4ac0-b803-d228ee6b59c1.db"

# OUTPUT_XML: Path where the final XMLTV file will be saved for Jellyfin.
OUTPUT_XML = "/mnt/user/appdata/schedulesdirect/plex_guide.xml"

# TEMP_DIR: Temporary folder used to copy the DB to prevent file locking.
TEMP_DIR = "/mnt/user/appdata/schedulesdirect/plex_EPG/"
# ==============================================================================


def create_xmltv():
    # 1. Setup temporary workspace
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    db_name = os.path.basename(PLEX_DB_PATH)
    temp_db = os.path.join(TEMP_DIR, db_name)
    
    print(f"--- Starting Sync ---")
    try:
        shutil.copy2(PLEX_DB_PATH, temp_db)
        # Copy sidecar files to prevent locking issues
        for suffix in ["-shm", "-wal"]:
            if os.path.exists(PLEX_DB_PATH + suffix):
                shutil.copy2(PLEX_DB_PATH + suffix, temp_db + suffix)
    except FileNotFoundError:
        print(f"Error: Plex DB not found at: {PLEX_DB_PATH}")
        return

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    root = ET.Element("tv", {"generator-info-name": "PlexToJellyfin-Arlington-Final"})

    # 2. Query Metadata
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
        conn.close()
        return

    # 3. GLOBAL TIME CORRECTION
    # Shifts future data (Jan 21) back to match the current system clock (Jan 10)
    first_start = rows[0][5]
    now_unix = datetime.now().timestamp()
    time_shift = 0
    if first_start > now_unix:
        time_shift = now_unix - first_start
        print(f"Applying date shift: Moving programs back to match today.")

    # 4. Map Channels with Sync IDs
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
        ET.SubElement(c_node, "display-name").text = info['clean_id'] # Helpful for auto-mapping
        if info['logo']:
            ET.SubElement(c_node, "icon", src=info['logo'])

    # 5. Process Programmes
    for row in rows:
        p_id, s_title, e_title, desc, start, end, rating, s_num, e_num = row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]
        c_id = channel_map[p_id]['clean_id']
        
        # Applying the TIMEZONE_OFFSET and time_shift
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

    # 6. Save File and Cleanup
    tree = ET.ElementTree(root)
    if hasattr(ET, 'indent'): 
        ET.indent(tree, space="  ", level=0)
    tree.write(OUTPUT_XML, encoding="utf-8", xml_declaration=True)

    conn.close()

    # Cleanup temporary database files
    if os.path.exists(temp_db):
        os.remove(temp_db)
        for suffix in ["-shm", "-wal"]:
            if os.path.exists(temp_db + suffix):
                os.remove(temp_db + suffix)
        print("Cleaned up temporary database files.")

    print(f"--- Success! ---")
    print(f"XML created at: {OUTPUT_XML}")
    print(f"Applied Offset: {TIMEZONE_OFFSET}")

if __name__ == "__main__":
    create_xmltv()
def create_xmltv():
    # 1. Setup temporary workspace
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    db_name = os.path.basename(PLEX_DB_PATH)
    temp_db = os.path.join(TEMP_DIR, db_name)
    
    print(f"--- Starting Sync ---")
    try:
        shutil.copy2(PLEX_DB_PATH, temp_db)
        # Copy sidecar files to prevent locking issues
        for suffix in ["-shm", "-wal"]:
            if os.path.exists(PLEX_DB_PATH + suffix):
                shutil.copy2(PLEX_DB_PATH + suffix, temp_db + suffix)
    except FileNotFoundError:
        print(f"Error: Plex DB not found at: {PLEX_DB_PATH}")
        return

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    root = ET.Element("tv", {"generator-info-name": "PlexToJellyfin-Arlington-Final"})

    # 2. Query Metadata
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
        conn.close()
        return

    # 3. GLOBAL TIME CORRECTION
    # Shifts future data (Jan 21) back to match the current system clock (Jan 10)
    first_start = rows[0][5]
    now_unix = datetime.now().timestamp()
    time_shift = 0
    if first_start > now_unix:
        time_shift = now_unix - first_start
        print(f"Applying date shift: Moving programs back to match today.")

    # 4. Map Channels with Sync IDs
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
        ET.SubElement(c_node, "display-name").text = info['clean_id'] # Helpful for auto-mapping
        if info['logo']:
            ET.SubElement(c_node, "icon", src=info['logo'])

    # 5. Process Programmes
    for row in rows:
        p_id, s_title, e_title, desc, start, end, rating, s_num, e_num = row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]
        c_id = channel_map[p_id]['clean_id']
        
        # Applying the TIMEZONE_OFFSET and time_shift
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

    # 6. Save File and Cleanup
    tree = ET.ElementTree(root)
    if hasattr(ET, 'indent'): 
        ET.indent(tree, space="  ", level=0)
    tree.write(OUTPUT_XML, encoding="utf-8", xml_declaration=True)

    conn.close()

    # Cleanup temporary database files
    if os.path.exists(temp_db):
        os.remove(temp_db)
        for suffix in ["-shm", "-wal"]:
            if os.path.exists(temp_db + suffix):
                os.remove(temp_db + suffix)
        print("Cleaned up temporary database files.")

    print(f"--- Success! ---")
    print(f"XML created at: {OUTPUT_XML}")
    print(f"Applied Offset: {TIMEZONE_OFFSET}")

if __name__ == "__main__":
    create_xmltv()
