from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

_client = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _client


def send_whatsapp_message(to: str, body: str) -> None:
    client = get_client()
    client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=to,
        body=body,
    )
