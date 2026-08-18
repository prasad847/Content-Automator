import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq()
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = (
    "You are a social media content strategist. You will be given a transcript "
    "of a talk or podcast episode. Generate content based ONLY on what's actually "
    "said in the transcript - don't invent facts, names, or statistics not present "
    "in it. Respond with ONLY valid JSON. No markdown formatting, no code fences, "
    "no explanation or preamble - just the raw JSON object."
)


def _call_model(user_prompt):
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4000,
        temperature=1.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


def _parse_json(raw_text):
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
    return json.loads(cleaned)


def _call_model_with_retry(prompt, max_attempts=3):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        raw_text = _call_model(prompt)
        try:
            return _parse_json(raw_text)
        except json.JSONDecodeError as e:
            last_error = e
            print(f"    (attempt {attempt}/{max_attempts}) JSON parse failed, retrying...")
    raise last_error


def _instruction_note(instructions):
    """Build a prompt fragment from optional client instructions."""
    if not instructions:
        return ""
    return (
        "\n\nSPECIFIC INSTRUCTIONS FROM THE CLIENT (follow these precisely - "
        "e.g. tone, category ratios, focus areas): " + instructions
    )


def generate_facebook_posts(transcript_text, instructions=None):
    prompt = (
        "Based on this transcript, write 5 completely distinct Facebook posts. "
        "Each MUST use a different angle - for example: "
        "1) a bold opinion/hot take, 2) a personal story or anecdote style, "
        "3) a practical tip or how-to, 4) a question that sparks discussion, "
        "5) a surprising fact or statistic from the transcript. "
        "Do not reuse the same opening line or sentence structure across posts. "
        "Conversational, 80-150 words each."
        + _instruction_note(instructions) +
        "\n\nTranscript:\n" + transcript_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"posts": [{"text": "..."}, {"text": "..."}, {"text": "..."}, {"text": "..."}, {"text": "..."}]}'
    )
    result = _call_model_with_retry(prompt)
    return result.get("posts", [])


def generate_linkedin_posts(transcript_text, instructions=None):
    prompt = (
        "Based on this transcript, write 5 distinct LinkedIn posts. "
        "Professional tone, insight-driven, 100-200 words, ending with a question to engage readers."
        + _instruction_note(instructions) +
        "\n\nTranscript:\n" + transcript_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"posts": [{"text": "..."}, {"text": "..."}, {"text": "..."}, {"text": "..."}, {"text": "..."}]}'
    )
    result = _call_model_with_retry(prompt)
    return result.get("posts", [])


def generate_x_posts(transcript_text, instructions=None):
    prompt = (
        "Based on this transcript, write 5 completely distinct X (Twitter) posts. "
        "Each MUST use a different style - for example: "
        "1) a bold one-liner, 2) a mini-thread style with a colon and list, "
        "3) a question, 4) a contrarian take, 5) a quote-style insight from the talk. "
        "Do not reuse the same opening words or structure across posts. "
        "Each under 280 characters, punchy."
        + _instruction_note(instructions) +
        "\n\nTranscript:\n" + transcript_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"posts": [{"text": "..."}, {"text": "..."}, {"text": "..."}, {"text": "..."}, {"text": "..."}]}'
    )
    result = _call_model_with_retry(prompt)
    return result.get("posts", [])


def generate_news_article(transcript_text, instructions=None):
    prompt = (
        "Based on this transcript, write 1 news-style article summarizing "
        "the key points. Third person, 300-500 words, include a headline."
        + _instruction_note(instructions) +
        "\n\nTranscript:\n" + transcript_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"headline": "...", "body": "..."}'
    )
    result = _call_model_with_retry(prompt)
    return [result]


def generate_reel_ideas(transcript_text, instructions=None):
    prompt = (
        "Based on this transcript, generate exactly 5 Instagram Reel ideas. "
        "Each needs: a hook (first 3 seconds), a complete script, a scene-by-scene "
        "breakdown, a caption, and 8-10 hashtags."
        + _instruction_note(instructions) +
        "\n\nTranscript:\n" + transcript_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"reels": [{"hook": "...", "script": "...", "scene_breakdown": ["Scene 1: ...", "Scene 2: ..."], "caption": "...", "hashtags": ["#tag1", "#tag2"]}]}\n'
        '(Provide exactly 5 items in the "reels" array.)'
    )
    result = _call_model_with_retry(prompt)
    return result.get("reels", [])


