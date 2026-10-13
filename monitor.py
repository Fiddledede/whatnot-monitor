import os
import sys
import requests

# Hardcoded exact target URL to guarantee no string joining bugs occur
TARGET_URL = "https://www.whatnot.com/en-GB/user/drexs_emporium/shows"
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
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        html = response.text
        
        print(f"Server Connection Status: {response.status_code}")
        
        # Checking backend parameters for explicit live truth values
        if '"islive":true' in html.lower() or '"is_live":true' in html.lower() or '"isactivelivestream":true' in html.lower():
            return True
            
        # Checking visual asset badge allocations 
        if 'badges/live.svg' in html or 'live-badge' in html.lower() or '"status":"live"' in html.lower():
            return True
            
    except Exception as e:
        print(f"Network error encountered during download: {e}")
        
    return False

def send_discord_alert(is_test=False):
    if is_test:
        payload = {
            "content": "✅ **Ping Test Successful!** Your Discord Webhook configuration is working correctly."
        }
    else:
        payload = {
            "content": f"🚨 **drexs_emporium is LIVE on Whatnot!** 🚨\nCheck out the show here: {TARGET_URL}"
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
