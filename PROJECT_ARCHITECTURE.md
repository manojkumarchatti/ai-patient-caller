# AI Patient Caller Architecture

![AI Patient Caller Architecture](./architecture_diagram.svg)

## Basic Flow

1. `caller.py` starts an outbound call using Twilio.
2. Twilio calls the target phone number.
3. When the person answers, Twilio requests instructions from the Flask webhook.
4. Cloudflare forwards Twilio requests to the local Flask app.
5. `app.py` returns TwiML so Twilio can speak and listen.
6. Twilio sends captured speech to `/respond`.
7. Flask sends the speech, scenario, and history to OpenAI.
8. OpenAI returns the patient reply.
9. Twilio speaks the reply and continues the conversation.
10. Twilio records the call, and `download_recordings.py` downloads it.

## Python Files

- `caller.py`: starts the outbound phone call.
- `app.py`: controls the call flow and OpenAI responses.
- `scenarios.py`: stores patient test scenarios.
- `download_recordings.py`: downloads Twilio MP3 recordings.
- `.env`: stores API keys, phone numbers, and Cloudflare URL.

