With JellyFin being broken when working with schedulesdirect.com, I tried dockers and all sorts of stuff, but running a nextPVR docker just for guide data didnt make sense to me. I created this script over a week with what free time I had.

Buy a Paramedic a coffee (or a line of code!) 

"Hi there! By day (and often by night), I’m a paramedic working on the front lines. When I’m not on the road, I’m at my desk diving into the world of computer science. It’s my favorite way to decompress after a long shift.

Your support helps keep me caffeinated for those 24-hour shifts and contributes to my learning journey in tech. Whether it's a 'thank you' for my service or just a shared love for clean code, I truly appreciate the support!"
Getting the family to adopt Jellyfin and Plex instead of paying for TV has been hard for me. They want it to be easy to use and always work.

<a href="https://www.buymeacoffee.com/yourditchdoc" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/arial-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

Schedules Direct to XMLTV for Jellyfin
A robust Python-based EPG (Electronic Program Guide) generator that fetches data from Schedules Direct and formats it specifically for Jellyfin. This script includes advanced logic to ensure that news programs and daily shows are correctly identified as "Series" to enable full DVR recording capabilities.

✨ Key Features
Series Recording Hack: Forces the "Record Series" button in Jellyfin for shows without traditional season/episode numbers (like local news).

* Local Icon Hosting: Downloads station logos locally to reduce API calls and speed up guide loading.
* Intelligent Repeat Logic: Cross-references original air dates to accurately flag "New" vs. "Repeat" episodes.
* Unraid Optimized: Includes automatic recursive permission management (chmod 777 and chown nobody:users).
* Test Mode: Option to process only one random channel to verify setup instantly.
* Debug Mode: Detailed logging to troubleshoot API responses or file system issues.

🚀 Setup Instructions
1. Prerequisites

A Schedules Direct active subscription.

Python 3.x installed.

The requests library (pip install requests).

2. Configuration

Open the script and update the configuration section at the top:
USER_NAME / PASSWORD: Your Schedules Direct credentials.
OUTPUT_DIR: The path where you want the XML and logos stored (e.g., /mnt/user/appdata/schedulesdirect).
JELLYFIN_URL / API_KEY: Required only if TRIGGER_JELLYFIN is set to True.

Toggle,Description
*DEBUG:  Set to True for verbose logging.
*TEST_MODE:  Set to True to process only 1 random channel (for testing).
*SAVE_JSON:  Set to False to prevent raw API data from being saved to your disk.
*TRIGGER_JELLYFIN:  Set to True to tell Jellyfin to refresh the guide automatically after a run.

*** jelly fin trigger will not work on first run, unless you have already mapped the /folder/xml file in the LIVE TV page in Jellyfin.


📂 Directory Structure
After the first run, your output directory will look like this:
/schedulesdirect/
├── guide.xml        <-- Point Jellyfin to this file
└── logos/           <-- Station icons stored here
    ├── 100147.png
    └── 20371.jpg

    Here is a professional and clear README.md tailored for your Schedules Direct to XMLTV script. It explains the features you’ve added (Local Icons, Debug Mode, Test Mode) and provides clear setup instructions for an Unraid environment.

Schedules Direct to XMLTV for Jellyfin
A robust Python-based EPG (Electronic Program Guide) generator that fetches data from Schedules Direct and formats it specifically for Jellyfin. This script includes advanced logic to ensure that news programs and daily shows are correctly identified as "Series" to enable full DVR recording capabilities.

✨ Key Features
Series Recording Hack: Forces the "Record Series" button in Jellyfin for shows without traditional season/episode numbers (like local news).

Local Icon Hosting: Downloads station logos locally to reduce API calls and speed up guide loading.

Intelligent Repeat Logic: Cross-references original air dates to accurately flag "New" vs. "Repeat" episodes.

Unraid Optimized: Includes automatic recursive permission management (chmod 777 and chown nobody:users).

Test Mode: Option to process only one random channel to verify setup instantly.

Debug Mode: Detailed logging to troubleshoot API responses or file system issues.

🚀 Setup Instructions
1. Prerequisites

A Schedules Direct active subscription.

Python 3.x installed.

The requests library (pip install requests).

2. Configuration

Open the script and update the configuration section at the top:

USER_NAME / PASSWORD: Your Schedules Direct credentials.

OUTPUT_DIR: The path where you want the XML and logos stored (e.g., /mnt/user/appdata/schedulesdirect).

JELLYFIN_URL / API_KEY: Required only if TRIGGER_JELLYFIN is set to True.

3. Toggles

Toggle	Description
DEBUG	Set to True for verbose logging.
TEST_MODE	Set to True to process only 1 random channel (for testing).
SAVE_JSON	Set to False to prevent raw API data from being saved to your disk.
TRIGGER_JELLYFIN	Set to True to tell Jellyfin to refresh the guide automatically after a run.
📂 Directory Structure
After the first run, your output directory will look like this:

Plaintext
/schedulesdirect/
├── guide.xml        <-- Point Jellyfin to this file
└── logos/           <-- Station icons stored here
    ├── 100147.png
    └── 20371.jpg
🛠 Integration with Jellyfin
Navigate to Dashboard > Live TV in Jellyfin.

Add a new XMLTV Tuner.

File Path: Enter the path to your guide.xml (Ensure the path is mapped inside your Jellyfin Docker container).

Refresh Guide Data: Run the manual refresh task. If logos do not appear immediately, ensure your Docker container has a path mapping to the logos/ folder.

🤝 Permissions
The script is designed to run in an Unraid environment. It automatically executes a recursive chmod 777 and chown nobody:users on the output directory at the end of every run to ensure the Jellyfin Docker container can always read the newly generated files.

📝 License
MIT License. Feel free to modify and share.
