import hashlib
import asyncio
from datetime import datetime
from pyairtable import Api
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()[:16]


def _log_sync(record: dict) -> None:
    try:
        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        table.create(record)
    except Exception as e:
        print(f"[Airtable] Logging failed: {e}")


async def log_fact_check(
    phone: str,
    content_type: str,
    language: str,
    input_raw: str,
    verdict: str,
    response_sent: str,
    processing_time_ms: int,
    error: bool = False,
    error_details: str = "",
) -> None:
    record = {
        "Timestamp": datetime.utcnow().isoformat(),
        "Phone_Hash": _hash_phone(phone),
        "Content_Type": content_type,
        "Language_Detected": language,
        "Input_Raw": input_raw[:500],  # truncate to avoid airtable limit
        "Verdict": verdict,
        "Response_Sent": response_sent[:1000],
        "Processing_Time_ms": processing_time_ms,
        "Error_Occurred": error,
        "Error_Details": error_details[:200] if error_details else "",
    }
    # Run in thread pool so it doesn't block the async event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _log_sync, record)
