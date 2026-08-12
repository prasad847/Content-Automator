import json
from db import get_connection, mark_content_item_published, log_event
from services.facebook_service import publish_post


def post_to_facebook(message, image_path=None):
    """Post to the connected Facebook page. Returns the published post ID."""
    connection = get_connection("facebook")
    if not connection:
        raise Exception("Facebook is not connected.")

    result = publish_post(connection.page_id, connection.access_token, message, image_path)

    if "error" in result:
        raise Exception(result["error"].get("message", "Unknown Facebook API error"))

    return result.get("post_id") or result.get("id")


def publish_facebook_item(item):
    """Publish an approved facebook_post content item using its saved publish flags."""
    try:
        data = json.loads(item.content)

        message = ""
        if item.publish_include_hook and item.hook_content:
            message += item.hook_content + "\n\n"
        if item.publish_include_text:
            message += data.get("text", "")
        message = message.strip()

        image_path = None
        if item.publish_include_image:
            image_path = item.final_image_path if (item.hook_on_image and item.final_image_path) else item.image_path

        result = post_to_facebook(message, image_path)
        post_url = f"https://www.facebook.com/{result}"

        mark_content_item_published(item.id)
        log_event(item.job_id, "facebook_publish", "success", f"Post ID: {result} — {post_url}")
        return post_url
    except Exception as e:
        log_event(item.job_id, "facebook_publish", "failed", str(e))
        raise
