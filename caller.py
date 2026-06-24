import os
import time
from dotenv import load_dotenv
from twilio.rest import Client
from scenarios import SCENARIOS

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
BASE_URL = os.getenv("BASE_URL")
TEST_NUMBER = os.getenv("TEST_NUMBER", "+18054398008")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def start_call(scenario):
    voice_url = f"{BASE_URL}/voice?scenario_id={scenario['id']}"

    call = client.calls.create(
        to=TEST_NUMBER,
        from_=TWILIO_PHONE_NUMBER,
        url=voice_url,
        record=True,
        recording_status_callback=f"{BASE_URL}/recording",
        status_callback=f"{BASE_URL}/status",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
    )

    print(f"Started {scenario['id']} | Call SID: {call.sid}")
    return call.sid


if __name__ == "__main__":
    for scenario in SCENARIOS:
        start_call(scenario)
        time.sleep(120)