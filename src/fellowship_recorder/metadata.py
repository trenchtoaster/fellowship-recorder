"""Metadata generation for Fellowship recordings."""

import hashlib
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .mappings import format_difficulty, get_affix_info, get_affix_name, get_mode_name


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
    date: str = Field(description="Human-readable date/time of death")
    timestamp: float = Field(ge=0, description="Seconds since dungeon start")


class Chapter(BaseModel):
    """A chapter marker in the recording."""

    title: str = Field(description="Chapter title")
    timestamp: float = Field(ge=0, description="Seconds since recording started")


class RecordingMetadata(BaseModel, populate_by_name=True):
    """Metadata for a Fellowship recording."""

    duration: float = Field(ge=0, description="Duration of recording in seconds")
    result: bool = Field(description="Whether the dungeon was completed successfully")
    party: list[Player] = Field(
        default_factory=list, description="List of party members"
    )
    overrun: int = Field(
        default=0,
        ge=0,
        exclude=True,
        description="Overrun time in seconds after dungeon end",
    )
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
    deaths: list[Death] | None = Field(
        default=None, description="List of player deaths during run"
    )
    chapters: list[Chapter] | None = Field(
        default=None, description="Chapter markers for encounters and events"
    )

    start: int | None = Field(
        default=None, description="Unix timestamp (milliseconds) when dungeon started"
    )
    unique_hash: str | None = Field(
        default=None, description="Unique hash identifying this run"
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

        return RecordingMetadata(
            duration=duration,
            result=result,
            dungeon_id=dungeon_id,
            dungeon_name=dungeon_name,
            difficulty_id=difficulty_id,
            mode_id=mode_id,
            mode_name=get_mode_name(mode_id),
            affixes=affix_list,
            difficulty_name=format_difficulty(difficulty_id, mode_id),
            start=int(start_time.timestamp() * 1000),
            unique_hash=unique_hash,
        )
