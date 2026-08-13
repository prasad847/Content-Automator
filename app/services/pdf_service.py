import json
import os
from fpdf import FPDF

TYPE_LABELS = {
    "facebook_post": "Facebook Posts",
    "linkedin_post": "LinkedIn Posts",
    "x_post": "X (Twitter) Posts",
    "news_article": "News Article",
    "reel_idea": "Instagram Reel Ideas",
    "youtube_idea": "YouTube Video Ideas",
}


def _clean(text):
    """Strip characters the basic PDF font can't render, and break up unwrappable long words."""
    if not text:
        return ""
    text = str(text).encode("latin-1", "ignore").decode("latin-1")

    # Insert a space every 40 characters inside any "word" longer than that,
    # so fpdf can always wrap the line (prevents "not enough horizontal space" crashes)
    words = text.split(" ")
    fixed_words = []
    for word in words:
        if len(word) > 40:
            chunks = [word[i:i+40] for i in range(0, len(word), 40)]
            fixed_words.append(" ".join(chunks))
        else:
            fixed_words.append(word)
    return " ".join(fixed_words)


def _write_paragraph(pdf, text):
    """Write a paragraph safely, resetting cursor position first."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, _clean(text))


def generate_approved_content_pdf(job, items):
    """Build a PDF of all approved content items for a job. Returns raw PDF bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 10, _clean(f"Approved Content - {job.file_name}"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 8, _clean(f"Job #{job.id}"), ln=True)
    pdf.ln(5)

    items_by_type = {}
    for item in items:
        items_by_type.setdefault(item.content_type, []).append(item)

    for content_type, group in items_by_type.items():
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(80, 40, 150)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 10, _clean(TYPE_LABELS.get(content_type, content_type)), ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        for item in group:
            data = json.loads(item.content)

            pdf.set_font("Helvetica", "B", 11)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 8, _clean(f"#{item.item_index}"), ln=True)
            pdf.set_font("Helvetica", "", 10)

            if content_type == "news_article":
                pdf.set_font("Helvetica", "B", 10)
                _write_paragraph(pdf, data.get("headline", ""))
                pdf.set_font("Helvetica", "", 10)
                _write_paragraph(pdf, data.get("body", ""))

            elif content_type in ("facebook_post", "linkedin_post", "x_post"):
                _write_paragraph(pdf, data.get("text", ""))

            elif content_type == "reel_idea":
                _write_paragraph(pdf, f"Hook: {data.get('hook', '')}")
                _write_paragraph(pdf, f"Script: {data.get('script', '')}")
                _write_paragraph(pdf, "Scenes: " + " | ".join(data.get("scene_breakdown", [])))
                _write_paragraph(pdf, f"Caption: {data.get('caption', '')}")
                _write_paragraph(pdf, "Hashtags: " + " ".join(data.get("hashtags", [])))

            elif content_type == "youtube_idea":
                _write_paragraph(pdf, f"Title: {data.get('seo_title', '')}")
                _write_paragraph(pdf, f"Thumbnail idea: {data.get('thumbnail_idea', '')}")
                _write_paragraph(pdf, f"Script: {data.get('script', '')}")
                _write_paragraph(pdf, f"Description: {data.get('description', '')}")
                _write_paragraph(pdf, "Tags: " + " ".join(data.get("tags", [])))

            pdf.ln(4)

        pdf.ln(4)

    return bytes(pdf.output())


def generate_facebook_pdf(job, items):
    """Build a PDF of Facebook posts that have completed the full pipeline (post + hook +
    image all approved), including each post's hook and final image. Returns raw PDF bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 10, _clean(f"Approved Facebook Posts - {job.file_name}"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 8, _clean(f"Job #{job.id}"), ln=True)
    pdf.ln(5)

    for item in items:
        data = json.loads(item.content)

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(80, 40, 150)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 10, _clean(f"Post #{item.item_index}"), ln=True)
        pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", "B", 10)
        _write_paragraph(pdf, "Hook: " + (item.hook_content or "(none)"))
        pdf.set_font("Helvetica", "", 10)
        _write_paragraph(pdf, data.get("text", ""))

        image_path = item.final_image_path if (item.hook_on_image and item.final_image_path) else item.image_path
        if image_path and os.path.exists(image_path):
            pdf.ln(2)
            try:
                pdf.image(image_path, x=pdf.l_margin, w=100)
            except Exception:
                # Skip an unreadable/corrupt image rather than failing the whole PDF.
                pass

        pdf.ln(6)

    return bytes(pdf.output())