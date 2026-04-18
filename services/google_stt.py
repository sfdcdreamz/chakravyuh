import os
import base64
import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request

STT_URL = "https://speech.googleapis.com/v1/speech:recognize"

INDIAN_LANGUAGE_CODES = [
    "hi-IN", "en-IN", "bn-IN", "ta-IN", "te-IN",
    "mr-IN", "gu-IN", "kn-IN", "ml-IN", "pa-IN", "ur-IN",
]


def _get_access_token() -> str:
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    credentials.refresh(Request())
    return credentials.token


async def transcribe_audio(audio_bytes: bytes) -> dict:
    encoded = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {
        "config": {
            "encoding": "OGG_OPUS",
            "sampleRateHertz": 16000,
            "languageCode": "hi-IN",
            "alternativeLanguageCodes": INDIAN_LANGUAGE_CODES,
            "enableAutomaticPunctuation": True,
        },
        "audio": {"content": encoded},
    }
    token = _get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(STT_URL, headers=headers, json=payload)
        response.raise_for_status()
        return _parse_stt_response(response.json())


def _parse_stt_response(raw: dict) -> dict:
    results = raw.get("results", [])
    if not results:
        return {"transcription": "", "confidence": 0, "language_code": "hi-IN"}

    best = results[0].get("alternatives", [{}])[0]
    language_code = results[0].get("languageCode", "hi-IN")
    confidence = round(best.get("confidence", 0) * 100, 1)
    transcript = best.get("transcript", "")

    return {
        "transcription": transcript,
        "confidence": confidence,
        "language_code": language_code,
    }
