import httpx
from services.claude_service import call_claude
from services.google_stt import transcribe_audio
from prompts import VOICE_TRANSCRIPTION_PROMPT_TEMPLATE, ERROR_MESSAGE
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


async def handle_voice(media_url: str) -> tuple[str, str]:
    """
    Downloads voice note, transcribes via Google STT, then fact-checks with Claude.
    Returns (verdict_response, verdict_label).
    """
    audio_bytes = await _download_media(media_url)
    stt_result = await transcribe_audio(audio_bytes)

    transcription = stt_result.get("transcription", "")
    if not transcription:
        return ERROR_MESSAGE, "ERROR"

    prompt = VOICE_TRANSCRIPTION_PROMPT_TEMPLATE.format(
        transcription=transcription,
        language_code=stt_result.get("language_code", "hi-IN"),
        confidence=stt_result.get("confidence", 0),
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
