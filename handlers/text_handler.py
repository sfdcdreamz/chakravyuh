from services.claude_service import call_claude
from prompts import MAIN_SYSTEM_PROMPT


async def handle_text(message: str) -> tuple[str, str]:
    """
    Returns (verdict_response, detected_verdict_label).
    verdict_label is one of: TRUE, FALSE, MISLEADING, UNVERIFIED, ERROR
    """
    response = await call_claude(MAIN_SYSTEM_PROMPT, message)
    verdict_label = _extract_verdict_label(response)
    return response, verdict_label


def _extract_verdict_label(text: str) -> str:
    first_line = text.strip().split("\n")[0].upper()
    if "✅" in first_line or "TRUE" in first_line or "सत्य" in first_line:
        return "TRUE"
    if "❌" in first_line or "FALSE" in first_line or "झूठ" in first_line:
        return "FALSE"
    if "⚠️" in first_line or "MISLEADING" in first_line or "भ्रामक" in first_line:
        return "MISLEADING"
    return "UNVERIFIED"
