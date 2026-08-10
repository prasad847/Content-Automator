from dotenv import load_dotenv
import os

load_dotenv()

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GRAPH_VERSION = os.getenv("GRAPH_VERSION")