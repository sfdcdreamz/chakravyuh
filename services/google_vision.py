import os
import base64
import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request

VISION_URL = "https://vision.googleapis.com/v1/images:annotate"


def _get_access_token() -> str:
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    credentials.refresh(Request())
    return credentials.token


async def analyze_image(image_bytes: bytes) -> dict:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "requests": [
            {
                "image": {"content": encoded},
                "features": [
                    {"type": "WEB_DETECTION", "maxResults": 10},
                    {"type": "SAFE_SEARCH_DETECTION"},
                    {"type": "TEXT_DETECTION"},
                    {"type": "LABEL_DETECTION", "maxResults": 5},
                ],
            }
        ]
    }
    token = _get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(VISION_URL, headers=headers, json=payload)
        response.raise_for_status()
        return _parse_vision_response(response.json())


def _parse_vision_response(raw: dict) -> dict:
    result = raw.get("responses", [{}])[0]
    web = result.get("webDetection", {})
    safe = result.get("safeSearchAnnotation", {})
    texts = result.get("textAnnotations", [])
    labels = result.get("labelAnnotations", [])

    page_urls = [p.get("url", "") for p in web.get("pagesWithMatchingImages", [])]
    best_guess = ""
    if web.get("bestGuessLabels"):
        best_guess = web["bestGuessLabels"][0].get("label", "")

    return {
        "best_guess": best_guess,
        "num_matches": len(web.get("fullMatchingImages", [])),
        "similar_count": len(web.get("visuallySimilarImages", [])),
        "page_urls": ", ".join(page_urls[:3]) if page_urls else "None found",
        "detected_text": texts[0].get("description", "No text detected") if texts else "No text detected",
        "labels": ", ".join([l.get("description", "") for l in labels]),
        "adult_score": safe.get("adult", "UNKNOWN"),
        "violence_score": safe.get("violence", "UNKNOWN"),
        "racy_score": safe.get("racy", "UNKNOWN"),
    }
