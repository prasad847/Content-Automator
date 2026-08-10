from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    drive_file_id = Column(String, unique=True)
    file_name = Column(String)
    status = Column(String, default="uploaded")  # uploaded, transcribing, generating, awaiting_approval, scheduled, published, failed
    instructions = Column(Text, nullable=True)  # guidance from the instructions text box
    created_at = Column(DateTime, default=datetime.utcnow)

    transcript = relationship("Transcript", back_populates="job", uselist=False)
    content_items = relationship("ContentItem", back_populates="job")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    text = Column(Text)
    provider = Column(String, default="groq-whisper-large-v3-turbo")
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="transcript")


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    content_type = Column(String)  # facebook_post, x_post, news_article, reel_idea, youtube_idea
    item_index = Column(Integer, default=1)  # which post number in the batch (1-5)
    content = Column(Text)  # JSON for this ONE item only
    version = Column(Integer, default=1)
    status = Column(String, default="draft")  # draft, approved, rejected
    scheduled_at = Column(DateTime, nullable=True)  # when this post should be published
    is_final = Column(Boolean, default=True)  # True = current version, False = superseded history

    stage = Column(String, default="post")  # post, hook, image, complete
    hook_content = Column(Text, nullable=True)
    hook_status = Column(String, default="draft")  # draft, approved
    image_path = Column(Text, nullable=True)
    image_status = Column(String, default="draft")  # draft, approved
    publish_include_text = Column(Boolean, default=True)
    publish_include_hook = Column(Boolean, default=False)
    publish_include_image = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="content_items")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    stage = Column(String)  # e.g. transcription, facebook_post, linkedin_post, etc.
    status = Column(String)  # success, failed
    message = Column(Text, nullable=True)  # error details, or None on success
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables in Postgres if they don't already exist."""
    Base.metadata.create_all(engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    init_db()