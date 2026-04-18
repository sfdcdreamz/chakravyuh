import re
import httpx
from services.claude_service import call_claude
from prompts import VIDEO_LINK_PROMPT_TEMPLATE

VIDEO_DOMAINS = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
}

URL_PATTERN = re.compile(r"https?://[^\s]+")


async def handle_video(message: str) -> tuple[str, str]:
    """
    Extracts video URL from message, fetches metadata, then Claude analysis.
    Returns (verdict_response, verdict_label).
    """
    urls = URL_PATTERN.findall(message)
    video_url = urls[0] if urls else message.strip()

    platform = _detect_platform(video_url)
    meta = await _fetch_metadata(video_url)

    prompt = VIDEO_LINK_PROMPT_TEMPLATE.format(
        video_url=video_url,
        platform=platform,
        video_title=meta.get("title", "Unknown"),
        video_description=meta.get("description", "Not available"),
        upload_date=meta.get("upload_date", "Unknown"),
        channel_name=meta.get("channel", "Unknown"),
        user_message=message,
    )

    response = await call_claude("You are Chakravyuh, an AI fact-checker.", prompt)
    verdict_label = _extract_verdict_label(response)
    return response, verdict_label


def _detect_platform(url: str) -> str:
    for domain, name in VIDEO_DOMAINS.items():
        if domain in url:
            return name
    return "Unknown platform"


async def _fetch_metadata(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # YouTube oEmbed — no API key required
            if "youtube.com" in url or "youtu.be" in url:
                oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                oe = await client.get(oembed_url, timeout=8)
                if oe.status_code == 200:
                    data = oe.json()
                    return {
                        "title": data.get("title", "Unknown"),
                        "description": "",
                        "channel": data.get("author_name", "Unknown"),
                        "upload_date": "",
                    }

            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            html = r.text
            title = _extract_meta_tag(html, "og:title") or _extract_title_tag(html)
            description = _extract_meta_tag(html, "og:description") or ""
            channel = _extract_meta_tag(html, "og:site_name") or ""

            # Try JSON-LD for upload date and author
            upload_date = ""
            ld_match = re.search(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
            if ld_match:
                import json
                try:
                    ld = json.loads(ld_match.group(1))
                    upload_date = ld.get("uploadDate", ld.get("datePublished", ""))
                    if not channel:
                        author = ld.get("author", {})
                        channel = author.get("name", "") if isinstance(author, dict) else ""
                except Exception:
                    pass

            return {"title": title, "description": description[:300], "channel": channel, "upload_date": upload_date}
    except Exception:
        return {"title": "Could not fetch", "description": "", "channel": "", "upload_date": ""}


def _extract_meta_tag(html: str, property_name: str) -> str:
    pattern = re.compile(rf'<meta[^>]+property="{re.escape(property_name)}"[^>]+content="([^"]+)"', re.IGNORECASE)
    match = pattern.search(html)
    if match:
        return match.group(1)
    pattern2 = re.compile(rf'<meta[^>]+content="([^"]+)"[^>]+property="{re.escape(property_name)}"', re.IGNORECASE)
    match2 = pattern2.search(html)
    return match2.group(1) if match2 else ""


def _extract_title_tag(html: str) -> str:
    match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    return match.group(1).strip() if match else "Unknown"


def _extract_verdict_label(text: str) -> str:
    first_line = text.strip().split("\n")[0].upper()
    if "✅" in first_line or "TRUE" in first_line:
        return "TRUE"
    if "❌" in first_line or "FALSE" in first_line:
        return "FALSE"
    if "⚠️" in first_line or "MISLEADING" in first_line:
        return "MISLEADING"
    return "UNVERIFIED"
