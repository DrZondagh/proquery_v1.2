# tools/test_grok.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-3-mini")

def test_grok():
    prompt = "Hello, are you online? Respond with 'Yes'."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            print("Grok response:", response.json()['choices'][0]['message']['content'].strip())
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_grok()