def generate_youtube_ideas(transcript_text, instructions=None):
    prompt = (
        "Based on this transcript, generate exactly 5 YouTube video ideas. "
        "Each needs: an SEO-optimized title, a thumbnail idea (visual description), a "
        "complete script, a video description, and 8-10 tags."
        + _instruction_note(instructions) +
        "\n\nTranscript:\n" + transcript_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"videos": [{"seo_title": "...", "thumbnail_idea": "...", "script": "...", "description": "...", "tags": ["tag1", "tag2"]}]}\n'
        '(Provide exactly 5 items in the "videos" array.)'
    )
    result = _call_model_with_retry(prompt)
    return result.get("videos", [])


def regenerate_single_item(content_type, transcript_text, previous_text=None, instructions=None):
    avoid_repeat_note = ""
    if previous_text:
        avoid_repeat_note = (
            "\n\nIMPORTANT: The previous version was:\n\"" + previous_text + "\"\n"
            "Write something meaningfully different - a different angle, opening line, "
            "and structure. Do not just tweak a few words."
        )

    note = _instruction_note(instructions) + avoid_repeat_note

    prompts = {
        "facebook_post": (
            "Based on this transcript, write 1 Facebook post. "
            "Conversational, 80-150 words." + note +
            "\n\nTranscript:\n" + transcript_text +
            "\n\nRespond with ONLY this JSON structure:\n"
            '{"text": "..."}'
        ),
        "linkedin_post": (
            "Based on this transcript, write 1 LinkedIn post. "
            "Professional tone, insight-driven, 100-200 words, ending with a question." + note +
            "\n\nTranscript:\n" + transcript_text +
            "\n\nRespond with ONLY this JSON structure:\n"
            '{"text": "..."}'
        ),
        "x_post": (
            "Based on this transcript, write 1 X (Twitter) post. "
            "Under 280 characters, punchy, one specific idea." + note +
            "\n\nTranscript:\n" + transcript_text +
            "\n\nRespond with ONLY this JSON structure:\n"
            '{"text": "..."}'
        ),
        "news_article": (
            "Based on this transcript, write 1 news-style article. "
            "Third person, 300-500 words, include a headline." + note +
            "\n\nTranscript:\n" + transcript_text +
            "\n\nRespond with ONLY this JSON structure:\n"
            '{"headline": "...", "body": "..."}'
        ),
        "reel_idea": (
            "Based on this transcript, generate 1 Instagram Reel idea with a hook, "
            "a complete script, a scene-by-scene breakdown, a caption, and 8-10 hashtags." + note +
            "\n\nTranscript:\n" + transcript_text +
            "\n\nRespond with ONLY this JSON structure:\n"
            '{"hook": "...", "script": "...", "scene_breakdown": ["Scene 1: ...", "Scene 2: ..."], "caption": "...", "hashtags": ["#tag1", "#tag2"]}'
        ),
        "youtube_idea": (
            "Based on this transcript, generate 1 YouTube video idea with an SEO title, "
            "a thumbnail idea, a complete script, a description, and 8-10 tags." + note +
            "\n\nTranscript:\n" + transcript_text +
            "\n\nRespond with ONLY this JSON structure:\n"
            '{"seo_title": "...", "thumbnail_idea": "...", "script": "...", "description": "...", "tags": ["tag1", "tag2"]}'
        ),
    }

    prompt = prompts.get(content_type)
    if not prompt:
        raise ValueError(f"Unknown content_type: {content_type}")

    return _call_model_with_retry(prompt)


def generate_hook(approved_post_text, instructions=None, previous_hook=None):
    """Generate a short, scroll-stopping hook line for an already-approved post."""
    note = _instruction_note(instructions)

    avoid_repeat_note = ""
    if previous_hook:
        avoid_repeat_note = (
            "\n\nIMPORTANT: The previous hook was: \"" + previous_hook + "\"\n"
            "Write a genuinely different hook - different angle, different opening word, "
            "different structure (e.g. switch between a question, a bold statement, a number/stat, "
            "or a curiosity gap). Do not just reorder or swap a word or two."
        )

    prompt = (
        "Based on this approved social media post, write ONE short, scroll-stopping "
        "hook line (under 15 words) that could be used as an opening line, headline, "
        "or attention-grabber to accompany this post."
        + note + avoid_repeat_note +
        "\n\nApproved post:\n" + approved_post_text + "\n\n"
        "Respond with ONLY this JSON structure:\n"
        '{"hook": "..."}'
    )
    result = _call_model_with_retry(prompt)
    return result.get("hook", "")