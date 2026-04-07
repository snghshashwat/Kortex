import os

import httpx
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
public_base_url = os.getenv("PUBLIC_BASE_URL")
secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")

if not bot_token or not public_base_url or not secret:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN, PUBLIC_BASE_URL, or TELEGRAM_WEBHOOK_SECRET")

url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
payload = {
    "url": f"{public_base_url}/telegram/webhook",
    "secret_token": secret,
}

response = httpx.post(url, json=payload, timeout=20)
response.raise_for_status()
print(response.json())
