import os
import sys
import requests
import re

# Configuration
WHATNOT_USERNAME = "drexs_emporium"  # <-- Replace with their exact username
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
    url = f"https://www.whatnot.com/en-GB/user/{WHATNOT_USERNAME}"
    
    # Simulating a realistic web browser to request the raw text content
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        html_content = response.text
        
        # When live, Whatnot embeds specific JSON payloads and raw HTML image state flags
        # such as '"isActiveLiveStream":true' or specific avatar wrapper configurations
        if '"isActiveLiveStream":true' in html_content or '"isLive":true' in html_content:
            return True
            
        # Alternative fallback: scan the profile's text payload directly for stream markers
        live_markers = [
            'status":"LIVE"',
            'avatar-live-border',
            'badges/live.svg',
            '"liveStatus":"LIVE"'
        ]
        
        for marker in live_markers:
            if marker in html_content:
                return True
                
    except Exception as e:
        print(f"Scraper error encountered: {e}")
        
    return False

def send_discord_alert(is_test=False):
    if is_test:
        payload = {
            "content": f"✅ **Ping Test Successful!** Your Discord Webhook is configured correctly for monitoring `{WHATNOT_USERNAME}`."
        }
    else:
        payload = {
            "content": f"🚨 **{WHATNOT_USERNAME} is LIVE on Whatnot!** 🚨\nCheck out the show here: https://whatnot.com{WHATNOT_USERNAME}"
        }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv == "test":
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
