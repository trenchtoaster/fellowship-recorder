"""Metadata enrichment from combat logs."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .mappings import get_dungeon_info, get_hero_name
from .mappings.dungeons import DungeonCategory
from .metadata import (
    Affix,
    Death,
    Encounter,
    KillObjective,
    Player,
    RecordingMetadata,
    to_utc_iso_string,
)

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Enriches metadata by scanning combat logs."""

    def __init__(self, log_directory: Path) -> None:
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

            encounters = self._extract_encounters(log_file, start_time, end_time)
            if encounters:
                metadata.encounters = encounters

            kill_objective = self._extract_kill_objective(
                log_file, start_time, end_time, metadata.affixes, metadata.dungeon_id
            )
            if kill_objective:
                metadata.kill_objective = kill_objective

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
        self,
        log_file: Path,
        start_time: datetime,
        end_time: datetime,
        players: list[Player],
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
                    occurred_at_str = to_utc_iso_string(timestamp)

                    deaths.append(
                        Death(
                            player_id=player_id,
                            player_name=player_name,
                            hero_id=hero_id,
                            hero_name=hero_name,
                            occurred_at=occurred_at_str,
                            time_offset=death_time_offset,
                        )
                    )

                except Exception:
                    continue

        return deaths

    def _extract_encounters(
        self, log_file: Path, start_time: datetime, end_time: datetime
    ) -> list[Encounter]:
        """Extract boss encounters from combat log.

        Args:
            log_file: Path to combat log file
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of encounters
        """
        encounters = []
        encounter_starts = {}

        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "ENCOUNTER_START" not in line and "ENCOUNTER_END" not in line:
                    continue

                try:
                    parts = line.strip().split("|")
                    timestamp_str = parts[0]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp < start_time:
                        continue
                    if timestamp > end_time:
                        break

                    event_type = parts[1]

                    if len(parts) < 4:
                        continue

                    boss_id = int(parts[2])
                    boss_name = parts[3].strip('[]"')

                    if event_type == "ENCOUNTER_START":
                        start_offset = (timestamp - start_time).total_seconds()
                        encounter_starts[boss_id] = {
                            "boss_name": boss_name,
                            "start_timestamp": start_offset,
                            "start_time": timestamp,
                        }

                    elif event_type == "ENCOUNTER_END":
                        end_offset = (timestamp - start_time).total_seconds()
                        success = bool(int(parts[4])) if len(parts) > 4 else None

                        start_data = encounter_starts.get(boss_id)
                        if start_data:
                            encounters.append(
                                Encounter(
                                    boss_id=boss_id,
                                    boss_name=boss_name,
                                    start_time_offset=start_data["start_timestamp"],
                                    end_time_offset=end_offset,
                                    success=success,
                                )
                            )
                            del encounter_starts[boss_id]
                        else:
                            encounters.append(
                                Encounter(
                                    boss_id=boss_id,
                                    boss_name=boss_name,
                                    start_time_offset=end_offset,
                                    end_time_offset=end_offset,
                                    success=success,
                                )
                            )

                except Exception:
                    continue

        for boss_id, data in encounter_starts.items():
            encounters.append(
                Encounter(
                    boss_id=boss_id,
                    boss_name=data["boss_name"],
                    start_time_offset=data["start_timestamp"],
                    end_time_offset=None,
                    success=None,
                )
            )

        encounters.sort(key=lambda e: e.start_time_offset)
        return encounters

    def _extract_kill_objective(
        self,
        log_file: Path,
        start_time: datetime,
        end_time: datetime,
        affixes: list[Affix] | None,
        dungeon_id: int | None,
    ) -> KillObjective | None:
        """Extract kill objective completion time and final score from combat log.

        For Shadow Lord's Trial affix, the combat log reports kill scores BEFORE
        adding the Emissary kill contribution. We correct this based on dungeon type:
        - Adventure dungeons: 2 Shadowlords at 50% each
        - Regular Dungeons: 3 Shadowlords at 33.33% each

        Args:
            log_file: Path to combat log file
            start_time: Start of time range
            end_time: End of time range
            affixes: List of affix objects to detect Shadow Lord's Trial
            dungeon_id: Dungeon ID to determine category

        Returns:
            KillObjective with completion data, or None if no kills found
        """
        completed_at = None
        completion_offset = None
        final_score = None
        shadowlord_kills = 0
        last_shadowlord_timestamp = None
        orb_count = None

        has_shadowlord_trial = False
        if affixes:
            has_shadowlord_trial = any(affix.affix_id == 19 for affix in affixes)

        if has_shadowlord_trial:
            orb_count = 0.0

        shadowlord_percentage = 50.0
        if has_shadowlord_trial and dungeon_id:
            dungeon_info = get_dungeon_info(dungeon_id)

            if dungeon_info and dungeon_info.category == DungeonCategory.DUNGEON:
                shadowlord_percentage = 100.0 / 3

        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "UNIT_DEATH" not in line:
                    continue

                try:
                    parts = line.strip().split("|")
                    timestamp_str = parts[0]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp < start_time:
                        continue
                    if timestamp > end_time:
                        break

                    if len(parts) < 10:
                        continue

                    unit_name = parts[3].strip('"')
                    is_shadowlord = (
                        has_shadowlord_trial
                        and unit_name == "Emissary of the Shadow Lord"
                    )

                    kill_score_str = parts[9]
                    kill_score = float(kill_score_str)
                    kill_score_percentage = kill_score * 100

                    if is_shadowlord:
                        shadowlord_kills += 1
                        last_shadowlord_timestamp = timestamp
                    elif has_shadowlord_trial and orb_count is not None:
                        orb_count += kill_score

                    final_score = kill_score_percentage

                    if (
                        not has_shadowlord_trial
                        and completed_at is None
                        and kill_score >= 1.0
                    ):
                        completed_at = to_utc_iso_string(timestamp)
                        completion_offset = (timestamp - start_time).total_seconds()

                except (ValueError, IndexError):
                    continue

        if final_score is None:
            return None

        if has_shadowlord_trial and shadowlord_kills > 0:
            final_score = shadowlord_kills * shadowlord_percentage

            if (
                completed_at is None
                and final_score >= 100.0
                and last_shadowlord_timestamp
            ):
                completed_at = to_utc_iso_string(last_shadowlord_timestamp)
                completion_offset = (
                    last_shadowlord_timestamp - start_time
                ).total_seconds()

        return KillObjective(
            completed_at=completed_at,
            completion_offset=completion_offset,
            final_score=final_score,
            orb_count=orb_count,
        )
