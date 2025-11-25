"""Metadata generation for Fellowship recordings."""

import hashlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from .mappings import format_difficulty, get_affix_info, get_mode_name


def to_utc_iso_string(dt_obj: datetime) -> str:
    """Convert datetime to UTC ISO 8601 string with milliseconds and 'Z' suffix.

    Args:
        dt_obj: Datetime object (naive or timezone-aware)

    Returns:
        ISO 8601 UTC string with 'Z' suffix (e.g., "2025-11-25T21:50:55.186Z")
    """
    dt_obj = dt_obj.astimezone(UTC)
    return dt_obj.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


class Affix(BaseModel):
    """Dungeon affix information."""

    affix_id: int = Field(description="Numeric affix ID from combat log")
    affix_name: str = Field(description="Human-readable affix name")
    affix_type: str = Field(description="Affix type (Ascension or Curse)")


class Player(BaseModel, populate_by_name=True):
    """Player in the dungeon."""

    player_id: str = Field(
        description="Unique player identifier"
    )
    player_name: str = Field(description="Player character name")
    hero_id: int = Field(
        description="Numeric hero ID from combat log (from COMBATANT_INFO event)"
    )
    hero_name: str | None = Field(
        default=None, description="Hero name"
    )
    is_recording_player: bool = Field(
        default=False, description="True if this is the player recording"
    )
    item_level: float | None = Field(default=None, description="Average item level")


class Death(BaseModel):
    """A player death during the dungeon."""

    player_id: str = Field(description="Unique player identifier")
    player_name: str = Field(description="Name of the player who died")
    hero_id: int = Field(description="Hero ID the player was using")
    hero_name: str | None = Field(default=None, description="Hero name")
    occurred_at: str = Field(description="ISO 8601 UTC timestamp when death occurred")
    time_offset: float = Field(ge=0, description="Seconds since dungeon start")


class Encounter(BaseModel):
    """A boss encounter during the dungeon."""

    boss_id: int = Field(description="Numeric boss ID from combat log")
    boss_name: str = Field(description="Name of the boss")
    start_time_offset: float = Field(ge=0, description="Seconds since dungeon start when encounter began")
    end_time_offset: float | None = Field(default=None, ge=0, description="Seconds since dungeon start when encounter ended")
    success: bool | None = Field(default=None, description="Whether the boss was defeated (True) or wiped (False)")


class Chapter(BaseModel):
    """A chapter marker in the recording."""

    title: str = Field(description="Chapter title")
    time_offset: float = Field(ge=0, description="Seconds since recording started (includes configured offset for context)")


class RecordingMetadata(BaseModel, populate_by_name=True):
    """Metadata for a Fellowship recording."""

    started_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp when dungeon started"
    )
    ended_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp when dungeon ended"
    )
    duration: float = Field(ge=0, description="Duration of recording in seconds")
    result: bool = Field(description="Whether the dungeon was completed successfully")

    dungeon_id: int | None = Field(default=None, description="Dungeon ID")
    dungeon_name: str | None = Field(
        default=None, description="Human-readable dungeon name"
    )
    difficulty_id: int | None = Field(default=None, ge=0, description="Difficulty level")
    difficulty_name: str | None = Field(
        default=None,
        description="User-friendly difficulty ('Eternal 45', 'Paragon 7', 'Quick Play', etc.)",
    )
    mode_id: str | None = Field(
        default=None, description="Dungeon mode ID (0=challenge, 1=quick_play)"
    )
    mode_name: str | None = Field(
        default=None, description="User-friendly mode name ('Challenge', 'Quick Play')"
    )
    affixes: list[Affix] | None = Field(
        default=None,
        description="List of dungeon affixes with IDs and names",
    )
    party: list[Player] = Field(
        default_factory=list, description="List of party members"
    )
    encounters: list[Encounter] | None = Field(
        default=None, description="List of boss encounters during run"
    )
    deaths: list[Death] | None = Field(
        default=None, description="List of player deaths during run"
    )
    chapters: list[Chapter] | None = Field(
        default=None, description="Chapter markers for encounters and events"
    )
    unique_hash: str | None = Field(
        default=None, description="Unique hash identifying this run"
    )
    overrun: int = Field(
        default=0,
        ge=0,
        exclude=True,
        description="Overrun time in seconds after dungeon end",
    )

    def to_json(self, path: Path) -> None:
        """Write metadata to JSON file.

        Args:
            path: Path to write JSON file
        """
        with path.open("w") as f:
            f.write(self.model_dump_json(indent=2, exclude_none=True))

    @staticmethod
    def from_dungeon(
        dungeon_name: str,
        dungeon_id: int | None,
        difficulty_id: int | None,
        duration: float,
        result: bool,
        start_time: datetime,
        mode_id: str | None = None,
        affixes: list[int] | None = None,
    ) -> RecordingMetadata:
        """Create metadata for a Fellowship dungeon.

        Args:
            dungeon_name: Name of the dungeon
            dungeon_id: Dungeon ID
            difficulty_id: Difficulty level
            duration: Duration in seconds
            result: Whether dungeon was completed successfully
            start_time: When the run started
            mode_id: Dungeon mode ID (0=challenge, 1=quick_play)
            affixes: List of dungeon affix IDs

        Returns:
            RecordingMetadata instance
        """
        hash_input = f"{dungeon_name}{difficulty_id}{start_time.isoformat()}"
        unique_hash = hashlib.md5(hash_input.encode()).hexdigest()

        affix_list = None
        if affixes:
            affix_list = []
            for affix_id in affixes:
                affix_info = get_affix_info(affix_id)
                if affix_info:
                    affix_list.append(
                        Affix(
                            affix_id=affix_id,
                            affix_name=affix_info["name"],
                            affix_type=affix_info["type"],
                        )
                    )

        started_at_str = to_utc_iso_string(start_time)
        end_time = start_time + timedelta(seconds=duration)
        ended_at_str = to_utc_iso_string(end_time)

        return RecordingMetadata(
            started_at=started_at_str,
            ended_at=ended_at_str,
            duration=duration,
            result=result,
            dungeon_id=dungeon_id,
            dungeon_name=dungeon_name,
            difficulty_id=difficulty_id,
            mode_id=mode_id,
            mode_name=get_mode_name(mode_id),
            affixes=affix_list,
            difficulty_name=format_difficulty(difficulty_id, mode_id),
            unique_hash=unique_hash,
        )
