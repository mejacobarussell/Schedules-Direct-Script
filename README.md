# Schedules-Direct-Script-
Python Script for use with SchedulesDirect.com and Jellyfin 

🛰️ Schedules Direct to Jellyfin XMLTV Optimizer
An automated EPG (Electronic Program Guide) processor designed to bridge the Schedules Direct JSON API and Jellyfin Live TV. Optimized for Unraid users, this script aggregates multiple channel lineups, enriches program metadata, and generates a structured guide.xml for seamless channel mapping.

🌟 Key Features
Multi-Lineup Aggregation: Automatically detects and merges all lineups associated with your Schedules Direct account (e.g., Local OTA, Cable, and Satellite) into a single XML file.

Jellyfin-Specific Metadata: * XMLTV_NS Support: Converts Gracenote metadata into the xmltv_ns format required by Jellyfin for proper Season/Episode grouping.

High-Res Descriptions: Prioritizes 1000-character descriptions for rich program details.

Automated IDs: Uses stable StationID keys to prevent guide "shifting" when channel names change.

Unraid Integration: Built to run via the User Scripts plugin with automatic permission handling (chmod 0666) to avoid Docker "Access Denied" errors.

Efficient Batching: Uses chunked API requests (500 stations/5000 programs) to prevent timeouts and respect API rate limits.

🏗️ How It Works
The script executes a six-stage pipeline to ensure data integrity:

Auth: Negotiates a SHA1-hashed token with the Schedules Direct API.

Discovery: Iterates through every lineup assigned to the user account.

De-duplication: Maps unique stations to a master dictionary to prevent duplicate channel entries.

Schedule Sync: Pulls 14 days of airing data in batches.

Metadata Enrichment: Fetches specific episode titles, descriptions, and air dates.

XML Transformation: Generates the final XMLTV file with Jellyfin-friendly formatting.

🛠️ Installation & Setup
1. Requirements

Python 3.x

requests library (pip install requests)

2. Configuration

***** Update the following variables within the script: *****

Python
USER_NAME = 'your_username'
PASSWORD  = 'YOURPASSWORD'
OUTPUT_DIR = "/mnt/user/appdata/schedulesdirect"

3. Unraid Automation
Install the User Scripts plugin.
Create a new script (e.g., Fetch-EPG).
Paste the script content and save.
Set the schedule to Daily (e.g., 0 3 * * * for 3 AM).

📺 Jellyfin Integration
To connect the output to Jellyfin:

Path Mapping: Ensure your Jellyfin Docker template maps the Unraid path /mnt/user/appdata/schedulesdirect to an internal container path like /data/guide.

Add Provider: Go to Dashboard > Live TV > Guide Data Providers and add an XMLTV provider.

Mapping: Use the Map Channels tool. Because this script provides the StationID and Callsign, Jellyfin will auto-match most channels.

📜 License
Distributed under the MIT License. See LICENSE for more information.
