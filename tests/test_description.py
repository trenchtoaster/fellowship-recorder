"""Tests for video description generation."""

from datetime import datetime
from pathlib import Path

import pytest

from fellowship_recorder.description import format_timestamp, generate_video_description
from fellowship_recorder.metadata import Affix, Chapter, Death, Player, RecordingMetadata


class TestFormatTimestamp:
    """Test timestamp formatting."""

    def test_format_seconds_only(self):
        """Test formatting timestamps under a minute."""
        assert format_timestamp(0) == "0:00"
        assert format_timestamp(15) == "0:15"
        assert format_timestamp(45) == "0:45"

    def test_format_minutes_and_seconds(self):
        """Test formatting timestamps in minutes."""
        assert format_timestamp(60) == "1:00"
        assert format_timestamp(90) == "1:30"
        assert format_timestamp(125) == "2:05"
        assert format_timestamp(599) == "9:59"

    def test_format_hours(self):
        """Test formatting timestamps with hours."""
        assert format_timestamp(3600) == "1:00:00"
        assert format_timestamp(3661) == "1:01:01"
        assert format_timestamp(7325) == "2:02:05"

    def test_format_with_decimals(self):
        """Test formatting with decimal seconds."""
        assert format_timestamp(90.5) == "1:30"
        assert format_timestamp(125.9) == "2:05"

    def test_format_large_values(self):
        """Test formatting very long durations."""
        assert format_timestamp(36000) == "10:00:00"


class TestGenerateVideoDescription:
    """Test video description generation."""

    def test_description_with_basic_metadata(self):
        """Test description with just dungeon name and difficulty."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Ransack of Drakheim",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime(2025, 11, 24, 8, 36, 19),
        )

        description = generate_video_description(metadata)

        assert "Ransack of Drakheim" in description
        assert "Paragon 7" in description

    def test_description_with_chapters(self):
        """Test description includes chapter markers."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime.now(),
        )

        metadata.chapters = [
            Chapter(title="Boss Fight", timestamp=60.0),
            Chapter(title="Final Boss", timestamp=300.0),
        ]

        description = generate_video_description(metadata)

        assert "Chapters:" in description
        assert "0:00 Start" in description
        assert "1:00 Boss Fight" in description
        assert "5:00 Final Boss" in description

    def test_description_with_party(self):
        """Test description includes party members."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime.now(),
        )

        metadata.party = [
            Player(
                player_id="Player-1",
                player_name="Player1",
                hero_id=2,
                hero_name="Elarion",
            ),
            Player(
                player_id="Player-2",
                player_name="Player2",
                hero_id=7,
                hero_name="Ardeos",
            ),
        ]

        description = generate_video_description(metadata)

        assert "Party:" in description
        assert "Elarion" in description
        assert "Ardeos" in description

    def test_description_with_affixes(self):
        """Test description includes Curse affixes but filters out Ascension affixes."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime.now(),
            affixes=[6, 4, 8, 11],
        )

        description = generate_video_description(metadata)

        assert "Affixes:" in description
        assert "Asha's Dilemma" not in description
        assert "Vayr's Legacy" not in description
        assert "Blood Shards" in description
        assert "Binding Ice" in description

    def test_description_with_all_metadata(self):
        """Test description with all metadata populated."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Ransack of Drakheim",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime.now(),
            affixes=[6, 4, 8],
        )

        metadata.party = [
            Player(
                player_id="Player-1",
                player_name="Player1",
                hero_id=2,
                hero_name="Elarion",
            )
        ]

        metadata.chapters = [
            Chapter(title="Boss Fight", timestamp=60.0),
        ]

        description = generate_video_description(metadata)

        assert "Ransack of Drakheim" in description
        assert "Paragon 7" in description
        assert "Chapters:" in description
        assert "Boss Fight" in description
        assert "Party:" in description
        assert "Elarion" in description
        assert "Affixes:" in description
        assert "Blood Shards" in description
        assert "Asha's Dilemma" not in description

    def test_description_empty_metadata(self):
        """Test description with minimal metadata."""
        metadata = RecordingMetadata(
            duration=100.0,
            result=True,
        )

        description = generate_video_description(metadata)

        assert description is not None
        assert isinstance(description, str)

    def test_description_party_without_hero_names(self):
        """Test description with party members missing hero names."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime.now(),
        )

        metadata.party = [
            Player(
                player_id="Player-1",
                player_name="Player1",
                hero_id=99,
                hero_name=None,
            )
        ]

        description = generate_video_description(metadata)

        assert "Party:" in description
        assert "Hero 99" in description

    def test_description_chapters_with_hours(self):
        """Test chapter timestamps with hour-long videos."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=31,
            duration=7200.0,
            result=True,
            start_time=datetime.now(),
        )

        metadata.chapters = [
            Chapter(title="Mid Point", timestamp=3600.0),
        ]

        description = generate_video_description(metadata)

        assert "1:00:00 Mid Point" in description

    def test_description_death_chapters_use_hero_names(self):
        """Test that death chapters use hero names instead of player names for privacy."""
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            result=True,
            start_time=datetime.now(),
        )

        metadata.party = [
            Player(
                player_id="Player-123",
                player_name="PlayerName123",
                hero_id=2,
                hero_name="Elarion",
            )
        ]

        metadata.deaths = [
            Death(
                player_id="Player-123",
                player_name="PlayerName123",
                hero_id=2,
                hero_name="Elarion",
                date="2025-11-25T10:30:00",
                timestamp=120.0,
            )
        ]

        metadata.chapters = [
            Chapter(title="Death: PlayerName123", timestamp=120.0),
        ]

        description = generate_video_description(metadata)

        assert "Death: Elarion" in description
        assert "PlayerName123" not in description
