"""Difficulty tier conversion for Fellowship dungeons.

Converts raw difficulty levels from combat logs to user-friendly tier names.
"""

from pydantic import BaseModel, Field


class DifficultyTier(BaseModel):
    """Represents a difficulty tier with name and level."""

    tier_name: str = Field(description="Name of the difficulty tier")
    tier_level: int = Field(ge=1, description="Level within the tier")
    is_quick_play: bool = Field(
        default=False, description="Whether this is Quick Play mode"
    )

    def __str__(self) -> str:
        """Return formatted difficulty string."""
        if self.is_quick_play:
            return "Quick Play"
        return f"{self.tier_name} {self.tier_level}"


def get_difficulty_tier(
    difficulty: int, mode: str | int | None = None
) -> DifficultyTier:
    """Convert raw difficulty level to user-friendly tier name.

    Args:
        difficulty: Raw difficulty level from combat logs
        mode: Mode flag from logs (0=challenge, 1=quick_play, None=unknown)

    Returns:
        DifficultyTier with tier name, level, and quick play flag
    """
    is_quick_play = mode == "1" or mode == 1

    if is_quick_play:
        return DifficultyTier(
            tier_name="Quick Play", tier_level=difficulty, is_quick_play=True
        )

    if 1 <= difficulty <= 7:
        return DifficultyTier(tier_name="Contender", tier_level=difficulty)

    if 9 <= difficulty <= 15:
        return DifficultyTier(tier_name="Adept", tier_level=difficulty - 8)

    if 17 <= difficulty <= 23:
        return DifficultyTier(tier_name="Champion", tier_level=difficulty - 16)

    if 25 <= difficulty <= 31:
        return DifficultyTier(tier_name="Paragon", tier_level=difficulty - 24)

    if difficulty >= 33:
        return DifficultyTier(tier_name="Eternal", tier_level=difficulty - 32)

    return DifficultyTier(tier_name="Unknown", tier_level=difficulty)


def format_difficulty(difficulty: int | None, mode: str | int | None = None) -> str:
    """Format difficulty as user-friendly string.

    Args:
        difficulty: Raw difficulty level from combat logs, or None
        mode: Mode flag from logs (0=challenge, 1=quick_play, None=unknown)

    Returns:
        Formatted difficulty string (e.g., "Eternal 45", "Paragon 7", "Quick Play")
        Returns "Unknown" if difficulty is None
    """
    if difficulty is None:
        return "Unknown"

    tier = get_difficulty_tier(difficulty, mode)
    return str(tier)
