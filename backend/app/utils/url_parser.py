import re
from typing import Optional


def detect_platform(url: str) -> str:
    """Detect video platform from URL."""
    url_lower = url.lower()

    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower or "vm.tiktok.com" in url_lower:
        return "tiktok"
    elif "twitter.com" in url_lower or "x.com" in url_lower or "t.co" in url_lower:
        return "twitter"
    else:
        return "other"


def extract_video_id(url: str, platform: str) -> Optional[str]:
    """Extract platform-specific video ID from URL."""

    if platform == "youtube":
        # Handle youtube.com/watch?v=ID and youtu.be/ID
        match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)", url)
        return match.group(1) if match else None

    elif platform == "instagram":
        # Handle instagram.com/p/ID/ or instagram.com/reel/ID/
        match = re.search(r"instagram\.com/(?:p|reel|stories)/([A-Za-z0-9_-]+)", url)
        return match.group(1) if match else None

    elif platform == "tiktok":
        # Handle tiktok.com/@user/video/ID or vm.tiktok.com/ID
        match = re.search(r"(?:tiktok\.com/.*?/video/|vm\.tiktok\.com/)(\d+)", url)
        return match.group(1) if match else None

    elif platform == "twitter":
        # Handle twitter.com/user/status/ID or x.com/user/status/ID
        match = re.search(r"(?:twitter|x)\.com/\w+/status/(\d+)", url)
        return match.group(1) if match else None

    # For other platforms, try a generic approach
    # Return the last meaningful part of the URL
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else None
