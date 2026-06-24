# Pretty Good AI Voice Bot

This project is a Python voice bot that calls the Pretty Good AI assessment test number and simulates realistic patient conversations.

## Features

- Places outbound calls using Twilio
- Simulates realistic patient scenarios
- Records calls
- Downloads MP3 recordings
- Transcribes recordings using Whisper
- Analyzes transcripts for bugs using an LLM
- Generates a bug report

## Setup

```bash
git clone <your-repo-url>
cd pgai-voice-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt