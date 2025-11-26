"""Tests for the recorder controller."""

import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from fellowship_recorder.metadata import Death, Encounter
from fellowship_recorder.parser import CombatLogEvent, EventType
from fellowship_recorder.recorder import GpuScreenRecorder, RecordingSession, sanitize_filename


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


def test_recording_start_offset_adjusts_chapters(tmp_path):
    """Test that chapters are adjusted for recording start delay.

    Scenario: Recording starts 10s after DUNGEON_START event is logged
    - Death at 50s (log time) - 5s (death_chapter_offset) - 10s (recording delay) = 35s (video time)
    - Boss at 60s (log time) - 10s (recording delay) = 50s (video time)
    """
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 11, 3, 37),
        event_type=EventType.DUNGEON_START,
        raw_line='test',
        metadata={"dungeon_name": "Test", "dungeon_id": "12", "difficulty_id": "40"},
    )

    end_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 11, 14, 21),
        event_type=EventType.DUNGEON_END,
        raw_line='test',
        metadata={"success": "1", "duration": "639424"},
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
            death_chapter_offset=5,
        )

        session = RecordingSession(
            start_event=start_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
            start_time=start_event.timestamp.timestamp() + 10.0,
        )
        session.end_event = end_event
        recorder.active_session = session

        with patch.object(recorder.enricher, "enrich_metadata") as mock_enrich:
            def add_test_events(metadata, start, end):
                metadata.deaths = [
                    Death(
                        player_id="P1",
                        player_name="Test",
                        hero_id=1,
                        hero_name="Hero",
                        occurred_at="2025-11-26T11:04:27Z",
                        time_offset=50.0,
                    )
                ]
                metadata.encounters = [
                    Encounter(
                        boss_id=1,
                        boss_name="Boss",
                        start_time_offset=60.0,
                        end_time_offset=100.0,
                        success=True,
                    )
                ]
                return metadata

            mock_enrich.side_effect = add_test_events

            metadata = recorder._generate_metadata(session)

    assert metadata.chapters is not None
    assert len(metadata.chapters) == 2
    assert metadata.chapters[0].title == "Death: Hero"
    assert metadata.chapters[0].time_offset == 35.0
    assert metadata.chapters[1].title == "Boss (Kill)"
    assert metadata.chapters[1].time_offset == 50.0


def test_recording_start_offset_skips_negative_chapters(tmp_path):
    """Test that chapters at ≤0 seconds are skipped.

    Scenario: Death happens very early, resulting in negative chapter time
    - Death at 3s (log time) - 5s (death_chapter_offset) - 10s (recording delay) = -12s
    - Chapter with negative time should be skipped entirely
    """
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 11, 3, 37),
        event_type=EventType.DUNGEON_START,
        raw_line='test',
        metadata={"dungeon_name": "Test", "dungeon_id": "12", "difficulty_id": "40"},
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
            death_chapter_offset=5,
        )

        session = RecordingSession(
            start_event=start_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
            start_time=start_event.timestamp.timestamp() + 10.0,
        )
        recorder.active_session = session

        with patch.object(recorder.enricher, "enrich_metadata") as mock_enrich:
            def add_early_death(metadata, start, end):
                metadata.deaths = [
                    Death(
                        player_id="P1",
                        player_name="Test",
                        hero_id=1,
                        hero_name="Hero",
                        occurred_at="2025-11-26T11:03:40Z",
                        time_offset=3.0,
                    )
                ]
                return metadata

            mock_enrich.side_effect = add_early_death

            metadata = recorder._generate_metadata(session)

    assert metadata.chapters is None or len(metadata.chapters) == 0
