import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from models import engine, Job, Transcript, ContentItem, Connection, Log

Session = sessionmaker(bind=engine)


def create_job(drive_file_id, file_name, instructions=None):
    """Return the existing job for this Drive file if one exists, otherwise create a new one."""
    session = Session()

    existing_job = session.query(Job).filter(Job.drive_file_id == drive_file_id).first()
    if existing_job:
        session.close()
        return existing_job

    job = Job(drive_file_id=drive_file_id, file_name=file_name, status="uploaded", instructions=instructions)
    session.add(job)
    session.commit()
    session.refresh(job)
    session.close()
    return job


def save_transcript(job_id, text):
    """Save a transcript linked to a job, and update the job's status."""
    session = Session()

    transcript = Transcript(job_id=job_id, text=text)
    session.add(transcript)

    job = session.query(Job).filter(Job.id == job_id).first()
    job.status = "transcribed"

    session.commit()
    session.close()


def save_content_items(job_id, content_type, items_list):
    """Save each item in the list as its own row, numbered 1, 2, 3..."""
    session = Session()
    for index, item_dict in enumerate(items_list, start=1):
        item = ContentItem(
            job_id=job_id,
            content_type=content_type,
            item_index=index,
            content=json.dumps(item_dict),
            status="draft"
        )
        session.add(item)
    session.commit()
    session.close()


def update_job_status(job_id, status):
    """Update a job's overall pipeline status."""
    session = Session()
    job = session.query(Job).filter(Job.id == job_id).first()
    job.status = status
    session.commit()
    session.close()


def get_all_jobs():
    """Return all jobs, most recent first."""
    session = Session()
    jobs = session.query(Job).order_by(Job.id.desc()).all()
    session.close()
    return jobs


def get_job(job_id):
    """Return a single job by ID."""
    session = Session()
    job = session.query(Job).filter(Job.id == job_id).first()
    session.close()
    return job


def get_transcript_text(job_id):
    """Return the transcript text for a job, or None if not found."""
    session = Session()
    transcript = session.query(Transcript).filter(Transcript.job_id == job_id).first()
    session.close()
    return transcript.text if transcript else None


def get_content_items(job_id):
    """Return only the CURRENT version of each content item for a job."""
    session = Session()
    items = (
        session.query(ContentItem)
        .filter(ContentItem.job_id == job_id)
        .filter(ContentItem.is_final == True)
        .order_by(ContentItem.content_type, ContentItem.item_index)
        .all()
    )
    session.close()
    return items


def update_content_item_status(item_id, status):
    """Approve a content item, or delete it entirely if rejected."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()

    if status == "rejected":
        session.delete(item)
    else:
        item.status = status

    session.commit()
    session.close()


def update_content_item_text(item_id, new_content_dict):
    """Save edited content for an item."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.content = json.dumps(new_content_dict)
    session.commit()
    session.close()


