import time
import asyncio
from collections import defaultdict
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse

from handlers.text_handler import handle_text
from handlers.image_handler import handle_image
from handlers.voice_handler import handle_voice
from handlers.video_handler import handle_video
from services.twilio_service import send_whatsapp_message
from services.airtable_service import log_fact_check
from prompts import WELCOME_MESSAGE, ERROR_MESSAGE, RATE_LIMIT_MESSAGE

app = FastAPI(title="Chakravyuh - WhatsApp Fact Checker")

VIDEO_DOMAINS = ["youtube", "youtu.be", "twitter.com", "x.com", "instagram.com", "facebook.com", "fb.watch"]
GREETING_KEYWORDS = ["hi", "hello", "नमस्ते", "hey", "start", "help"]

# Rate limiting: max 10 requests per phone number per hour
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 10
RATE_WINDOW = 3600  # seconds


def _is_rate_limited(phone: str) -> bool:
    now = time.time()
    _rate_store[phone] = [t for t in _rate_store[phone] if now - t < RATE_WINDOW]
    if len(_rate_store[phone]) >= RATE_LIMIT:
        return True
    _rate_store[phone].append(now)
    return False


@app.get("/")
async def root():
    return {"status": "Chakravyuh is running 🛡️"}


@app.post("/webhook")
async def webhook(
    From: str = Form(default=""),
    Body: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default=""),
):
    if _is_rate_limited(From):
        send_whatsapp_message(From, RATE_LIMIT_MESSAGE)
        return PlainTextResponse("", status_code=200)

    start_time = time.time()
    sender = From
    num_media = int(NumMedia or 0)
    body = Body.strip()

    response_text = ""
    verdict_label = "UNVERIFIED"
    content_type = "text"
    language = "hi"
    error_occurred = False
    error_details = ""

    try:
        # Greeting / first contact
        if not body and num_media == 0:
            response_text = WELCOME_MESSAGE
            verdict_label = "WELCOME"
            content_type = "text"

        elif num_media == 0 and body.lower() in GREETING_KEYWORDS:
            response_text = WELCOME_MESSAGE
            verdict_label = "WELCOME"
            content_type = "text"

        # Image
        elif num_media > 0 and "image" in MediaContentType0.lower():
            content_type = "image"
            response_text, verdict_label = await handle_image(MediaUrl0, body)

        # Voice note
        elif num_media > 0 and "audio" in MediaContentType0.lower():
            content_type = "voice"
            response_text, verdict_label = await handle_voice(MediaUrl0)

        # Video link in text
        elif num_media == 0 and any(d in body.lower() for d in VIDEO_DOMAINS):
            content_type = "video"
            response_text, verdict_label = await handle_video(body)

        # Plain text fact-check
        elif num_media == 0 and body:
            content_type = "text"
            response_text, verdict_label = await handle_text(body)

        else:
            response_text = ERROR_MESSAGE
            verdict_label = "ERROR"

    except Exception as e:
        error_occurred = True
        error_details = str(e)[:200]
        response_text = (
            "⚠️ Something went wrong while checking this.\n"
            "Please try again in a moment.\n\n"
            "Chakravyuh 🛡️"
        )
        verdict_label = "ERROR"

    # Send WhatsApp reply
    try:
        send_whatsapp_message(sender, response_text)
    except Exception as send_err:
        error_occurred = True
        error_details += f" | Send error: {str(send_err)[:100]}"

    processing_ms = int((time.time() - start_time) * 1000)

    # Log to Airtable (fire-and-forget)
    asyncio.create_task(
        log_fact_check(
            phone=sender,
            content_type=content_type,
            language=language,
            input_raw=body or f"[{content_type} media]",
            verdict=verdict_label,
            response_sent=response_text,
            processing_time_ms=processing_ms,
            error=error_occurred,
            error_details=error_details,
        )
    )

    # Twilio expects a 200 OK (empty TwiML or plain text)
    return PlainTextResponse("", status_code=200)
