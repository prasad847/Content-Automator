import requests
from urllib.parse import urlencode
from config import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, REDIRECT_URI, GRAPH_VERSION

def get_login_url():
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "public_profile,pages_show_list,pages_manage_posts"
    }

    return (
        f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth?"
        + urlencode(params)
    )

def get_access_token(code):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token"

    params = {
        "client_id": FACEBOOK_APP_ID,
        "client_secret": FACEBOOK_APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }

    response = requests.get(url, params=params)

    return response.json()

def get_user_profile(access_token):

    url = f"https://graph.facebook.com/me"

    params = {
        "fields": "id,name",
        "access_token": access_token
    }

    response = requests.get(url, params=params)

    return response.json()


def get_pages(access_token):

    url = "https://graph.facebook.com/me/accounts"

    params = {
        "access_token": access_token
    }

    response = requests.get(url, params=params)

    return response.json()

def publish_post(page_id, page_access_token, message):

    url = f"https://graph.facebook.com/v23.0/{page_id}/feed"

    response = requests.post(
        url,
        data={
            "message": message,
            "access_token": page_access_token
        }
    )

    return response.json()