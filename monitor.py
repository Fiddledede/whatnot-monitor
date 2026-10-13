import os
import sys
import requests

# ==================== CONFIGURATION ====================
WHATNOT_USERNAME = "drexs_emporium"
# =======================================================

# Target the specific /shows URL where live state tags are initially rendered
TARGET_URL = f"https://www.whatnot.com/en-GB/user/{WHATNOT_USERNAME}/shows"
DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        html = response.text
        
        print(f"Targeting URL: {TARGET_URL}")
        print(f"Server Connection Status: {response.status_code}")
        
        # Scan for the physical live badges that appear when a show is actively broadcasting
        if "live-badge" in html.lower() or "live" in html.lower() or "badges/live.svg" in html:
            # Let's perform a safety check to ensure it's not picking up static words
            if "live-badge" in html.lower() or "badges/live.svg" in html:
                return True
                
    except Exception as e:
        print(f"Network error encountered: {e}")
        
    return False

def send_discord_alert(is_test=False):
    profile_url = f"https://www.whatnot.com/user/{WHATNOT_USERNAME}"
    if is_test:
        payload = {
            "content": f"✅ **Ping Test Successful!** Your Discord Webhook configuration is working correctly for `{WHATNOT_USERNAME}`."
        }
    else:
        payload = {
            "content": f"🚨 **{WHATNOT_USERNAME} is LIVE on Whatnot!** 🚨\nCheck out the show here: {profile_url}"
        }
    requests.post(DISCORD_URL, json=payload)

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
