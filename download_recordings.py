import os
import requests
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

os.makedirs("recordings", exist_ok=True)

recordings = client.recordings.list(limit=10)

print(f"Found {len(recordings)} recordings")

for rec in recordings:
    print("Recording:", rec.sid, rec.date_created, rec.duration)

    media_url = "https://api.twilio.com" + rec.uri.replace(".json", ".mp3")
    output_path = os.path.join("recordings", f"{rec.sid}.mp3")

    response = requests.get(media_url, auth=(ACCOUNT_SID, AUTH_TOKEN))

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print("Downloaded:", output_path)
    else:
        print("Failed:", rec.sid, response.status_code, response.text)