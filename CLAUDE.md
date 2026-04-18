# Chakravyuh — Claude Code Project Instructions

## Project Identity

**Chakravyuh** is a WhatsApp fact-checker built for Indian audiences. Users send text, images,
voice notes, or YouTube links via WhatsApp; the bot fact-checks the content using Claude AI
and replies in the user's own language.

**Tech stack:** FastAPI · Twilio (WhatsApp) · Anthropic Claude API · Google Cloud (Vision + STT) · Airtable

---

## Architecture at a Glance

- **Entry point:** `main.py` — single `POST /webhook` endpoint receives all Twilio callbacks
- **Routing:** message type (text / image / voice / video) → dedicated handler → Claude →
  Twilio reply → Airtable log
- **Rate limiter:** in-memory, 10 requests per phone number per hour (implemented in `main.py`)
- **Airtable logging:** fire-and-forget — failures are printed to server log but never block
  the main response flow

---

## File Map

| File | Role |
|------|------|
| `main.py` | FastAPI app, `/webhook` routing, rate limiting |
| `config.py` | Env var loading, Google credentials handling |
| `prompts.py` | All Claude prompts and WhatsApp reply strings |
| `handlers/text_handler.py` | Plain-text fact-check flow |
| `handlers/image_handler.py` | Google Vision OCR/label → Claude |
| `handlers/voice_handler.py` | Google STT transcription → Claude |
| `handlers/video_handler.py` | YouTube oEmbed + JSON-LD metadata → Claude |
| `services/claude_service.py` | Anthropic API calls (`claude-sonnet-4-20250514`) |
| `services/twilio_service.py` | WhatsApp send helper (singleton Twilio client) |
| `services/google_vision.py` | Google Vision API wrapper |
| `services/google_stt.py` | Google STT (`hi-IN` primary, 11 Indian language codes) |
| `services/airtable_service.py` | Analytics logging (phone hashed with SHA-256) |

---

## Environment Variables

```
CLAUDE_API_KEY             Anthropic API key (loaded as CLAUDE_API_KEY in config.py)
TWILIO_ACCOUNT_SID         Twilio account SID
TWILIO_AUTH_TOKEN          Twilio auth token
TWILIO_WHATSAPP_NUMBER     Twilio sandbox/production WhatsApp number (e.g. whatsapp:+14155238886)
AIRTABLE_API_KEY           Airtable personal access token
AIRTABLE_BASE_ID           Airtable base ID
AIRTABLE_TABLE_NAME        Airtable table name for logs
GOOGLE_APPLICATION_CREDENTIALS  Path to local Google service-account JSON (local dev only)
GOOGLE_CREDENTIALS_B64     Base64-encoded Google service-account JSON (production)
```

---

## Key Conventions — Read Before Editing

1. **No markdown in Claude responses.** WhatsApp renders plain text; all prompts in
   `prompts.py` explicitly instruct Claude to avoid markdown. Do not add `**`, `_`, `#`, etc.

2. **Verdict labels** must be exactly one of:
   `TRUE` / `FALSE` / `MISLEADING` / `UNVERIFIED` / `WELCOME` / `ERROR`

3. **Claude model:** `claude-sonnet-4-20250514` — defined as `CLAUDE_MODEL` in `config.py`.
   Do not hard-code the model string anywhere else.

4. **Response language:** always matches the user's input language. Claude auto-detects it;
   do not force English.

5. **Max response length:** 200 words (enforced via prompt instruction in `prompts.py`).

6. **Airtable errors:** catch and `print(f"[Airtable] Logging failed: {e}")` — never `raise`.

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (always run from project root so .env is found)
uvicorn main:app --reload --port 8000

# Expose to Twilio via ngrok
ngrok http 8000
# Set Twilio sandbox webhook URL to: https://<ngrok-url>/webhook
```

> **Important:** Always start uvicorn from the project root directory
> (`C:\Users\Dhirendra Mohan\Productathon\chakravyuh`). `config.py` uses
> `load_dotenv()` which resolves `.env` relative to the working directory.
> If the server is restarted (e.g. after editing `.env`), make sure to fully
> terminate the old process first — on Windows, use Task Manager or
> `python -c "import subprocess; subprocess.run(['taskkill','/F','/PID','<PID>'])"`.
> Killing only the reloader (the first listed uvicorn PID) may leave the
> worker process alive and still serving on port 8000 with the old env.

---

## Google Credentials

| Environment | How to configure |
|-------------|-----------------|
| Local dev | `GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json` |
| Production | Base64-encode the JSON key → set as `GOOGLE_CREDENTIALS_B64` |

`config.py` checks for `GOOGLE_CREDENTIALS_B64` first; if absent it falls back to
`GOOGLE_APPLICATION_CREDENTIALS`. No changes needed in handler code.

---

## Deployment

- **Process file:** `Procfile` → `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Target platforms:** Railway or Render
- Ensure all env vars above are set in the platform's environment settings.
- Replace `GOOGLE_APPLICATION_CREDENTIALS` with `GOOGLE_CREDENTIALS_B64` (base64 of the service account JSON).

---

## E2E Test Status (verified 2026-04-19)

All 5 handlers confirmed working end-to-end via Twilio WhatsApp sandbox:

| Handler | Test input | Result |
|---------|-----------|--------|
| Welcome | `Hello` | Bilingual welcome message |
| Text (English) | `Is 5G causing COVID-19?` | FALSE verdict |
| Text (Hindi) | Hindi claim | Correct verdict in Hindi |
| Image | WhatsApp screenshot | Google Vision → verdict |
| Voice | Voice note | Google STT → verdict |
| Video | YouTube URL | Metadata → verdict |

Twilio sandbox number: `whatsapp:+14155238886`
