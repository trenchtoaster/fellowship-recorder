"""Tests for metadata enrichment from combat logs."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fellowship_recorder.enrichment import MetadataEnricher
from fellowship_recorder.metadata import RecordingMetadata


@pytest.fixture
def log_directory(tmp_path):
    """Create a temporary log directory."""
    return tmp_path / "logs"


@pytest.fixture
def enricher(log_directory):
    """Create a MetadataEnricher instance."""
    log_directory.mkdir(exist_ok=True)
    return MetadataEnricher(log_directory)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for enrichment."""
    return RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=605.0,
        result=True,
        start_time=datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc),
    )


class TestMetadataEnricher:
    """Test metadata enrichment."""

    def test_enricher_initialization(self, log_directory):
        """Test enricher can be initialized."""
        enricher = MetadataEnricher(log_directory)
        assert enricher.log_directory == log_directory

    def test_enrich_no_log_file(self, enricher, sample_metadata):
        """Test enrichment when no log file exists."""
        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        enriched = enricher.enrich_metadata(sample_metadata, start_time, end_time)

        assert enriched.party == []
        assert enriched.deaths is None

    def test_find_log_file_by_date(self, enricher, log_directory):
        """Test finding log file by date pattern."""
        log_file = log_directory / "CombatLog241125_083000.txt"
        log_file.touch()

        timestamp = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        found = enricher._find_log_file(timestamp)

        assert found == log_file

    def test_find_log_file_multiple_files(self, enricher, log_directory):
        """Test finding correct log file when multiple exist."""
        log_file1 = log_directory / "CombatLog241125_080000.txt"
        log_file2 = log_directory / "CombatLog241125_083000.txt"
        log_file3 = log_directory / "CombatLog241125_090000.txt"

        log_file1.touch()
        log_file2.touch()
        log_file3.touch()

        timestamp = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        found = enricher._find_log_file(timestamp)

        assert found == log_file2

    def test_find_log_file_no_match(self, enricher, log_directory):
        """Test finding log file when date doesn't match."""
        log_file = log_directory / "CombatLog231125_083000.txt"
        log_file.touch()

        timestamp = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        found = enricher._find_log_file(timestamp)

        assert found is None

    def test_extract_players_from_log(self, enricher, log_directory, sample_metadata):
        """Test extracting player information from combat log."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:36:20.000+00:00|COMBATANT_INFO|1|Player-1000|"Player1"|1|5|450.5
2025-11-24T08:36:21.000+00:00|COMBATANT_INFO|1|Player-2000|"Player2"|0|3|425.0
2025-11-24T08:36:22.000+00:00|COMBATANT_INFO|1|Player-3000|"Player3"|0|7|475.2
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        players = enricher._extract_players(log_file, start_time, end_time)

        assert len(players) == 3
        assert players[0].player_id == "Player-1000"
        assert players[0].player_name == "Player1"
        assert players[0].hero_id == 5
        assert players[0].is_recording_player is True
        assert players[0].item_level == 450.5

        assert players[1].player_id == "Player-2000"
        assert players[1].player_name == "Player2"
        assert players[1].is_recording_player is False
        assert players[1].item_level == 425.0

    def test_extract_players_time_filter(self, enricher, log_directory):
        """Test that player extraction respects time boundaries."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:35:00.000+00:00|COMBATANT_INFO|1|Player-1000|"Early"|1|5|450.5
