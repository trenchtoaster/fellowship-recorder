"""Tests for configuration and threshold logic."""

from pathlib import Path

import pytest

from fellowship_recorder.config import FellowshipRecorderConfig


class TestFellowshipRecorderConfig:
    """Test configuration threshold logic."""

    def test_should_record_enabled_by_default(self):
        """Test that dungeons are recorded by default."""
        config = FellowshipRecorderConfig()
        assert config.should_record()

    def test_should_record_above_difficulty_threshold(self):
        """Test dungeon recording above difficulty threshold."""
        config = FellowshipRecorderConfig(min_difficulty=10)
        metadata = {"difficulty": "15"}
        assert config.should_record(metadata)

    def test_should_record_below_difficulty_threshold(self):
        """Test dungeon recording below difficulty threshold."""
        config = FellowshipRecorderConfig(min_difficulty=10)
        metadata = {"difficulty": "5"}
        assert not config.should_record(metadata)

    def test_should_record_at_difficulty_threshold(self):
        """Test dungeon recording exactly at difficulty threshold."""
        config = FellowshipRecorderConfig(min_difficulty=10)
        metadata = {"difficulty": "10"}
        assert config.should_record(metadata)

    def test_should_record_no_metadata(self):
        """Test recording when no metadata is provided."""
        config = FellowshipRecorderConfig(min_difficulty=10)
        assert config.should_record(None)

    def test_should_record_invalid_difficulty(self):
        """Test recording with invalid difficulty value."""
        config = FellowshipRecorderConfig(min_difficulty=10)
        metadata = {"difficulty": "invalid"}
        assert config.should_record(metadata)

    def test_get_overrun_time(self):
        """Test getting overrun time."""
        config = FellowshipRecorderConfig(dungeon_overrun=10)
        assert config.get_overrun_time() == 10

    def test_default_values(self):
        """Test default configuration values."""
        config = FellowshipRecorderConfig()
        assert config.min_difficulty == 0
        assert config.dungeon_overrun == 5
        assert config.inactivity_timeout == 300
        assert config.recording_quality == "high"
        assert config.recording_fps == 60
        assert config.format == "mkv"
        assert config.add_chapter_markers is True
        assert config.boss_markers is True
        assert config.death_markers is True

    def test_path_expansion(self):
        """Test that paths with ~ are expanded."""
        config = FellowshipRecorderConfig()
        assert not str(config.log_directory).startswith("~")
        assert not str(config.output_directory).startswith("~")

    def test_from_toml_nonexistent_file(self, tmp_path):
        """Test loading from non-existent TOML file uses defaults."""
        config_path = tmp_path / "nonexistent.toml"
        config = FellowshipRecorderConfig.from_toml(config_path)
        assert config.min_difficulty == 0
        assert config.recording_quality == "high"

    def test_from_toml_with_values(self, tmp_path):
        """Test loading configuration from TOML file."""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[paths]
output_directory = "~/Videos/Test"

[recording]
quality = "ultra"
fps = 120
format = "mp4"

[filters]
min_difficulty = 20

[timing]
dungeon_overrun = 15
inactivity_timeout = 300

[chapters]
enabled = false
boss_markers = false
death_markers = false
""")

        config = FellowshipRecorderConfig.from_toml(config_path)
        assert config.recording_quality == "ultra"
        assert config.recording_fps == 120
        assert config.format == "mp4"
        assert config.min_difficulty == 20
        assert config.dungeon_overrun == 15
        assert config.inactivity_timeout == 300
        assert config.add_chapter_markers is False
        assert config.boss_markers is False
        assert config.death_markers is False
        assert "Videos/Test" in str(config.output_directory)
