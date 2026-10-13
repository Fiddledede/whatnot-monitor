import os
import requests

# Configuration
WHATNOT_USERNAME = "THE_SELLER_USERNAME_HERE"  # <-- Replace with their exact username
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_whatnot_live():
    url = f"https://whatnot.com{WHATNOT_USERNAME}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Whatnot profile pages visually contain the word "LIVE" or a live tag when streaming
        if '"isLive":true' in response.text or 'live-badge' in response.text.lower():
            return True
    except Exception as e:
        print(f"Error checking page: {e}")
    return False

def send_discord_alert():
    payload = {
        "content": f"🚨 **{WHATNOT_USERNAME} is LIVE on Whatnot!** 🚨\nCheck out the show here: https://whatnot.com{WHATNOT_USERNAME}"
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if check_whatnot_live():
        print("Seller is live! Sending alert.")
        send_discord_alert()
    else:
        print("Seller is offline.")
