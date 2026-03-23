import re
from typing import Optional

import structlog

logger = structlog.get_logger()

# Category rules based on title/description patterns
CATEGORY_RULES = {
    "tutorials": r"tutorial|how to|learn|course|guide|lesson|explained|instruction",
    "music": r"music|song|album|concert|remix|cover|lyrics|audio",
    "cooking": r"recipe|cooking|chef|kitchen|bake|food|meal|diet",
    "gaming": r"gameplay|gaming|playthrough|walkthrough|lets? play|game|esports",
    "tech": r"tech|programming|code|software|hardware|review|dev|api|database",
    "sports": r"sport|football|basketball|soccer|match|goal|game|championship",
    "news": r"news|breaking|report|update|analysis|current events",
    "entertainment": r"funny|comedy|prank|vlog|reaction|skit|laugh",
}


def auto_categorize(
    title: str,
    description: Optional[str],
    platform: str,
    duration: Optional[int],
) -> str:
    """
    Automatically categorize a video based on its metadata.

    Args:
        title: Video title
        description: Video description
        platform: Platform (youtube, instagram, tiktok, etc.)
        duration: Duration in seconds

    Returns:
        Category name or 'uncategorized'
    """
    # Short-form content detection
    if platform in ("instagram", "tiktok") or (duration and duration < 60):
        return "short-form"

    # Combine title and description for analysis
    text = f"{title} {description or ''}".lower()

    # Check each category rule
    for category, pattern in CATEGORY_RULES.items():
        if re.search(pattern, text, re.IGNORECASE):
            logger.debug(
                "auto_categorized", title=title, category=category, pattern=pattern
            )
            return category

    logger.debug("auto_categorization_failed", title=title)
    return "uncategorized"
