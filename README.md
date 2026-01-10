I have had tons of issues getting locas to show new or repeat.
I have created a new script that pull the data from your plex server! Unfortunatly it only pulls 7 days.
I am going to use the guide data from plex, to figure out where my issues are at in the guide data from schedules direct and how to fix it.

Until then if you have an issue and have Plex serial with jellyfin,  try the plex grabber script
https://github.com/mejacobarussell/Schedules-Direct-Script/tree/main/plexguidegrabber

With JellyFin being broken when working with schedulesdirect.com, I tried dockers and all sorts of stuff, but running a nextPVR docker just for guide data didnt make sense to me. I created this script over a week with what free time I had.

Buy a Paramedic a coffee (or a line of code!) 

"Hi there! By day (and often by night), I’m a paramedic working on the front lines. When I’m not on the road, I’m at my desk diving into the world of computer science. It’s my favorite way to decompress after a long shift.

Your support helps keep me caffeinated for those 24-hour shifts and contributes to my learning journey in tech. Whether it's a 'thank you' for my service or just a shared love for clean code, I truly appreciate the support!"
Getting the family to adopt Jellyfin and Plex instead of paying for TV has been hard for me. They want it to be easy to use and always work.

<a href="https://www.buymeacoffee.com/yourditchdoc" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/arial-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

Schedules Direct to XMLTV for Unraid
A custom Python-based EPG (Electronic Program Guide) grabber designed specifically for Unraid users running Jellyfin or Emby.

This script solves the common "missing series recording" issue by correctly formatting episode numbers for daily news and regular series, while ensuring sub-channels (e.g., 4.1, 4.2) auto-map to your tuner.

🚀 Key Features
Jellyfin/Emby Optimized: Forces SxxExx and xmltv_ns tags even for Daily News to enable the "Record Series" button.

Automatic Channel Mapping: Cross-references ATSC Major/Minor numbers so channels like 47.1 map automatically to your antenna tuner.

Unraid Permission Friendly: Automatically sets file ownership to nobody:users and permissions to 777 for seamless access by Docker containers.

Intelligent "New" Flagging: Specifically identifies News programs to ensure they are marked as "New," preventing the DVR from skipping them as "Repeats."

LOCAL HOSTING OF CHANNEL ICONS AND COMING SOON TV SHOW PICTURES.

🛠️ Installation on Unraid
1. Requirements

Ensure you have the User Scripts plugin installed from the Unraid Community Applications store.

2. Setup Script

Go to Settings > User Scripts.
Click Add New Script and name it EPG-Grabber-V3.0.epg
Paste the contents of the Python script into the editor.
Update your Schedules Direct credentials in the configuration section:

Python
USER_NAME = "your_username"
PASSWORD_HASH = "your_sha1_password_hash"

3. Schedule
Set the script to run Daily (typically at 2:00 AM or 3:00 AM) to keep your guide data fresh.

📂 Output Details
Default Path: /mnt/user/appdata/schedulesdirect/guide.xml
Ownership: nobody:users
Permissions: 777

📺 Connecting to Jellyfin/Emby
Open your media server dashboard.
Navigate to Live TV > Tuner Devices.
Add a new XMLTV Guide Provider.

Point the path to: /data/schedulesdirect/guide.xml (mapped via your Docker container settings).
Refresh guide data. Channels should map automatically based on the 4.1, 4.2 numbering system.

📝 XML Structure Example
The script produces a rich XML format that includes specific triggers for the recording engine:

XML
<programme start="20260103180000 +0000" stop="20260103190000 +0000" channel="4.1">
    <title>Fox 4 News at 6</title>
    <category>Series</category>
    <category>News</category>
    <episode-num system="xmltv_ns">2025.0103.0</episode-num>
    <episode-num system="onscreen">S2026E0103</episode-num>
    <new/>
</programme>

🔑 Generating the Password Hash

Schedules Direct requires a SHA1 hash of your password rather than the plain text. To generate your PASSWORD_HASH, run this command in your Unraid terminal:

Bash
echo -n "your_password_here" | sha1sum | awk '{print $1}'
Copy the resulting 40-character string into the PASSWORD_HASH variable in the script.

📁 Unraid Folder Mapping
For the XML to be visible to your Jellyfin or Emby Docker container, ensure your container paths are mapped correctly in the Unraid Docker settings:

Container Path	Host Path	Notes
/data/schedulesdirect	/mnt/user/appdata/schedulesdirect	Set to Read Only for security

🔧 Troubleshooting
Channels not mapping: Ensure the debug log shows "Virtual Channel" numbers like 4.1 or 5.2. If it shows a 5-digit number (e.g., 19616), check that your Schedules Direct lineup is set to the "Local Broadcast" or "Antenna" version for your zip code.

Series recording missing: If the "Record Series" button is missing in Jellyfin, ensure the <category>Series</category> tag is present in the XML. This script forces this for all non-movie programs.

Permission Denied: If Jellyfin cannot see the file, check the logs of this script to ensure you see: [DEBUG] Permissions set: nobody:users 777.

This script is provided "as-is" for the community. Feel free to fork and modify it for your specific lineup needs.