def update_content_item_schedule(item_id, scheduled_datetime):
    """Save a publish date/time for a content item."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.scheduled_at = scheduled_datetime
    session.commit()
    session.close()


def get_scheduled_posts():
    """Return all approved content items that have a schedule time set, soonest first."""
    session = Session()
    items = (
        session.query(ContentItem)
        .filter(ContentItem.status == "approved")
        .filter(ContentItem.scheduled_at.isnot(None))
        .order_by(ContentItem.scheduled_at.asc())
        .all()
    )
    session.close()
    return items


def regenerate_content_item(old_item_id, new_content_dict):
    """Replace a content item with a new version, deleting the old one entirely."""
    session = Session()

    old_item = session.query(ContentItem).filter(ContentItem.id == old_item_id).first()
    job_id = old_item.job_id
    content_type = old_item.content_type
    item_index = old_item.item_index
    next_version = old_item.version + 1

    session.delete(old_item)

    new_item = ContentItem(
        job_id=job_id,
        content_type=content_type,
        item_index=item_index,
        content=json.dumps(new_content_dict),
        version=next_version,
        status="draft",
        is_final=True
    )
    session.add(new_item)
    session.commit()
    session.close()


def get_approved_items(job_id):
    """Return all approved content items for a job, current versions only."""
    session = Session()
    items = (
        session.query(ContentItem)
        .filter(ContentItem.job_id == job_id)
        .filter(ContentItem.is_final == True)
        .filter(ContentItem.status == "approved")
        .order_by(ContentItem.content_type, ContentItem.item_index)
        .all()
    )
    session.close()
    return items


def get_analytics_summary():
    """Return overall counts across the whole pipeline."""
    session = Session()

    total_jobs = session.query(Job).count()

    total_content_items = session.query(ContentItem).filter(ContentItem.is_final == True).count()
    approved_items = session.query(ContentItem).filter(ContentItem.is_final == True, ContentItem.status == "approved").count()
    rejected_items = session.query(ContentItem).filter(ContentItem.is_final == True, ContentItem.status == "rejected").count()
    draft_items = session.query(ContentItem).filter(ContentItem.is_final == True, ContentItem.status == "draft").count()
    scheduled_items = session.query(ContentItem).filter(
        ContentItem.is_final == True,
        ContentItem.status == "approved",
        ContentItem.scheduled_at.isnot(None)
    ).count()

    type_counts = {}
    all_current_items = session.query(ContentItem).filter(ContentItem.is_final == True).all()
    for item in all_current_items:
        type_counts[item.content_type] = type_counts.get(item.content_type, 0) + 1

    session.close()

    return {
        "total_jobs": total_jobs,
        "total_content_items": total_content_items,
        "approved_items": approved_items,
        "rejected_items": rejected_items,
        "draft_items": draft_items,
        "scheduled_items": scheduled_items,
        "type_counts": type_counts,
    }


def log_event(job_id, stage, status, message=None):
    """Record a pipeline event (success or failure) permanently."""
    session = Session()
    log = Log(job_id=job_id, stage=stage, status=status, message=message)
    session.add(log)
    session.commit()
    session.close()


def get_logs(job_id=None):
    """Return logs, optionally filtered to one job, most recent first."""
    session = Session()
    query = session.query(Log)
    if job_id is not None:
        query = query.filter(Log.job_id == job_id)
    logs = query.order_by(Log.created_at.desc()).all()
    session.close()
    return logs


def approve_post_and_advance(item_id):
    """Approve the post text stage and move the item into the hook stage."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.status = "approved"
    item.stage = "hook"
    session.commit()
    session.close()


def save_hook(item_id, hook_text):
    """Save a freshly generated hook, in draft status."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.hook_content = hook_text
    item.hook_status = "draft"
    session.commit()
    session.close()


def approve_hook_and_advance(item_id):
    """Approve the hook and move the item into the image stage."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.hook_status = "approved"
    item.stage = "image"
    session.commit()
    session.close()


def save_image(item_id, image_path):
    """Save a freshly generated image's file path, in draft status."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.image_path = image_path
    item.image_status = "draft"
    session.commit()
    session.close()


def approve_image_and_complete(item_id):
    """Approve the image and mark the item's pipeline as complete."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.image_status = "approved"
    item.stage = "complete"
    session.commit()
    session.close()


def update_publish_flags(item_id, include_text, include_hook, include_image):
    """Save which combination of text/hook/image should actually be published."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.publish_include_text = include_text
    item.publish_include_hook = include_hook
    item.publish_include_image = include_image
    session.commit()
    session.close()


def mark_content_item_published(item_id):
    """Mark a content item as published, recording when it happened."""
    session = Session()
    item = session.query(ContentItem).filter(ContentItem.id == item_id).first()
    item.status = "published"
    item.published_at = datetime.utcnow()
    session.commit()
    session.close()


def get_connection(platform):
    """Return the saved connection for a platform (e.g. 'facebook'), or None if not connected."""
    session = Session()
    connection = session.query(Connection).filter(Connection.platform == platform).first()
    session.close()
    return connection


def save_connection(platform, page_id, access_token):
    """Create or update the saved connection for a platform."""
    session = Session()
    connection = session.query(Connection).filter(Connection.platform == platform).first()

    if connection:
        connection.page_id = page_id
        connection.access_token = access_token
    else:
        connection = Connection(platform=platform, page_id=page_id, access_token=access_token)
        session.add(connection)

    session.commit()
    session.close()