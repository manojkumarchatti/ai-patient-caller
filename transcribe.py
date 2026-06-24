import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

os.makedirs("transcripts", exist_ok=True)

for filename in os.listdir("recordings"):
    if not filename.endswith(".mp3"):
        continue

    audio_path = os.path.join("recordings", filename)

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    output_name = filename.replace(".mp3", ".txt")
    output_path = os.path.join("transcripts", output_name)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript.text)

    print("Transcribed:", output_path)