import os
import sys
import requests

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
    # Target Whatnot's public backend gateway
    url = "https://whatnot.com"
    
    # Payload targeting the specific user's public info
    payload = {
        "query": """
        query getUserPublicInfo(\$username: String!) {
            userPublicInfo(username: \$username) {
                user {
                    username
                    isLive
                }
            }
        }
        """,
        "variables": {"username": WHATNOT_USERNAME}
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Extract the native true/false live status from Whatnot's database response
            is_live = data.get("data", {}).get("userPublicInfo", {}).get("user", {}).get("isLive", False)
            print(f"API Check Result for {WHATNOT_USERNAME}: isLive = {is_live}")
            return is_live
        else:
            print(f"API error: Received status code {response.status_code}")
    except Exception as e:
        print(f"Error checking API: {e}")
    return False

def send_discord_alert(is_test=False):
    if is_test:
        payload = {
            "content": f"✅ **Ping Test Successful!** Your Discord Webhook is configured correctly for monitoring `{WHATNOT_USERNAME}`."
        }
    else:
        payload = {
            "content": f"🚨 **{WHATNOT_USERNAME} is LIVE on Whatnot!** 🚨\nCheck out the show here: https://www.whatnot.com/user/{WHATNOT_USERNAME}"
        }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running manual test notification...")
        send_discord_alert(is_test=True)
        sys.exit(0)

    currently_live = check_whatnot_live()
    previously_live = get_previous_status()

    if currently_live and not previously_live:
        print("Seller just went live! Sending alert.")
        send_discord_alert()
    elif currently_live and previously_live:
        print("Seller is still live. Skipping duplicate alert.")
    elif not currently_live and previously_live:
        print("Seller went offline. Updating status.")
    else:
        print("Seller is offline.")

    save_current_status(currently_live)
