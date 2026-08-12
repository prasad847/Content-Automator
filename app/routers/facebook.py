import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import save_connection
from services.facebook_service import get_access_token, get_pages

app = FastAPI()


@app.get("/facebook/callback", response_class=HTMLResponse)
def facebook_callback(code: str):
    """Facebook redirects here after the user approves the OAuth dialog."""
    token_response = get_access_token(code)
    user_access_token = token_response.get("access_token")
    if not user_access_token:
        return f"<h3>Facebook login failed</h3><p>{token_response}</p>"

    pages_response = get_pages(user_access_token)
    pages = pages_response.get("data", [])
    if not pages:
        return "<h3>No Facebook Pages found</h3><p>This account doesn't manage any Pages.</p>"

    page = pages[0]
    save_connection("facebook", page["id"], page["access_token"])

    return f"<h3>Connected to Facebook Page: {page['name']}</h3><p>You can close this tab and return to the dashboard.</p>"
