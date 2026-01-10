#!/usr/bin/env python3
# Description: Enhanced conversion with fix for "Everything is New" badge bug

import sqlite3
import shutil
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================================================================
#                               CONFIGURATION
# ==============================================================================
TIMEZONE_OFFSET = "-0600" # Central Time (Arlington)
PLEX_DB_PATH = r"/mnt/user/appdata/Plex-Media-Server/Library/Application Support/Plex Media Server/Plug-in Support/Databases/tv.plex.providers.epg.cloud-729b9c07-3c68-4ac0-b803-d228ee6b59c1.db"
OUTPUT_XML = "/mnt/user/appdata/schedulesdirect/plex_guide.xml"
TEMP_DIR = "/mnt/user/appdata/schedulesdirect/plex_EPG/"
# ==============================================================================

def create_xmltv():
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
    temp_db = os.path.join(TEMP_DIR, "temp_epg.db")
    
    print(f"--- Starting Enhanced Sync V3 ---")
    try:
        shutil.copy2(PLEX_DB_PATH, temp_db)
    except Exception as e:
        print(f"Error copying DB: {e}")
        return

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    root = ET.Element("tv", {"generator-info-name": "PlexToJellyfin-Enhanced-V3"})

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
        tv.user_thumb_url AS channel_logo,
        episode.user_thumb_url AS ep_thumb,
        show.originally_available_at AS air_date,
        show.tags_genre AS genres
    FROM metadata_items AS show
    JOIN metadata_items AS season ON show.id = season.parent_id
    JOIN metadata_items AS episode ON season.id = episode.parent_id
    JOIN media_items AS items ON episode.id = items.metadata_item_id
    JOIN tags AS tv ON items.channel_id = tv.id
    ORDER BY items.begins_at;
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    if not rows: return

    # Time Correction Logic
    first_start = rows[0][5]
    now_unix = datetime.now().timestamp()
    today_date_str = datetime.now().strftime('%Y%m%d')
    time_shift = now_unix - first_start if first_start > now_unix else 0

    # 1. Process Channels
    channels = {}
    for row in rows:
        p_id, name, logo = row[1], row[0], row[10]
        if p_id not in channels:
            match = re.match(r'^(\d+\.\d+|\d+)', name)
            clean_id = match.group(1) if match else str(p_id)
            channels[p_id] = {"name": name, "logo": logo, "clean_id": clean_id}

    for p_id, info in channels.items():
        c_node = ET.SubElement(root, "channel", id=info['clean_id'])
        ET.SubElement(c_node, "display-name").text = info['name']
        ET.SubElement(c_node, "display-name").text = info['clean_id']
        if info['logo']: ET.SubElement(c_node, "icon", src=info['logo'])

    # 2. Process Programmes
    for row in rows:
        p_id, s_title, e_title, desc, start, end, rating, s_num, e_num, c_logo, ep_thumb, air_date, genres = row[1:]
        c_id = channels[p_id]['clean_id']
        
        t_format = f"%Y%m%d%H%M%S {TIMEZONE_OFFSET}"
        t_start = datetime.fromtimestamp(start + time_shift).strftime(t_format)
        t_end = datetime.fromtimestamp(end + time_shift).strftime(t_format)

        prog = ET.SubElement(root, "programme", start=t_start, stop=t_end, channel=c_id)
        ET.SubElement(prog, "title", lang="en").text = str(s_title or "No Title")
        if e_title and e_title != s_title:
            ET.SubElement(prog, "sub-title", lang="en").text = str(e_title)
        ET.SubElement(prog, "desc", lang="en").text = str(desc or "")
        
        if genres and isinstance(genres, str):
            for genre in genres.split('|'):
                ET.SubElement(prog, "category", lang="en").text = genre

        # FIXED AIR DATE / NEW BADGE LOGIC
        if air_date:
            try:
                if isinstance(air_date, (int, float)):
                    clean_date = datetime.fromtimestamp(air_date).strftime('%Y%m%d')
                else:
                    clean_date = str(air_date).split(' ')[0].replace('-', '')
                
                # Only add 'previously-shown' if the air_date is NOT today
                # If we omit this tag, Jellyfin sees it as a Premiere (New)
                if clean_date < today_date_str:
                    ET.SubElement(prog, "previously-shown", start=clean_date)
                else:
                    # It's actually a new episode today!
                    ET.SubElement(prog, "new")
            except:
                pass

        icon_url = ep_thumb or c_logo
        if icon_url: ET.SubElement(prog, "icon", src=str(icon_url))
        if rating:
            r_node = ET.SubElement(prog, "rating", system="VCHIP")
            ET.SubElement(r_node, "value").text = str(rating)

        if s_num and e_num:
            ns = f"{max(0, s_num-1)}.{max(0, e_num-1)}.0"
            ET.SubElement(prog, "episode-num", system="xmltv_ns").text = ns

    tree = ET.ElementTree(root)
    if hasattr(ET, 'indent'): ET.indent(tree, space="  ")
    tree.write(OUTPUT_XML, encoding="utf-8", xml_declaration=True)
    conn.close()
    if os.path.exists(temp_db): os.remove(temp_db)
    print(f"--- Success! Enhanced XML (Fixed Badges) created at {OUTPUT_XML} ---")

if __name__ == "__main__":
    create_xmltv()
