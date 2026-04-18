import os
import json
import base64
import tempfile
from dotenv import load_dotenv

load_dotenv()

# --- Google Cloud credentials ---
# On Railway/Render: store the JSON key as base64 in GOOGLE_CREDENTIALS_B64
# Locally: set GOOGLE_APPLICATION_CREDENTIALS to the path of the JSON file
_google_creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if _google_creds_b64:
    _decoded = base64.b64decode(_google_creds_b64).decode("utf-8")
    _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    _tmp.write(_decoded)
    _tmp.flush()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Fact_Checks")
