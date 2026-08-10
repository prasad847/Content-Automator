import os
import time
import requests
from urllib.parse import quote

IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_images")
os.makedirs(IMAGE_DIR, exist_ok=True)


def generate_image(post_text, hook_text=None, feedback=None):
    """Generate a supporting visual for an approved post/hook. Returns the local file path."""

    base_instruction = (
        "Clean, modern social media graphic. Flat design, simple, high contrast, no clutter. "
        "Do NOT render large blocks of text - at most a short 3-6 word phrase, or no text at all, "
        "just a strong supporting visual/illustration matching the theme below."
    )

    theme_parts = []
    if hook_text:
        theme_parts.append("Theme: " + hook_text)
    else:
        theme_parts.append("Theme: " + post_text[:150])
    if feedback:
        theme_parts.append("Style notes: " + feedback)

    prompt = base_instruction + " " + " | ".join(theme_parts)
    encoded_prompt = quote(prompt)

    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    filename = f"image_{int(time.time() * 1000)}.png"
    file_path = os.path.join(IMAGE_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(response.content)

    return file_path