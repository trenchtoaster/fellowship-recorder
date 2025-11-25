"""Metadata enrichment from combat logs."""

import logging
from datetime import datetime
from pathlib import Path

from .mappings import get_hero_name
from .metadata import Death, Player, RecordingMetadata

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Enriches metadata by scanning combat logs."""

    def __init__(self, log_directory: Path):
        """Initialize enricher.

        Args:
            log_directory: Path to Fellowship combat log directory
        """
        self.log_directory = log_directory

    def enrich_metadata(
        self,
        metadata: RecordingMetadata,
        start_time: datetime,
        end_time: datetime,
    ) -> RecordingMetadata:
        """Enrich metadata by scanning combat log.

        Args:
            metadata: Base metadata to enrich
            start_time: When recording started
            end_time: When recording ended

        Returns:
            Enriched metadata
        """
        log_file = self._find_log_file(start_time)
        if not log_file or not log_file.exists():
            return metadata

        try:
            players = self._extract_players(log_file, start_time, end_time)
            metadata.party = players

            deaths = self._extract_deaths(log_file, start_time, end_time, players)
            if deaths:
                metadata.deaths = deaths

        except Exception as e:
            logger.error(f"Error enriching metadata: {e}")

        return metadata

    def _find_log_file(self, timestamp: datetime) -> Path | None:
        """Find the combat log file for a given timestamp.

        Args:
            timestamp: Timestamp to search for

        Returns:
            Path to log file or None
        """
        date_str = timestamp.strftime("%d%m%y")
        pattern = f"CombatLog{date_str}_*.txt"

        matching_files = sorted(self.log_directory.glob(pattern))
        if not matching_files:
            return None

        for log_file in reversed(matching_files):
            try:
                file_time_str = log_file.stem.split("_")[1]
                file_time = datetime.strptime(
                    f"{date_str}_{file_time_str}", "%d%m%y_%H%M%S"
                ).replace(tzinfo=timestamp.tzinfo)

                if file_time <= timestamp:
                    return log_file
            except (IndexError, ValueError):
                continue

        return matching_files[-1]

    def _extract_players(
        self, log_file: Path, start_time: datetime, end_time: datetime
    ) -> list[Player]:
        """Extract player information from combat log.

        Args:
            log_file: Path to combat log file
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of combatants
        """
        players = {}

        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    if "COMBATANT_INFO" not in line:
                        continue

                    parts = line.strip().split("|")
                    if len(parts) < 8:
                        continue

                    timestamp_str = parts[0]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp < start_time:
                        continue
                    if timestamp > end_time:
                        break

                    player_id = parts[3]
                    player_name = parts[4].strip('"')
                    is_recording_player = bool(int(parts[5]))
                    hero_id = int(parts[6])
                    item_level = float(parts[7]) if parts[7] else None

                    if player_id not in players:
                        players[player_id] = Player(
                            player_id=player_id,
                            player_name=player_name,
                            hero_id=hero_id,
                            hero_name=get_hero_name(hero_id),
                            is_recording_player=is_recording_player,
                            item_level=item_level,
                        )

                except Exception:
                    continue

        return list(players.values())

    def _extract_deaths(
        self, log_file: Path, start_time: datetime, end_time: datetime, players: list[Player]
    ) -> list[Death]:
        """Extract player deaths from combat log.

        Args:
            log_file: Path to combat log file
            start_time: Start of time range
            end_time: End of time range
            players: List of players in the party (for hero lookup)

        Returns:
            List of deaths
        """
        deaths = []
        player_lookup = {p.player_id: p for p in players}

        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "ALLY_DEATH" not in line:
                    continue

                try:
                    parts = line.strip().split("|")
                    timestamp_str = parts[0]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp < start_time:
                        continue
                    if timestamp > end_time:
                        break

                    if len(parts) < 4:
                        continue

                    player_id = parts[2]
                    player_name = parts[3].strip('"')

                    player = player_lookup.get(player_id)
                    hero_id = player.hero_id if player else 0
                    hero_name = player.hero_name if player else None

                    death_time_offset = (timestamp - start_time).total_seconds()

                    deaths.append(
                        Death(
                            player_id=player_id,
                            player_name=player_name,
                            hero_id=hero_id,
                            hero_name=hero_name,
                            date=timestamp.isoformat(),
                            timestamp=death_time_offset,
                        )
                    )

                except Exception:
                    continue

        return deaths
