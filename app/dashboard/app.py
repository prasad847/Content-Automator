import sys
import os
import json
from datetime import datetime, date, time as dtime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(
    page_title="Content Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)
from services.transcription_service import transcribe_audio
from services.content_service import (
    regenerate_single_item, generate_hook,
    generate_facebook_posts, generate_linkedin_posts, generate_x_posts,
    generate_news_article, generate_reel_ideas, generate_youtube_ideas
)
from services.image_service import generate_image
from services.image_compose_service import compose_hook_on_image
from services.pdf_service import generate_approved_content_pdf, generate_facebook_pdf
from services.publisher_service import publish_facebook_item
from services.scheduler_service import start_scheduler
from db import (
    get_all_jobs, get_transcript_text, get_content_items,
    update_content_item_status, update_content_item_text,
    update_content_item_schedule, regenerate_content_item, get_approved_items,
    approve_post_and_advance, save_hook, approve_hook_and_advance,
    save_image, approve_image_and_complete, update_publish_flags,
    save_final_composition, approve_final, approve_and_schedule, cancel_schedule,
    mark_content_item_failed,
    create_job, save_transcript, save_content_items, update_job_status, log_event,
    reset_and_regenerate_item
)

start_scheduler()

css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploaded_audio")
os.makedirs(STORAGE_DIR, exist_ok=True)

STAGED_TYPES = ("facebook_post", "linkedin_post", "x_post")

PLATFORM_META = {
    "facebook_post": {"label": "Facebook", "color": "#1877F2", "icon": "📘"},
    "linkedin_post": {"label": "LinkedIn", "color": "#0A66C2", "icon": "💼"},
    "x_post": {"label": "X (Twitter)", "color": "#111111", "icon": "✖️"},
    "news_article": {"label": "News Article", "color": "#4B5563", "icon": "📰"},
    "reel_idea": {"label": "Instagram Reels", "color": "#C13584", "icon": "📸"},
    "youtube_idea": {"label": "YouTube", "color": "#FF0000", "icon": "▶️"},
}

STAGE_STEPS = ["Post", "Hook", "Image", "Done"]


def badge(text, kind):
    return f'<span class="badge badge-{kind}">{text}</span>'


def save_audio_locally(uploaded_file):
    dest_path = os.path.join(STORAGE_DIR, uploaded_file.name)
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    return dest_path


def render_stage_tracker(current_stage):
    stage_order = {"post": 0, "hook": 1, "image": 2, "complete": 3}
    current_index = stage_order.get(current_stage, 0)
    cols = st.columns(4)
    for i, step_name in enumerate(STAGE_STEPS):
        with cols[i]:
            if i < current_index:
                st.markdown(f"✅ **{step_name}**")
            elif i == current_index:
                st.markdown(f"🟣 **{step_name}**")
            else:
                st.markdown(f"⚪ {step_name}")


def render_accept_regenerate_edit(item_id, current_value, on_save, on_regenerate, on_accept,
                                   height=100, area_label="Content", show_instructions=False,
                                   instructions_placeholder=""):
    """Generic 3-button pattern: Accept (green) / Regenerate (purple) / Edit -> Save & Accept (blue).

    If show_instructions is True, an optional instructions box is rendered above the button
    row, and its value (or "" if left blank) is passed to on_regenerate so the same Regenerate
    button covers both "regenerate as-is" and "regenerate with instructions"."""
    editing_key = f"editing_{item_id}"
    if editing_key not in st.session_state:
        st.session_state[editing_key] = False

    if not st.session_state[editing_key]:
        st.write(current_value)
        instructions = ""
        if show_instructions:
            instructions = st.text_area(
                "Instructions for regeneration (optional)",
                placeholder=instructions_placeholder,
                key=f"instructions_{item_id}", height=70
            )
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(key=f"accept-btn-{item_id}"):
                if st.button("Accept", key=f"acceptbtn_{item_id}", use_container_width=True):
                    on_accept()
                    st.rerun()
        with c2:
            with st.container(key=f"regen-btn-{item_id}"):
                if st.button("Regenerate", key=f"regenbtn_{item_id}", use_container_width=True):
                    if show_instructions:
                        on_regenerate(instructions)
                    else:
                        on_regenerate()
                    st.rerun()
        with c3:
            if st.button("Edit", key=f"editbtn_{item_id}", use_container_width=True):
                st.session_state[editing_key] = True
                st.rerun()
    else:
        new_value = st.text_area(area_label, value=current_value, height=height, key=f"editarea_{item_id}")
        with st.container(key=f"edit-btn-{item_id}"):
            if st.button("Save & Accept", key=f"saveacceptbtn_{item_id}", use_container_width=True):
                on_save(new_value)
                on_accept()
                st.session_state[editing_key] = False
                st.rerun()


# ============ TOP ROW: upload / instructions / job select (bordered, equal-height boxes) ============
jobs = get_all_jobs()
job_labels = [f"Job #{job.id} — {job.file_name} ({job.status})" for job in jobs] if jobs else []

col_upload, col_instructions, col_jobselect = st.columns(
    [1.3, 2.2, 1.5],
    gap="medium"
)

with col_upload:
    with st.container(border=True, key="topbox-audio"):
        st.markdown("**🎙️ Content audio**")
        content_audio = st.file_uploader("Content audio", type=["mp3", "wav", "m4a"],
                                          key="content_audio", label_visibility="collapsed")
        

with col_instructions:
    with st.container(border=True, key="topbox-instructions"):
        st.markdown("**📝 Instructions**")
        instructions_text_input = st.text_area("Instructions", key="instructions_text_input",
                                                height=90, label_visibility="collapsed",
                                                placeholder="e.g. 3 educational, 2 motivational")

with col_jobselect:
    with st.container(border=True, key="topbox-job"):
        st.markdown("**📂 Job**")
        if jobs:
            selected_label = st.selectbox("Select a job", job_labels, label_visibility="collapsed")
            selected_job = jobs[job_labels.index(selected_label)]
        else:
            st.caption("No jobs yet.")
            selected_job = None

if content_audio is not None:
    if st.button("⚡ Process this upload", type="primary"):
        instructions_text = instructions_text_input.strip() if instructions_text_input else None

        with st.spinner("Saving and transcribing..."):
            content_local_path = save_audio_locally(content_audio)
            drive_file_id = "local_" + content_audio.name
            job = create_job(drive_file_id=drive_file_id, file_name=content_audio.name, instructions=instructions_text)

            try:
                text = transcribe_audio(content_local_path)
                save_transcript(job.id, text)
                log_event(job.id, "transcription", "success")
            except Exception as e:
                log_event(job.id, "transcription", "failed", str(e))
                st.error(f"Transcription failed: {e}")
                st.stop()

        update_job_status(job.id, "generating")
        content_generators = [
            ("facebook_post", generate_facebook_posts),
            ("linkedin_post", generate_linkedin_posts),
            ("x_post", generate_x_posts),
            ("news_article", generate_news_article),
            ("reel_idea", generate_reel_ideas),
            ("youtube_idea", generate_youtube_ideas),
        ]
        progress = st.progress(0)
        for i, (content_type, generator_function) in enumerate(content_generators):
            try:
                result = generator_function(text, instructions=instructions_text)
                save_content_items(job.id, content_type, result)
                log_event(job.id, content_type, "success")
            except Exception as e:
                log_event(job.id, content_type, "failed", str(e))
            progress.progress((i + 1) / len(content_generators))

        update_job_status(job.id, "awaiting_approval")
        st.success(f"Job #{job.id} complete! Select it above to review.")
        st.rerun()

if not jobs:
    st.stop()

st.divider()

# ============ Transcript + PDF button side by side ============
col_transcript, col_pdf_btn = st.columns(
    [7, 1],
    gap="small"
)
with col_transcript:
    with st.expander("View transcript"):
        transcript_text = get_transcript_text(selected_job.id)
        st.write(transcript_text if transcript_text else "No transcript yet.")

with col_pdf_btn:
    approved_items = get_approved_items(selected_job.id)
    if approved_items:
        pdf_bytes = generate_approved_content_pdf(selected_job, approved_items)
        with st.container(key="pdf-download-btn"):
            st.download_button(f"📄 PDF ({len(approved_items)})", data=pdf_bytes,
                                file_name=f"job_{selected_job.id}_approved_content.pdf",
                                mime="application/pdf", use_container_width=True)
    else:
        st.caption("No approved items yet")

content_items = get_content_items(selected_job.id)
if not content_items:
    st.warning("No content generated yet for this job.")
    st.stop()

items_by_type = {}
for item in content_items:
    items_by_type.setdefault(item.content_type, []).append(item)

content_types_present = list(items_by_type.keys())
tab_labels = [f"{PLATFORM_META.get(ct, {}).get('icon', '')} {PLATFORM_META.get(ct, {}).get('label', ct)}"
              for ct in content_types_present]
tabs = st.tabs(tab_labels)
transcript_text = get_transcript_text(selected_job.id)


def render_tab(content_type, items):
    meta = PLATFORM_META.get(content_type, {"label": content_type, "color": "#666666", "icon": "📄"})
    st.markdown(
        f"<div class='platform-banner' style='background:{meta['color']}1A; color:{meta['color']};'>"
        f"{meta['icon']} {meta['label']}</div>",
        unsafe_allow_html=True
    )

    if content_type == "facebook_post":
        complete_items = [i for i in items if i.stage == "complete"]
        if complete_items:
            fb_pdf_bytes = generate_facebook_pdf(selected_job, complete_items)
            with st.container(key="fb-pdf-download-btn"):
                st.download_button(
                    f"📄 Download Facebook PDF ({len(complete_items)}) - posts, hooks & images",
                    data=fb_pdf_bytes,
                    file_name=f"job_{selected_job.id}_facebook_posts.pdf",
                    mime="application/pdf",
                )
        else:
            st.caption("No fully approved Facebook posts yet (post + hook + image) to export.")

    list_col, detail_col, schedule_col = st.columns([0.9, 3.4, 1.1],gap="medium")

    # Tracked by item_index (stable across regeneration) rather than item.id, because
    # regenerate_content_item() deletes the old row and inserts a new one with a new id -
    # tracking by id would silently snap the selection back to Post 1 on every regenerate.
    selection_key = f"selected_item_{content_type}"
    if selection_key not in st.session_state:
        st.session_state[selection_key] = items[0].item_index

    with list_col:
        for item in items:
            is_selected = st.session_state[selection_key] == item.item_index
            with st.container(border=True):
                status_kind = "approved" if item.status == "approved" else "draft"
                if content_type in STAGED_TYPES and item.stage == "complete":
                    status_kind = "complete"
                st.markdown(
                    f"<span class='post-title'>Post {item.item_index}</span> {badge(item.status, status_kind)}",
                    unsafe_allow_html=True
                )
                if content_type in STAGED_TYPES:
                    st.caption(f"Stage: {item.stage}")
                if item.scheduled_at:
                    st.caption(f"📅 {item.scheduled_at.strftime('%b %d, %I:%M %p')}")
                with st.container(key=f"selectbtn-wrap-{item.id}"):
                    if st.button("Select", key=f"pick_{item.id}", type="primary" if is_selected else "secondary",
                                 use_container_width=True):
                        st.session_state[selection_key] = item.item_index
                        st.rerun()

    selected_item = next((i for i in items if i.item_index == st.session_state[selection_key]), items[0])
    data = json.loads(selected_item.content)

    with detail_col:
        with st.container(border=True):
            st.markdown(
                f"<span class='post-title'>Post {selected_item.item_index}</span> "
                f"<span class='post-version'>v{selected_item.version}</span>",
                unsafe_allow_html=True
            )
            if content_type in STAGED_TYPES:
                render_stage_tracker(selected_item.stage)
                st.divider()
                render_staged_detail(selected_item, content_type, data)
            else:
                render_simple_detail(selected_item, content_type, data)

    with schedule_col:
        with st.container(border=True):
            st.markdown("**Schedule**")
            is_ready = (content_type not in STAGED_TYPES and selected_item.status == "approved") or \
                       (content_type in STAGED_TYPES and selected_item.stage == "complete")

            if not is_ready:
                st.caption("Complete approval to enable scheduling.")
            else:
                existing_date = selected_item.scheduled_at.date() if selected_item.scheduled_at else date.today()
                existing_time = selected_item.scheduled_at.time() if selected_item.scheduled_at else dtime(9, 0)
                picked_date = st.date_input("Date", value=existing_date, key=f"sched_date_{selected_item.id}")
                picked_time = st.time_input("Time", value=existing_time, key=f"sched_time_{selected_item.id}")

                combo = (True, False, False)
                if content_type in STAGED_TYPES:
                    st.caption("Publish with:")
                    preset = st.radio("Publish combination",
                                       ["Post only", "Post + Hook", "Post + Image", "Post + Hook + Image"],
                                       key=f"preset_{selected_item.id}", label_visibility="collapsed")
                    combo = {
                        "Post only": (True, False, False),
                        "Post + Hook": (True, True, False),
                        "Post + Image": (True, False, True),
                        "Post + Hook + Image": (True, True, True),
                    }[preset]

                if st.button("Save schedule", type="primary", key=f"save_sched_{selected_item.id}"):
                    scheduled_datetime = datetime.combine(picked_date, picked_time)
                    update_content_item_schedule(selected_item.id, scheduled_datetime)
                    if content_type in STAGED_TYPES:
                        update_publish_flags(selected_item.id, *combo)
                    st.success("Saved.")
                    st.rerun()


def render_staged_detail(item, content_type, data):
    reset_confirm_key = f"confirm_reset_{item.id}"
    if st.session_state.get(reset_confirm_key):
        st.warning(
            "This discards this post's current text, hook, and image, and generates a "
            "brand new post in its place. This cannot be undone. Continue?"
        )
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("Yes, reset this post", key=f"reset_yes_{item.id}", type="primary", use_container_width=True):
                with st.spinner("Generating a new post..."):
                    new_content = regenerate_single_item(content_type, transcript_text)
                    reset_and_regenerate_item(item.id, new_content)
                st.session_state[reset_confirm_key] = False
                st.rerun()
        with rc2:
            if st.button("Cancel", key=f"reset_cancel_{item.id}", use_container_width=True):
                st.session_state[reset_confirm_key] = False
                st.rerun()
    else:
        with st.container(key=f"reset-btn-wrap-{item.id}"):
            if st.button("🔄 Reset Post", key=f"reset_btn_{item.id}"):
                st.session_state[reset_confirm_key] = True
                st.rerun()
    st.divider()

    if item.stage == "post":
        render_accept_regenerate_edit(
            item_id=f"post_{item.id}",
            current_value=data.get("text", ""),
            on_save=lambda new_val: update_content_item_text(item.id, {"text": new_val}),
            on_regenerate=lambda: regenerate_content_item(
                item.id, regenerate_single_item(content_type, transcript_text, previous_text=data.get("text", ""))
            ),
            on_accept=lambda: approve_post_and_advance(item.id),
            height=100, area_label="Post text"
        )

    elif item.stage == "hook":
        st.text_area("Approved post", value=data.get("text", ""), height=80, disabled=True, key=f"locked_text_{item.id}")

        if not item.hook_content:
            initial_hook_instructions = st.text_area(
                "Instructions for the hook (optional)",
                placeholder="Tell the AI what tone or angle you want. Example: curiosity-driven, "
                            "focus on the biggest takeaway, keep it under 8 words. Leave blank for a "
                            "default hook.",
                key=f"initial_hook_instructions_{item.id}", height=70
            )
            if st.button("Generate hook", key=f"gen_hook_{item.id}"):
                with st.spinner("Generating hook..."):
                    try:
                        hook_text = generate_hook(data.get("text", ""), instructions=initial_hook_instructions or None)
                        save_hook(item.id, hook_text)
                    except Exception as e:
                        st.error("Hook generation failed. Try again.")
                        with st.expander("Technical details"):
                            st.code(str(e))
                        st.stop()
                st.rerun()
        else:
            st.caption(f"Version {item.hook_version}")

            def regenerate_hook(instructions):
                with st.spinner("Regenerating hook..."):
                    try:
                        new_hook = generate_hook(data.get("text", ""), instructions=instructions or None,
                                                  previous_hook=item.hook_content)
                        save_hook(item.id, new_hook)
                    except Exception as e:
                        st.error("Hook generation failed. Try again.")
                        with st.expander("Technical details"):
                            st.code(str(e))
                        st.stop()

            render_accept_regenerate_edit(
                item_id=f"hook_{item.id}",
                current_value=item.hook_content,
                on_save=lambda new_val: save_hook(item.id, new_val),
                on_regenerate=regenerate_hook,
                on_accept=lambda: approve_hook_and_advance(item.id),
                height=60, area_label="Hook",
                show_instructions=True,
                instructions_placeholder="Tell the AI what you want changed. Example: Make it more "
                                          "emotional, shorter, more curiosity-driven, or professional. "
                                          "Leave blank to regenerate as-is."
            )

    elif item.stage == "image":
        st.text_area("Approved post", value=data.get("text", ""), height=80, disabled=True, key=f"locked_text_{item.id}")
        st.text_area("Approved hook", value=item.hook_content or "", height=50, disabled=True, key=f"locked_hook_{item.id}")

        if not item.image_path:
            initial_image_instructions = st.text_area(
                "Instructions for the image (optional)",
                placeholder="Tell the AI what you want. Example: dark background, show a laptop, "
                            "minimalist style. Leave blank for a default image.",
                key=f"initial_img_instructions_{item.id}", height=70
            )
            if st.button("Generate image", key=f"gen_img_{item.id}"):
                with st.spinner("Generating image..."):
                    try:
                        image_path = generate_image(data.get("text", ""), item.hook_content,
                                                      initial_image_instructions or None)
                        save_image(item.id, image_path)
                    except Exception as e:
                        st.error("Image generation failed. Try again or modify your instructions.")
                        with st.expander("Technical details"):
                            st.code(str(e))
                        st.stop()
                st.rerun()
        else:
            st.caption(f"Version {item.image_version}")
            st.image(item.image_path, width=280)

            img_instructions_key = f"img_instructions_{item.id}"
            img_instructions_reset_key = f"{img_instructions_key}_reset"
            # Widget values can't be written after the widget's been instantiated this run,
            # so a pending clear from the previous run is applied here, before the text_area
            # below is created.
            if st.session_state.get(img_instructions_reset_key):
                st.session_state[img_instructions_key] = ""
                st.session_state[img_instructions_reset_key] = False

            image_instructions = st.text_area(
                "Instructions for image regeneration (optional)",
                placeholder="Tell the AI what you want changed. Example: Make it more professional, "
                            "use a darker background, show a person working on a laptop, remove "
                            "unnecessary objects, make it more realistic. Leave blank to regenerate as-is.",
                key=img_instructions_key, height=70
            )

            c1, c2 = st.columns(2)
            with c1:
                with st.container(key=f"regen-btn-img-{item.id}"):
                    if st.button("Regenerate", key=f"regen_img_{item.id}", use_container_width=True):
                        with st.spinner("Regenerating image..."):
                            try:
                                image_path = generate_image(data.get("text", ""), item.hook_content,
                                                              image_instructions or None)
                                save_image(item.id, image_path)
                            except Exception as e:
                                st.error("Image generation failed. Try again or modify your instructions.")
                                with st.expander("Technical details"):
                                    st.code(str(e))
                                st.stop()
                        st.session_state[img_instructions_reset_key] = True
                        st.rerun()
            with c2:
                with st.container(key=f"accept-btn-img-{item.id}"):
                    if st.button("Accept Image", key=f"approve_img_{item.id}", use_container_width=True):
                        approve_image_and_complete(item.id)
                        st.rerun()

    elif item.stage == "complete":
        st.text_area("Final post", value=data.get("text", ""), height=80, disabled=True, key=f"final_text_{item.id}")
        st.text_area("Final hook", value=item.hook_content or "", height=50, disabled=True, key=f"final_hook_{item.id}")
        st.success("Hook and image both approved.")

        st.divider()
        st.markdown("#### Publish with")

        publish_mode = st.radio(
            "Choose how the post should look when published",
            ["Post + Hook on Image", "Post + Image", "Only Post"],
            index=0 if item.hook_on_image else 1,
            key=f"publish_mode_{item.id}"
        )
        want_hook_on_image = publish_mode == "Post + Hook on Image"
        want_text_only = publish_mode == "Only Post"

        if want_hook_on_image != item.hook_on_image:
            save_final_composition(item.id, item.final_image_path, want_hook_on_image)
            st.rerun()

        if want_hook_on_image:
            if item.final_image_path:
                st.markdown("**Preview: hook on image**")
                st.image(item.final_image_path, width=320)
            else:
                st.info("Not composed yet. Generate a preview of the hook placed on the image below.")
                if item.image_path:
                    st.image(item.image_path, width=320)

            compose_instructions = st.text_area(
                "Instructions for hook + image",
                placeholder="Put the hook at the top, use large bold text, keep the person visible, "
                            "use a clean professional layout.",
                key=f"compose_instructions_{item.id}", height=70
            )
            if st.button("Generate Hook + Image", key=f"compose_btn_{item.id}"):
                with st.spinner("Placing hook on image..."):
                    try:
                        composed_path = compose_hook_on_image(item.image_path, item.hook_content, compose_instructions)
                        save_final_composition(item.id, composed_path, True)
                    except Exception as e:
                        st.error("Could not place the hook on the image. Try again or adjust your instructions.")
                        with st.expander("Technical details"):
                            st.code(str(e))
                        st.stop()
                st.rerun()
        elif want_text_only:
            st.markdown("**Preview: post text only**")
            st.caption("No hook or image will be published - only the post text.")
        else:
            st.markdown("**Preview: image only**")
            if item.image_path:
                st.image(item.image_path, width=320)

        st.divider()
        st.markdown("#### Final Approval")
        st.markdown(f"**Hook:** {item.hook_content or '(none)'}")
        st.markdown(f"**Post:** {data.get('text', '')}")

        publish_image = None if want_text_only else (
            item.final_image_path if (want_hook_on_image and item.final_image_path) else item.image_path
        )
        publish_blocked = want_hook_on_image and not item.final_image_path

        if item.final_status == "published":
            st.success("✅ Successfully published to Facebook.")
        elif item.final_status == "scheduled":
            when_str = item.scheduled_at.strftime("%b %d, %Y at %I:%M %p") if item.scheduled_at else "an unset time"
            st.info(f"📅 Approved and scheduled - will publish automatically on {when_str}.")
            with st.container(key=f"cancel-schedule-btn-{item.id}"):
                if st.button("Cancel schedule", key=f"cancel_schedule_{item.id}"):
                    cancel_schedule(item.id)
                    st.rerun()
        else:
            if item.final_status == "final_approved":
                st.info("✅ Approved - ready to publish or schedule.")
            st.caption("Approving is your explicit sign-off on this final version.")

            schedule_open_key = f"show_schedule_picker_{item.id}"
            if schedule_open_key not in st.session_state:
                st.session_state[schedule_open_key] = False

            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                if content_type == "facebook_post":
                    if st.button("🚀 Approve & Publish Now", key=f"publish_now_{item.id}",
                                 type="primary", disabled=publish_blocked, use_container_width=True):
                        with st.spinner("Publishing to Facebook..."):
                            approve_final(item.id)
                            # Hook text is never duplicated as a separate caption - it's either
                            # burned into the image (hook-on-image mode) or left off entirely.
                            update_publish_flags(item.id, True, False, bool(publish_image))
                            # item is the in-memory object loaded before this click; update_publish_flags
                            # wrote to the DB via its own session, so mirror those flags here too or
                            # publish_facebook_item would read the stale pre-click values off `item`.
                            item.publish_include_text = True
                            item.publish_include_hook = False
                            item.publish_include_image = bool(publish_image)
                            item.hook_on_image = want_hook_on_image
                            try:
                                post_url = publish_facebook_item(item)
                                st.success("Successfully published to Facebook.")
                                st.markdown(f"[View post]({post_url})")
                            except Exception as e:
                                mark_content_item_failed(item.id, str(e))
                                st.error("Facebook publishing failed.")
                                with st.expander("Technical details"):
                                    st.code(str(e))
                        st.rerun()
                    if publish_blocked:
                        st.caption("Generate the hook + image preview above first.")
            with pc2:
                with st.container(key=f"edit-btn-schedule-{item.id}"):
                    if st.button("📅 Approve & Schedule Date & Time", key=f"schedule_toggle_{item.id}",
                                 disabled=publish_blocked, use_container_width=True):
                        st.session_state[schedule_open_key] = not st.session_state[schedule_open_key]
                        st.rerun()
                if publish_blocked:
                    st.caption("Generate the hook + image preview above first.")
            with pc3:
                # Placeholder only - group scheduling isn't implemented yet.
                if st.button("🗓️ Schedule in Group", key=f"schedule_group_{item.id}", use_container_width=True):
                    st.info("Scheduling in a group is coming soon.")

            if st.session_state[schedule_open_key]:
                st.markdown("###### Choose when to publish")
                sc1, sc2, sc3, sc4 = st.columns([2, 2, 1, 1])
                with sc1:
                    sched_date = st.date_input("Date", value=date.today(), min_value=date.today(),
                                                key=f"final_sched_date_{item.id}")
                with sc2:
                    sched_time = st.time_input("Time", value=dtime(9, 0), key=f"final_sched_time_{item.id}")
                with sc3:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    if st.button("Confirm", key=f"confirm_schedule_{item.id}", type="primary", use_container_width=True):
                        scheduled_dt = datetime.combine(sched_date, sched_time)
                        approve_and_schedule(item.id, scheduled_dt)
                        update_publish_flags(item.id, True, False, bool(publish_image))
                        st.session_state[schedule_open_key] = False
                        st.rerun()
                with sc4:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    if st.button("Cancel", key=f"cancel_schedule_picker_{item.id}", use_container_width=True):
                        st.session_state[schedule_open_key] = False
                        st.rerun()

            if item.final_status == "failed" and item.error_message:
                with st.expander("Last publish error"):
                    st.code(item.error_message)


def render_simple_detail(item, content_type, data):
    if content_type == "news_article":
        preview = f"**{data.get('headline', '')}**\n\n{data.get('body', '')}"
    elif content_type == "reel_idea":
        preview = f"**Hook:** {data.get('hook', '')}\n\n**Script:** {data.get('script', '')}"
    elif content_type == "youtube_idea":
        preview = f"**Title:** {data.get('seo_title', '')}\n\n**Script:** {data.get('script', '')}"
    else:
        preview = str(data)

    editing_key = f"editing_simple_{item.id}"
    if editing_key not in st.session_state:
        st.session_state[editing_key] = False

    if not st.session_state[editing_key]:
        st.markdown(preview)
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(key=f"accept-btn-{item.id}"):
                if st.button("Accept", key=f"acceptbtn_{item.id}", use_container_width=True):
                    update_content_item_status(item.id, "approved")
                    st.rerun()
        with c2:
            with st.container(key=f"regen-btn-{item.id}"):
                if st.button("Regenerate", key=f"regenbtn_{item.id}", use_container_width=True):
                    with st.spinner("Regenerating..."):
                        new_content = regenerate_single_item(content_type, transcript_text, previous_text=preview)
                        regenerate_content_item(item.id, new_content)
                    st.rerun()
        with c3:
            if st.button("Edit", key=f"editbtn_{item.id}", use_container_width=True):
                st.session_state[editing_key] = True
                st.rerun()
    else:
        if content_type == "news_article":
            new_headline = st.text_input("Headline", value=data.get("headline", ""), key=f"headline_{item.id}")
            new_body = st.text_area("Body", value=data.get("body", ""), height=200, key=f"body_{item.id}")
            edited_data = {"headline": new_headline, "body": new_body}
        elif content_type == "reel_idea":
            new_hook = st.text_input("Hook", value=data.get("hook", ""), key=f"hook_{item.id}")
            new_script = st.text_area("Script", value=data.get("script", ""), height=120, key=f"script_{item.id}")
            new_scenes = st.text_area("Scene breakdown", value="\n".join(data.get("scene_breakdown", [])), height=100, key=f"scenes_{item.id}")
            new_caption = st.text_area("Caption", value=data.get("caption", ""), height=60, key=f"caption_{item.id}")
            new_hashtags = st.text_input("Hashtags", value=" ".join(data.get("hashtags", [])), key=f"hashtags_{item.id}")
            edited_data = {
                "hook": new_hook, "script": new_script,
                "scene_breakdown": new_scenes.split("\n"),
                "caption": new_caption, "hashtags": new_hashtags.split()
            }
        elif content_type == "youtube_idea":
            new_title = st.text_input("SEO Title", value=data.get("seo_title", ""), key=f"title_{item.id}")
            new_thumb = st.text_area("Thumbnail idea", value=data.get("thumbnail_idea", ""), height=60, key=f"thumb_{item.id}")
            new_script = st.text_area("Script", value=data.get("script", ""), height=120, key=f"yt_script_{item.id}")
            new_desc = st.text_area("Description", value=data.get("description", ""), height=80, key=f"desc_{item.id}")
            new_tags = st.text_input("Tags", value=" ".join(data.get("tags", [])), key=f"tags_{item.id}")
            edited_data = {
                "seo_title": new_title, "thumbnail_idea": new_thumb,
                "script": new_script, "description": new_desc,
                "tags": new_tags.split()
            }
        else:
            edited_data = data

        with st.container(key=f"edit-btn-{item.id}"):
            if st.button("Save & Accept", key=f"saveacceptbtn_{item.id}", use_container_width=True):
                update_content_item_text(item.id, edited_data)
                update_content_item_status(item.id, "approved")
                st.session_state[editing_key] = False
                st.rerun()


for tab, content_type in zip(tabs, content_types_present):
    with tab:
        render_tab(content_type, items_by_type[content_type])