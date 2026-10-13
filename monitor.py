import os
import sys
import requests
import re

# Configuration
WHATNOT_USERNAME = "drexs_emporium"  
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Status tracking file
STATUS_FILE = "live_status.txt"

def get_previous_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            return f.read().strip() == "True"
    return False

def save_current_status(is_live):
    with open(STATUS_FILE, "w") as f:
        f.write(str(is_live))

def check_whatnot_live():
    # Target the direct web portal locale URL layout safely
    url = f"https://whatnot.com{WHATNOT_USERNAME}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        html = response.text
        
        # Log basic debug data to the actions panel
        print(f"Server Response Code: {response.status_code}")
        
        # Method 1: Look for exact case-insensitive raw boolean keys in backend script text blocks
        if '"islive":true' in html.lower() or '"is_live":true' in html.lower() or '"isactivelivestream":true' in html.lower():
            print("Found explicit true state flag in backend data frame.")
            return True
            
        # Method 2: Check for live badges or streaming media indicator hooks 
        if 'badges/live.svg' in html or 'live-badge' in html.lower() or '"status":"live"' in html.lower():
            print("Found visual asset badge matching live states.")
            return True
            
    except Exception as e:
        print(f"Scraper error encountered: {e}")
        
    return False

def send_discord_alert(is_test=False):
    # Formatted to create a clean clickable link structure for the end-user
    profile_url = f"https://whatnot.com{WHATNOT_USERNAME}"
    
    if is_test:
        payload = {
            "content": f"✅ **Ping Test Successful!** Your Discord Webhook is configured correctly for monitoring `{WHATNOT_USERNAME}`."
        }
    else:
        payload = {
            "content": f"🚨 **{WHATNOT_USERNAME} is LIVE on Whatnot!** 🚨\nCheck out the show here: {profile_url}"
        }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running manual test notification...")
        send_discord_alert(is_test=True)
        sys.exit(0)

    currently_live = check_whatnot_live()
    previously_live = get_previous_status()
    
    print(f"Current scan state: {currently_live} | Previous scan state: {previously_live}")

    if currently_live and not previously_live:
        print("Change detected: Seller just went live! Sending Discord message.")
        send_discord_alert()
    elif currently_live and previously_live:
        print("Seller is still live. Skipping message to avoid spam.")
    elif not currently_live and previously_live:
        print("Seller went offline. Resetting status file tracker.")
    else:
        print("Seller remains offline. No action taken.")

    save_current_status(currently_live)
