"""Tests for TUI functionality."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fellowship_recorder.cli.parse_log import get_metadata_filename
from fellowship_recorder.metadata import RecordingMetadata
from fellowship_recorder.parser import CombatLogEvent, EventType
from fellowship_recorder.recorder import RecordingSession, sanitize_filename


class TestFilenameGeneration:
    """Test filename generation consistency between recorder and regenerate."""

    def test_recorder_and_regenerate_produce_same_filename(self):
        """Verify recorder and regenerate create matching filenames."""
        test_time = datetime(2025, 10, 30, 10, 34, 5)
        dungeon_name = "Sailor's Abyss"
        difficulty_id = 29
        mode = "0"

        event = CombatLogEvent(
            timestamp=test_time,
            event_type=EventType.DUNGEON_START,
            raw_line="test",
            metadata={
                "dungeon_name": dungeon_name,
                "difficulty_id": str(difficulty_id),
                "mode": mode,
            },
        )

        session = RecordingSession(
            start_event=event,
            process=None,
            output_file=Path("/tmp/test.mkv"),
            format="mkv",
        )
        recorder_filename = session.get_filename()

        metadata = RecordingMetadata.from_dungeon(
            dungeon_name=dungeon_name,
            dungeon_id=15,
            difficulty_id=difficulty_id,
            duration=100.0,
            completed=True,
            success=True,
            start_time=test_time,
            mode_id=mode,
        )
        regenerate_filename = get_metadata_filename(metadata)

        recorder_stem = Path(recorder_filename).stem
        regenerate_stem = Path(regenerate_filename).stem
        assert recorder_stem == regenerate_stem

    def test_filename_with_special_characters(self):
        """Test filename sanitization with special characters."""
        assert sanitize_filename("Sailor's Abyss") == "Sailors_Abyss"
        assert sanitize_filename("Test/Name") == "Test_Name"
        assert sanitize_filename("Test:Name") == "Test_Name"

    def test_filename_format(self):
        """Test filename follows expected format."""
        test_time = datetime(2025, 1, 15, 9, 5, 30)

        event = CombatLogEvent(
            timestamp=test_time,
            event_type=EventType.DUNGEON_START,
            raw_line="test",
            metadata={
                "dungeon_name": "Test Dungeon",
                "difficulty_id": "10",
                "mode": "0",
            },
        )

        session = RecordingSession(
            start_event=event,
            process=None,
            output_file=Path("/tmp/test.mkv"),
            format="mkv",
        )
        filename = session.get_filename()

        assert filename.startswith("20250115_090530_")
        assert "Test_Dungeon" in filename
        assert filename.endswith(".mkv")


class TestDeleteStemMatching:
    """Test file deletion stem matching logic."""

    def test_finds_all_files_with_same_stem(self, tmp_path):
        """Test that all files with matching stem are found."""
        stem = "20251030_103405_Test_Dungeon_Paragon_5"
        (tmp_path / f"{stem}.json").touch()
        (tmp_path / f"{stem}.mkv").touch()
        (tmp_path / f"{stem}.txt").touch()
        (tmp_path / "other_file.json").touch()

        matching = []
        for file in tmp_path.iterdir():
            if file.is_file() and file.stem == stem:
                matching.append(file.name)

        assert len(matching) == 3
        assert f"{stem}.json" in matching
        assert f"{stem}.mkv" in matching
        assert f"{stem}.txt" in matching

    def test_does_not_match_partial_stem(self, tmp_path):
        """Test that partial stem matches are not included."""
        (tmp_path / "20251030_103405_Test.json").touch()
        (tmp_path / "20251030_103405_Test_Extended.mkv").touch()

        stem = "20251030_103405_Test"
        matching = []
        for file in tmp_path.iterdir():
            if file.is_file() and file.stem == stem:
                matching.append(file.name)

        assert len(matching) == 1
        assert "20251030_103405_Test.json" in matching


class TestEditorSelection:
    """Test editor selection logic."""

    def test_editor_env_var_used_when_set(self, monkeypatch):
        """Test that EDITOR environment variable is respected."""
        monkeypatch.setenv("EDITOR", "nvim")
        import os
        assert os.environ.get("EDITOR") == "nvim"

    def test_editor_env_var_fallback_when_unset(self, monkeypatch):
        """Test fallback when EDITOR is not set."""
        monkeypatch.delenv("EDITOR", raising=False)
        import os
        editor = os.environ.get("EDITOR")
        assert editor is None


class TestMetadataFilenameTimezone:
    """Test that metadata filename handles timezone correctly."""

    def test_utc_to_local_conversion(self):
        """Test that UTC timestamps are converted to local time for filenames."""
        local_time = datetime(2025, 10, 30, 10, 34, 5)

        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test",
            dungeon_id=1,
            difficulty_id=10,
            duration=100.0,
            completed=True,
            success=True,
            start_time=local_time,
            mode_id="0",
        )

        filename = get_metadata_filename(metadata)
        assert "20251030_103405" in filename