2025-11-24T08:36:20.000+00:00|COMBATANT_INFO|1|Player-2000|"During"|0|3|425.0
2025-11-24T08:50:00.000+00:00|COMBATANT_INFO|1|Player-3000|"Late"|0|7|475.2
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        players = enricher._extract_players(log_file, start_time, end_time)

        assert len(players) == 1
        assert players[0].player_name == "During"

    def test_extract_deaths_from_log(self, enricher, log_directory):
        """Test extracting death events from combat log."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:36:20.000+00:00|COMBATANT_INFO|1|Player-1000|"Player1"|1|5|450.5
2025-11-24T08:36:21.000+00:00|COMBATANT_INFO|1|Player-2000|"Player2"|0|3|425.0
2025-11-24T08:40:00.000+00:00|ALLY_DEATH|Player-1000|"Player1"|Npc-123|"Boss"|123|"Strike"|0|0
2025-11-24T08:42:00.000+00:00|ALLY_DEATH|Player-2000|"Player2"|Npc-456|"Minion"|456|"Blast"|0|0
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        players = enricher._extract_players(log_file, start_time, end_time)
        deaths = enricher._extract_deaths(log_file, start_time, end_time, players)

        assert len(deaths) == 2

        assert deaths[0].player_id == "Player-1000"
        assert deaths[0].player_name == "Player1"
        assert deaths[0].hero_id == 5
        assert deaths[0].timestamp == pytest.approx(221.0)

        assert deaths[1].player_id == "Player-2000"
        assert deaths[1].player_name == "Player2"
        assert deaths[1].hero_id == 3
        assert deaths[1].timestamp == pytest.approx(341.0)

    def test_extract_deaths_time_filter(self, enricher, log_directory):
        """Test that death extraction respects time boundaries."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:35:00.000+00:00|ALLY_DEATH|Player-1000|"Early"|Npc-123|"Boss"|123|"Strike"|0|0
2025-11-24T08:40:00.000+00:00|ALLY_DEATH|Player-2000|"During"|Npc-456|"Minion"|456|"Blast"|0|0
2025-11-24T08:50:00.000+00:00|ALLY_DEATH|Player-3000|"Late"|Npc-789|"Boss2"|789|"Smash"|0|0
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        deaths = enricher._extract_deaths(log_file, start_time, end_time, [])

        assert len(deaths) == 1
        assert deaths[0].player_name == "During"

    def test_enrich_metadata_full(self, enricher, log_directory, sample_metadata):
        """Test full metadata enrichment with players and deaths."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:36:20.000+00:00|COMBATANT_INFO|1|Player-1000|"Player1"|1|5|450.5
2025-11-24T08:36:21.000+00:00|COMBATANT_INFO|1|Player-2000|"Player2"|0|3|425.0
2025-11-24T08:40:00.000+00:00|ALLY_DEATH|Player-1000|"Player1"|Npc-123|"Boss"|123|"Strike"|0|0
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        enriched = enricher.enrich_metadata(sample_metadata, start_time, end_time)

        assert len(enriched.party) == 2
        assert enriched.party[0].player_name == "Player1"
        assert enriched.party[1].player_name == "Player2"

        assert enriched.deaths is not None
        assert len(enriched.deaths) == 1
        assert enriched.deaths[0].player_name == "Player1"

    def test_extract_players_malformed_lines(self, enricher, log_directory):
        """Test that malformed lines don't crash extraction."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:36:20.000+00:00|COMBATANT_INFO|1|Player-1000|"Player1"|1|5|450.5
invalid line without enough fields
2025-11-24T08:36:21.000+00:00|COMBATANT_INFO|incomplete
|||||||
2025-11-24T08:36:22.000+00:00|COMBATANT_INFO|1|Player-2000|"Player2"|0|3|425.0
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        players = enricher._extract_players(log_file, start_time, end_time)

        assert len(players) == 2

    def test_extract_deaths_malformed_lines(self, enricher, log_directory):
        """Test that malformed death lines don't crash extraction."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:40:00.000+00:00|ALLY_DEATH|Player-1000|"Player1"|Npc-123|"Boss"|123|"Strike"|0|0
invalid death line
2025-11-24T08:41:00.000+00:00|ALLY_DEATH|incomplete
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        deaths = enricher._extract_deaths(log_file, start_time, end_time, [])

        assert len(deaths) == 1

    def test_extract_players_duplicate_player(self, enricher, log_directory):
        """Test that duplicate player entries are deduplicated."""
        log_file = log_directory / "CombatLog241125_083000.txt"

        log_content = """2025-11-24T08:36:20.000+00:00|COMBATANT_INFO|1|Player-1000|"Player1"|1|5|450.5
2025-11-24T08:36:25.000+00:00|COMBATANT_INFO|1|Player-1000|"Player1"|1|5|450.5
2025-11-24T08:36:30.000+00:00|COMBATANT_INFO|1|Player-2000|"Player2"|0|3|425.0
"""
        log_file.write_text(log_content)

        start_time = datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 24, 8, 46, 19, tzinfo=timezone.utc)

        players = enricher._extract_players(log_file, start_time, end_time)

        assert len(players) == 2
