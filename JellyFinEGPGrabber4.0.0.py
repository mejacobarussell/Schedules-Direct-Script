#
# work in progress
#
#!/usr/bin/python3
"""
Schedules Direct & TVDB Grabber for Unraid/Jellyfin
Author: mrjacobarussell 
Location: /mnt/user/appdata/schedulesdirect/

CHANGE LOG:
----------
v4.2.2 - Added real-time log flushing (sys.stdout.reconfigure) to prevent 
         buffering in Unraid console. Increased progress log frequency.
v4.2.1 - Integrated Unraid Dashboard Notifications (notify script).
v4.2.0 - Added persistent local logging to 'grabber.log' with auto-creation.
v4.1.2 - Implemented TVDB caching (tvdb_cache.json) to speed up repeat runs.
v4.1.0 - Initial stable build with SD-to-XMLTV conversion and episode mapping.
"""

import os, sys, subprocess, json, datetime, time, logging
import xml.etree.ElementTree as ET

# --- CONFIGURATION ---
USER_NAME = "mrjacobarussell"
PASSWORD_HASH = "e06e6df873d3fcc0e7fd33a2246da96a93c1fbb4" 
TVDB_API_KEY = "4c371140-719b-44ce-9eff-0448c098b623"
TVDB_PIN = "695C18D5D4F1D6.34161382" 

OUTPUT_DIR = "/mnt/user/appdata/schedulesdirect"
XML_OUTPUT = os.path.join(OUTPUT_DIR, "guide.xml")
CACHE_FILE = os.path.join(OUTPUT_DIR, "tvdb_cache.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "grabber.log")

DAYS_TO_FETCH = 7 
TIMEOUT = 15 

# --- REAL-TIME LOGGING SETUP ---
os.makedirs(OUTPUT_DIR, exist_ok=True)

class RealTimeHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(formatter)
logger.addHandler(fh)

sh = RealTimeHandler(sys.stdout)
sh.setFormatter(formatter)
logger.addHandler(sh)

# Force immediate output to Unraid console
sys.stdout.reconfigure(line_buffering=True)

def send_unraid_notify(subject, message, importance="normal"):
    try:
        os.system(f'/usr/local/emhttp/webGui/scripts/notify -i {importance} -s "{subject}" -d "{message}"')
    except: pass

try:
    import requests
except ImportError:
    logger.info("Installing missing dependency: requests...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ... [The TVDBAPI Class and internal logic remain unchanged from 4.2.2] ...

def generate_xml():
    logger.info("=== STARTING EPG GRAB v4.2.2 ===")
    # ... logic continues ...
    
    # Final cleanup log
    logger.info(f"SUCCESS: EPG generated with {prog_count} programs.")
    send_unraid_notify("EPG Update", f"Process complete. {prog_count} items synced.", "normal")

if __name__ == "__main__":
    generate_xml()
