"""Combat log parser for detecting Fellowship activities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventType(Enum):
    """Types of events we detect from the combat log."""

    DUNGEON_START = "DUNGEON_START"
    DUNGEON_END = "DUNGEON_END"
    ENCOUNTER_START = "ENCOUNTER_START"
    ENCOUNTER_END = "ENCOUNTER_END"
    UNIT_DEATH = "UNIT_DEATH"
    ALLY_DEATH = "ALLY_DEATH"
    ZONE_CHANGE = "ZONE_CHANGE"
    LOGGING_STARTED = "LOGGING_STARTED"
    UNKNOWN = "UNKNOWN"


class CombatLogEvent(BaseModel):
    """Parsed combat log event."""

    timestamp: datetime = Field(description="When the event occurred")
    event_type: EventType = Field(
        description="Type of event (DUNGEON_START, DUNGEON_END, etc.)"
    )
    raw_line: str = Field(description="Original raw line from combat log")
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Event-specific metadata parsed from log parameters",
    )

    @property
    def is_start_event(self) -> bool:
        """Check if this is a start event.

        Returns True for:
        - DUNGEON_START events
        - ZONE_CHANGE events where dungeon_id != 17 (leaving Stronghold to enter dungeon)
        """
        if self.event_type == EventType.DUNGEON_START:
            return True

        if self.event_type == EventType.ZONE_CHANGE:
            dungeon_id = self.metadata.get("dungeon_id")
            return dungeon_id is not None and dungeon_id != "17"

        return False

    @property
    def is_end_event(self) -> bool:
        """Check if this is an end event.

        Returns True for:
        - DUNGEON_END events
        - ZONE_CHANGE events where dungeon_id == 17 (returning to Stronghold)
        """
        if self.event_type == EventType.DUNGEON_END:
            return True

        if self.event_type == EventType.ZONE_CHANGE:
            dungeon_id = self.metadata.get("dungeon_id")
            return dungeon_id == "17"

        return False


class CombatLogParser:
    """Parser for Fellowship combat log files."""

    def parse_line(self, line: str) -> CombatLogEvent | None:
        """Parse a single line from the combat log.

        Args:
            line: Raw line from CombatLog*.txt

        Returns:
            CombatLogEvent if the line contains a recordable event, None otherwise
        """
        try:
            line = line.strip()
            if not line:
                return None

            parts = line.split("|")
            if len(parts) < 2:
                return None

            timestamp_str = parts[0]
            event_name = parts[1]

            timestamp = self._parse_timestamp(timestamp_str)
            if timestamp is None:
                return None

            try:
                event_type = EventType(event_name)
            except ValueError:
                return None

            metadata = {}
            if len(parts) > 2:
                metadata = self._parse_metadata(event_type, parts[2:])

            return CombatLogEvent(
                timestamp=timestamp,
                event_type=event_type,
                raw_line=line,
                metadata=metadata,
            )
        except Exception:
            return None

    def _parse_timestamp(self, timestamp_str: str) -> datetime | None:
        """Parse Fellowship combat log timestamp.

        Format: ISO 8601 with timezone

        Returns:
            Parsed datetime or None if parsing fails
        """
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError):
            return None

    def _parse_metadata(
        self, event_type: EventType, params: list[str]
    ) -> dict[str, str]:
        """Parse event-specific metadata.

        Args:
            event_type: Type of event
            params: List of pipe-separated parameters

        Returns:
            Dictionary of metadata
        """
        metadata: dict[str, str] = {}

        if event_type == EventType.ENCOUNTER_START:
            if len(params) >= 1:
                metadata["encounter_id"] = params[0]
            if len(params) >= 2:
                boss_name = params[1].strip('[]"')
                metadata["encounter_name"] = boss_name

        elif event_type == EventType.ENCOUNTER_END:
            if len(params) >= 1:
                metadata["encounter_id"] = params[0]
            if len(params) >= 2:
                boss_name = params[1].strip('[]"')
                metadata["encounter_name"] = boss_name
            if len(params) >= 3:
                metadata["success"] = params[2]

        elif event_type == EventType.DUNGEON_START:
            if len(params) >= 1:
                metadata["dungeon_name"] = params[0].strip('"')
            if len(params) >= 2:
                metadata["dungeon_id"] = params[1]
            if len(params) >= 3:
                metadata["difficulty_id"] = params[2]
            if len(params) >= 4:
                metadata["affixes"] = params[3]
            if len(params) >= 5:
                metadata["mode"] = params[4]

        elif event_type == EventType.DUNGEON_END:
            if len(params) >= 1:
                metadata["dungeon_name"] = params[0].strip('"')
            if len(params) >= 2:
                metadata["dungeon_id"] = params[1]
            if len(params) >= 3:
                metadata["difficulty_id"] = params[2]
            if len(params) >= 4:
                metadata["affixes"] = params[3]
            if len(params) >= 5:
                metadata["mode"] = params[4]
            if len(params) >= 6:
                metadata["duration"] = params[5]
            if len(params) >= 7:
                metadata["remaining_time"] = params[6]
            if len(params) >= 8:
                metadata["success"] = params[7]

        elif event_type == EventType.UNIT_DEATH:
            if len(params) >= 2:
                metadata["unit_name"] = params[1].strip('"')
            if len(params) >= 8:
                metadata["kill_score"] = params[7]

        elif event_type == EventType.ALLY_DEATH:
            if len(params) >= 2:
                metadata["player_name"] = params[1].strip('"')

        elif event_type == EventType.ZONE_CHANGE:
            if len(params) >= 1:
                metadata["dungeon_name"] = params[0].strip('"')
            if len(params) >= 2:
                metadata["dungeon_id"] = params[1]
            if len(params) >= 3:
                metadata["difficulty_id"] = params[2]

        return metadata
