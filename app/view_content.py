import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from itertools import groupby
from db import get_all_jobs, get_content_items

TYPE_LABELS = {
    "facebook_post": "FACEBOOK POSTS",
    "linkedin_post": "LINKEDIN POSTS",
    "x_post": "X (TWITTER) POSTS",
    "news_article": "NEWS ARTICLE",
    "reel_idea": "INSTAGRAM REEL IDEAS",
    "youtube_idea": "YOUTUBE VIDEO IDEAS",
}


def print_job_content(job_id):
    items = get_content_items(job_id)

    if not items:
        print(f"No content found for job #{job_id}")
        return

    for content_type, group in groupby(items, key=lambda i: i.content_type):
        label = TYPE_LABELS.get(content_type, content_type)
        print("\n" + "=" * 60)
        print(label)
        print("=" * 60)

        for item in group:
            data = json.loads(item.content)
            print(f"\n--- #{item.item_index} (status: {item.status}) ---")

            if content_type == "news_article":
                print(f"HEADLINE: {data.get('headline')}\n")
                print(data.get("body"))

            elif content_type in ("facebook_post", "linkedin_post", "x_post"):
                print(data.get("text"))

            elif content_type == "reel_idea":
                print(f"Hook: {data.get('hook')}")
                print(f"Script: {data.get('script')}")
                print(f"Scenes: {data.get('scene_breakdown')}")
                print(f"Caption: {data.get('caption')}")
                print(f"Hashtags: {' '.join(data.get('hashtags', []))}")

            elif content_type == "youtube_idea":
                print(f"Title: {data.get('seo_title')}")
                print(f"Thumbnail idea: {data.get('thumbnail_idea')}")
                print(f"Script: {data.get('script')}")
                print(f"Description: {data.get('description')}")
                print(f"Tags: {' '.join(data.get('tags', []))}")


if __name__ == "__main__":
    jobs = get_all_jobs()
    print("Available jobs:")
    for job in jobs:
        print(f"  #{job.id} — {job.file_name} ({job.status})")

    job_id = int(input("\nEnter job ID to view: "))
    print_job_content(job_id)