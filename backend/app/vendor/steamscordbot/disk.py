"""Disk commands that can be embedded without a Discord client."""

from __future__ import annotations


def playing_title(summary: dict) -> str | None:
    """Read the current public game from a Steam GetPlayerSummaries result."""
    game = summary.get("gameextrainfo")
    if (
        summary.get("communityvisibilitystate") != 3
        or summary.get("personastate") == 0
        or not summary.get("gameid")
        or not isinstance(game, str)
    ):
        return None
    return game.strip()[:160] or None


def latest_posts(rows: list[dict]) -> list[dict]:
    """Turn the disk feed into compact, plain-text command results."""
    return [
        {
            "id": int(row["id"]),
            "username": row["username"],
            "excerpt": " ".join((row.get("excerpt") or "").split()),
        }
        for row in rows[:5]
    ]
