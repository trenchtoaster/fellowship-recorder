"""Dungeon metadata for Fellowship including target times for challenge mode."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DungeonCategory(str, Enum):
    """Category of dungeon instance.

    Dungeons are categorized into:
    - Adventures: Shorter instances (~10-15 minutes)
    - Dungeons: Capstone dungeons with multiple bosses (~25-30 minutes)
    - Pinnacle: Weekly high-end challenge dungeons (added in Season 3)
    """

    ADVENTURE = "Adventure"
    DUNGEON = "Dungeon"
    PINNACLE = "Pinnacle"


class DungeonInfo(BaseModel):
    """Metadata for a specific dungeon."""

    dungeon_id: int = Field(description="Dungeon identifier from combat logs")
    name: str = Field(description="Display name of the dungeon")
    category: DungeonCategory = Field(
        description="Type of dungeon (Adventure or Dungeon)"
    )
    target_time_seconds: int | None = Field(
        default=None,
        description="Target completion time in seconds for challenge mode (if known)",
    )

    @property
    def target_time_milliseconds(self) -> int | None:
        """Get target time in milliseconds."""
        if self.target_time_seconds is None:
            return None
        return self.target_time_seconds * 1000

    def format_target_time(self) -> str:
        """Format target time as MM:SS."""
        if self.target_time_seconds is None:
            return "Unknown"
        minutes = self.target_time_seconds // 60
        seconds = self.target_time_seconds % 60
        return f"{minutes}:{seconds:02d}"


DUNGEONS: dict[int, DungeonInfo] = {
    6: DungeonInfo(
        dungeon_id=6,
        name="Empyrean Sands",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=744,
    ),
    8: DungeonInfo(
        dungeon_id=8,
        name="Wyrmheart",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=806,
    ),
    11: DungeonInfo(
        dungeon_id=11,
        name="Everdawn Grove",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=708,
    ),
    12: DungeonInfo(
        dungeon_id=12,
        name="Stormwatch",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=848,
    ),
    15: DungeonInfo(
        dungeon_id=15,
        name="Sailor's Abyss",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=717,
    ),
    21: DungeonInfo(
        dungeon_id=21,
        name="Urrak Markets",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=781,
    ),
    24: DungeonInfo(
        dungeon_id=24,
        name="Silken Hollow",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=812,
    ),
    25: DungeonInfo(
        dungeon_id=25,
        name="Godfall Quarry",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=738,
    ),
    29: DungeonInfo(
        dungeon_id=29,
        name="Ruins of Regath",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=900,
    ),
    31: DungeonInfo(
        dungeon_id=31,
        name="Scryer's Peak",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=807,
    ),
    5: DungeonInfo(
        dungeon_id=5,
        name="The Heart of Tuzari",
        category=DungeonCategory.DUNGEON,
        target_time_seconds=1485,
    ),
    7: DungeonInfo(
        dungeon_id=7,
        name="Cithrel's Fall",
        category=DungeonCategory.DUNGEON,
        target_time_seconds=1671,
    ),
    13: DungeonInfo(
        dungeon_id=13,
        name="Wraithtide Vault",
        category=DungeonCategory.DUNGEON,
        target_time_seconds=1782,
    ),
    23: DungeonInfo(
        dungeon_id=23,
        name="Ransack of Drakheim",
        category=DungeonCategory.DUNGEON,
        target_time_seconds=1740,
    ),
    30: DungeonInfo(
        dungeon_id=30,
        name="Xul, The Blood Monolith",
        category=DungeonCategory.PINNACLE,
        target_time_seconds=1700,
    ),
}


def get_dungeon_info(dungeon_id: int | str) -> DungeonInfo | None:
    """Get dungeon info by ID.

    Args:
        dungeon_id: The dungeon ID from combat logs

    Returns:
        DungeonInfo if found, None otherwise
    """
    if isinstance(dungeon_id, str):
        try:
            dungeon_id = int(dungeon_id)
        except ValueError:
            return None

    return DUNGEONS.get(dungeon_id)


def get_target_time(dungeon_id: int | str) -> int | None:
    """Get target time in seconds for a dungeon.

    Args:
        dungeon_id: The dungeon ID from combat logs

    Returns:
        Target time in seconds, or None if unknown
    """
    info = get_dungeon_info(dungeon_id)
    return info.target_time_seconds if info else None


def format_target_time(dungeon_id: int | str) -> str:
    """Format target time as MM:SS.

    Args:
        dungeon_id: The dungeon ID from combat logs

    Returns:
        Formatted time string (e.g., "11:00") or "Unknown"
    """
    info = get_dungeon_info(dungeon_id)
    return info.format_target_time() if info else "Unknown"
