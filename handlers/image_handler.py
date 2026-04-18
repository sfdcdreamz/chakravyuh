import base64
import httpx
from services.claude_service import call_claude
from services.google_vision import analyze_image
from prompts import IMAGE_ANALYSIS_PROMPT_TEMPLATE
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


async def handle_image(media_url: str, user_message: str = "") -> tuple[str, str]:
    """
    Downloads image from Twilio, runs Google Vision, then Claude analysis.
    Returns (verdict_response, verdict_label).
    """
    image_bytes = await _download_media(media_url)
    vision_data = await analyze_image(image_bytes)

    prompt = IMAGE_ANALYSIS_PROMPT_TEMPLATE.format(
        vision_results=vision_data.get("labels", "Not available"),
        best_guess=vision_data.get("best_guess", "Unknown"),
        num_matches=vision_data.get("num_matches", 0),
        page_urls=vision_data.get("page_urls", "None found"),
        similar_count=vision_data.get("similar_count", 0),
        adult_score=vision_data.get("adult_score", "UNKNOWN"),
        violence_score=vision_data.get("violence_score", "UNKNOWN"),
        racy_score=vision_data.get("racy_score", "UNKNOWN"),
        detected_text=vision_data.get("detected_text", "No text"),
        user_message=user_message or "Please analyze this image for misinformation.",
    )

    response = await call_claude("You are Chakravyuh, an AI fact-checker.", prompt)
    verdict_label = _extract_verdict_label(response)
    return response, verdict_label


async def _download_media(url: str) -> bytes:
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient(timeout=30, auth=auth) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


def _extract_verdict_label(text: str) -> str:
    first_line = text.strip().split("\n")[0].upper()
    if "✅" in first_line or "TRUE" in first_line:
        return "TRUE"
    if "❌" in first_line or "FALSE" in first_line:
        return "FALSE"
    if "⚠️" in first_line or "MISLEADING" in first_line:
        return "MISLEADING"
    return "UNVERIFIED"
