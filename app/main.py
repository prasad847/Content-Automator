from dotenv import load_dotenv
from groq import Groq
from services.drive_service import list_new_audio_files, download_file, save_processed_id
from services.content_service import (
    generate_facebook_posts, generate_linkedin_posts, generate_x_posts,
    generate_news_article, generate_reel_ideas, generate_youtube_ideas
)
from db import create_job, save_transcript, save_content_items, update_job_status, log_event
from services.transcription_service import transcribe_audio

load_dotenv()

client = Groq()


# def transcribe_audio(file_path):
#     with open(file_path, "rb") as audio_file:
#         transcription = client.audio.transcriptions.create(
#             model="whisper-large-v3-turbo",
#             file=audio_file
#         )
#     return transcription.text



def main():
    new_files = list_new_audio_files()

    if not new_files:
        print("No new files found.")
        return

    for file in new_files:
        print(f"Found new file: {file['name']}")

        job = create_job(drive_file_id=file["id"], file_name=file["name"])
        print(f"Created job #{job.id}")

        local_path = download_file(file["id"], file["name"])
        print(f"Downloaded to: {local_path}")

        print("Transcribing...")
        try:
            text = transcribe_audio(local_path)
            save_transcript(job.id, text)
            log_event(job.id, "transcription", "success")
            print(f"Job #{job.id} saved with status 'transcribed'")
        except Exception as e:
            log_event(job.id, "transcription", "failed", str(e))
            print(f"Transcription FAILED: {e}")
            save_processed_id(file["id"])
            continue  # skip this file entirely, move to the next one

        print("Generating content...")
        update_job_status(job.id, "generating")

        content_generators = [
            ("facebook_post", generate_facebook_posts),
            ("linkedin_post", generate_linkedin_posts),
            ("x_post", generate_x_posts),
            ("news_article", generate_news_article),
            ("reel_idea", generate_reel_ideas),
            ("youtube_idea", generate_youtube_ideas),
        ]

        for content_type, generator_function in content_generators:
            try:
                result = generator_function(text)
                save_content_items(job.id, content_type, result)
                log_event(job.id, content_type, "success")
                print(f"  {content_type} done")
            except Exception as e:
                log_event(job.id, content_type, "failed", str(e))
                print(f"  {content_type} FAILED: {e}")

        update_job_status(job.id, "awaiting_approval")
        print(f"Job #{job.id} complete — awaiting approval")

        save_processed_id(file["id"])


if __name__ == "__main__":
    main()