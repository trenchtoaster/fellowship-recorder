"""Tests for the recorder controller."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from fellowship_recorder.parser import CombatLogEvent, EventType
from fellowship_recorder.recorder import RecordingSession, sanitize_filename


def test_dungeon_filename():
    """Test filename generation for dungeons."""
    event = CombatLogEvent(
        timestamp=datetime(2025, 11, 24, 8, 36, 19),
        event_type=EventType.DUNGEON_START,
        raw_line='2025-11-24T08:36:19.097+08:00|DUNGEON_START|"Ransack of Drakheim"|23|31|[6,4]|0',
        metadata={
            "dungeon_name": "Ransack of Drakheim",
            "dungeon_id": "23",
            "difficulty_id": "31",
        },
    )

    session = RecordingSession(
        start_event=event,
        process=MagicMock(),
        output_file=Path("/tmp/test.mp4"),
    )

    filename = session.get_filename()

    assert filename == "20251124_083619_Ransack_of_Drakheim_Paragon_7.mp4"


def test_mkv_format():
    """Test filename generation with MKV container format."""
    event = CombatLogEvent(
        timestamp=datetime(2025, 11, 24, 8, 36, 19),
        event_type=EventType.DUNGEON_START,
        raw_line='2025-11-24T08:36:19.097+08:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0',
        metadata={
            "dungeon_name": "Test Dungeon",
            "dungeon_id": "23",
            "difficulty_id": "31",
        },
    )

    session = RecordingSession(
        start_event=event,
        process=MagicMock(),
        output_file=Path("/tmp/test.mkv"),
        format="mkv",
    )

    filename = session.get_filename()

    assert filename == "20251124_083619_Test_Dungeon_Paragon_7.mkv"


def test_sanitize_filename_spaces():
    """Test that spaces are replaced with underscores."""
    assert sanitize_filename("Temple of the Jade Serpent") == "Temple_of_the_Jade_Serpent"
    assert sanitize_filename("Ransack of Drakheim") == "Ransack_of_Drakheim"


def test_sanitize_filename_special_chars():
    """Test that special characters are removed or replaced."""
    assert sanitize_filename("Test: Name") == "Test_Name"
    assert sanitize_filename("Test (Name)") == "Test_Name"
    assert sanitize_filename("Test [Name]") == "Test_Name"
    assert sanitize_filename("Test, Name") == "Test_Name"


def test_sanitize_filename_multiple_underscores():
    """Test that multiple underscores are collapsed."""
    assert sanitize_filename("Multiple   Spaces") == "Multiple_Spaces"
    assert sanitize_filename("Test___Name") == "Test_Name"


def test_sanitize_filename_strips_underscores():
    """Test that leading/trailing underscores are stripped."""
    assert sanitize_filename(" Leading Space") == "Leading_Space"
    assert sanitize_filename("Trailing Space ") == "Trailing_Space"
    assert sanitize_filename("_Leading_") == "Leading"


def test_sanitize_filename_preserves_valid_chars():
    """Test that valid characters are preserved."""
    assert sanitize_filename("Test-Name") == "Test-Name"
    assert sanitize_filename("Test.Name") == "Test.Name"
    assert sanitize_filename("Normal_Name") == "Normal_Name"


def test_filename_with_unknown_dungeon():
    """Test filename generation when dungeon name is missing."""
    event = CombatLogEvent(
        timestamp=datetime(2025, 11, 24, 8, 36, 19),
        event_type=EventType.DUNGEON_START,
        raw_line="test",
        metadata={
            "dungeon_id": "23",
            "difficulty_id": "31",
        },
    )

    session = RecordingSession(
        start_event=event,
        process=MagicMock(),
        output_file=Path("/tmp/test.mp4"),
    )

    filename = session.get_filename()

    assert filename == "20251124_083619_Unknown_Paragon_7.mp4"


def test_filename_with_missing_difficulty():
    """Test filename generation when difficulty is missing."""
    event = CombatLogEvent(
        timestamp=datetime(2025, 11, 24, 8, 36, 19),
        event_type=EventType.DUNGEON_START,
        raw_line="test",
        metadata={
            "dungeon_name": "Test Dungeon",
            "dungeon_id": "23",
        },
    )

    session = RecordingSession(
        start_event=event,
        process=MagicMock(),
        output_file=Path("/tmp/test.mp4"),
    )

    filename = session.get_filename()

    assert filename == "20251124_083619_Test_Dungeon_Unknown.mp4"
