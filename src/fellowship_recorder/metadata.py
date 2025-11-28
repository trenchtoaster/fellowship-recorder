"""Metadata generation for Fellowship recordings."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .mappings import (
    format_difficulty,
    get_affix_info,
    get_mode_name,
    get_target_time,
)


def to_utc_iso_string(dt_obj: datetime) -> str:
    """Convert datetime to UTC ISO 8601 string with milliseconds and 'Z' suffix.

    Args:
        dt_obj: Datetime object (naive or timezone-aware)

    Returns:
        ISO 8601 UTC string with 'Z' suffix (e.g., "2025-11-25T21:50:55.186Z")
    """
    dt_obj = dt_obj.astimezone(UTC)
    return dt_obj.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Affix(BaseModel):
    """Dungeon affix information."""

    affix_id: int = Field(description="Numeric affix ID from combat log")
    affix_name: str = Field(description="Human-readable affix name")
    affix_type: str = Field(description="Affix type (Ascension or Curse)")


class Player(BaseModel, populate_by_name=True):
    """Player in the dungeon."""

    player_id: str = Field(description="Unique player identifier")
    player_name: str = Field(description="Player character name")
    hero_id: int = Field(
        description="Numeric hero ID from combat log (from COMBATANT_INFO event)"
    )
    hero_name: str | None = Field(default=None, description="Hero name")
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
    start_time_offset: float = Field(
        ge=0, description="Seconds since dungeon start when encounter began"
    )
    end_time_offset: float | None = Field(
        default=None,
        ge=0,
        description="Seconds since dungeon start when encounter ended",
    )
    success: bool | None = Field(
        default=None,
        description="Whether the boss was defeated (True) or wiped (False)",
    )


class Chapter(BaseModel):
    """A chapter marker in the recording."""

    title: str = Field(description="Chapter title")
    time_offset: float = Field(
        ge=0,
        description="Seconds since recording started (includes configured offset)",
    )


class KillObjective(BaseModel):
    """Kill score objective completion data."""

    completed_at: str | None = Field(
        default=None,
        description="ISO 8601 UTC timestamp when kill score objective completed (score >= 1.0)",
    )
    completion_offset: float | None = Field(
        default=None,
        ge=0,
        description="Time offset in seconds from dungeon start when kill score objective completed",
    )
    final_score: float | None = Field(
        default=None,
        ge=0,
        description="Final kill score as percentage",
    )
    orb_count: float | None = Field(
        default=None,
        ge=0,
        description="Total orbs collected (Shadow Lord's Trial only). 30 orbs spawn the Shadow Lord.",
    )


class RecordingMetadata(BaseModel, populate_by_name=True):
    """Metadata for a Fellowship recording."""

    started_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp when dungeon started"
    )
    ended_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp when dungeon ended"
    )
    duration: float = Field(ge=0, description="Duration of recording in seconds")
    target_time: float | None = Field(
        default=None,
        description="Target completion time in seconds for challenge mode (None if quick play or unknown)",
    )
    remaining_time: float | None = Field(
        default=None,
        description="Time remaining when completed in seconds (challenge mode only, None if target time unknown)",
    )
    completed: bool = Field(
        description="Whether the dungeon run finished (vs abandoned due to crash/quit)"
    )
    success: bool = Field(
        description="Whether the dungeon was successful (vs failed timer/wipe)"
    )

    dungeon_id: int | None = Field(default=None, description="Dungeon ID")
    dungeon_name: str | None = Field(
        default=None, description="Human-readable dungeon name"
    )
    difficulty_id: int | None = Field(
        default=None, ge=0, description="Difficulty level"
    )
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
    kill_objective: KillObjective | None = Field(
        default=None, description="Kill objective completion data"
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

    @property
    def result_status(self) -> str:
        """Get the result status of the run."""
        if self.success:
            return "Success"

        if self.remaining_time is not None and self.remaining_time <= 0:
            return "Failed"

        return "Abandoned"

    def to_json(self, path: Path) -> None:
        """Write metadata to JSON file.

        Args:
            path: Path to write JSON file
        """
        with path.open("w") as f:
            f.write(self.model_dump_json(indent=2, exclude_none=True))

    def generate_chapters(
        self,
        boss_markers: bool = True,
        death_markers: bool = True,
        chapter_offset: int = 5,
    ) -> list[Chapter]:
        """Generate chapter markers from encounters and deaths.

        Args:
            boss_markers: Whether to include boss encounter markers
            death_markers: Whether to include death markers
            chapter_offset: Seconds to offset chapter markers backward

        Returns:
            List of Chapter objects sorted by time offset
        """
        chapters = []

        if death_markers and self.deaths:
            player_to_hero = {
                d.player_name: d.hero_name for d in self.deaths if d.hero_name
            }
            for death in self.deaths:
                player_name = death.player_name

                if player_name in player_to_hero:
                    title = f"Death: {player_to_hero[player_name]}"
                else:
                    title = f"Death: {player_name}"

                time_offset = max(0, death.time_offset - chapter_offset)
                chapters.append(
                    Chapter(
                        title=title,
                        time_offset=time_offset,
                    )
                )

        boss_attempts = defaultdict(int)
        if boss_markers and self.encounters:
            for encounter in self.encounters:
                boss_attempts[encounter.boss_id] += 1
                attempt_num = boss_attempts[encounter.boss_id]

                if encounter.success:
                    title = f"{encounter.boss_name} (Kill)"
                else:
                    title = f"{encounter.boss_name} (Attempt {attempt_num})"

                time_offset = max(0, encounter.start_time_offset - chapter_offset)

                chapters.append(
                    Chapter(
                        title=title,
                        time_offset=time_offset,
                    )
                )

        chapters.sort(key=lambda c: c.time_offset)
        return chapters

    @staticmethod
    def from_dungeon(
        dungeon_name: str,
        dungeon_id: int | None,
        difficulty_id: int | None,
        duration: float,
        completed: bool,
        success: bool,
        start_time: datetime,
        end_time: datetime | None = None,
        mode_id: str | None = None,
        affixes: list[int] | None = None,
    ) -> RecordingMetadata:
        """Create metadata for a Fellowship dungeon.

        Args:
            dungeon_name: Name of the dungeon
            dungeon_id: Dungeon ID
            difficulty_id: Difficulty level
            duration: Duration in seconds
            completed: Whether the dungeon run finished (vs abandoned)
            success: Whether the dungeon was successful (vs failed)
            start_time: When the run started
            end_time: When the run ended (if None, calculated from start_time + duration)
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
        ended_at_str = to_utc_iso_string(end_time) if end_time is not None else None

        target_time_value = None
        remaining_time = None
        if mode_id == "0" and dungeon_id is not None:
            target_time_value = get_target_time(dungeon_id)

            if target_time_value is not None:
                remaining_time = target_time_value - duration

        return RecordingMetadata(
            started_at=started_at_str,
            ended_at=ended_at_str,
            duration=duration,
            target_time=target_time_value,
            remaining_time=remaining_time,
            completed=completed,
            success=success,
            dungeon_id=dungeon_id,
            dungeon_name=dungeon_name,
            difficulty_id=difficulty_id,
            mode_id=mode_id,
            mode_name=get_mode_name(mode_id),
            affixes=affix_list,
            difficulty_name=format_difficulty(difficulty_id, mode_id),
            unique_hash=unique_hash,
        )
