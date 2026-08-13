import threading
import time

from db import get_due_scheduled_items, mark_content_item_failed
from services.publisher_service import publish_facebook_item

POLL_SECONDS = 30

_started = False
_lock = threading.Lock()


def _publish_due_items():
    for item in get_due_scheduled_items():
        if item.content_type != "facebook_post":
            # No publisher implemented yet for this platform - leave it scheduled.
            continue
        try:
            publish_facebook_item(item)
        except Exception as e:
            mark_content_item_failed(item.id, str(e))


def _run_loop():
    while True:
        try:
            _publish_due_items()
        except Exception:
            pass
        time.sleep(POLL_SECONDS)


def start_scheduler():
    """Start the background auto-publish loop once per server process.

    Streamlit reruns app scripts on every interaction, but this module-level
    guard means the polling thread is only ever spawned the first time - safe
    to call from the top of any page."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
        threading.Thread(target=_run_loop, daemon=True).start()
