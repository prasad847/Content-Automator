from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq()


def transcribe_audio(file_path):
    """Transcribe a local audio file using Groq Whisper. Returns the text."""
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=audio_file
        )
    return transcription.text