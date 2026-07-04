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
    - Death at 50s (log time) - 5s (chapter_offset) - 10s (recording delay) = 35s (video time)
    - Boss start at 60s (log time) - 5s (chapter_offset) - 10s (recording delay) = 45s (video time)
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
            chapter_offset=5,
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
    assert metadata.chapters[1].time_offset == 45.0


def test_recording_start_offset_skips_negative_chapters(tmp_path):
    """Test that chapters at ≤0 seconds are skipped.

    Scenario: Death happens very early, resulting in negative chapter time
    - Death at 3s (log time) - 5s (chapter_offset) - 10s (recording delay) = -12s
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
            chapter_offset=5,
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


def test_abandoned_dungeon_metadata(tmp_path):
    """Test that completed=False when end_event is ZONE_CHANGE to Stronghold."""
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 26, 58),
        event_type=EventType.ZONE_CHANGE,
        raw_line='2025-11-26T10:26:58.573+08:00|ZONE_CHANGE|"Ransack of Drakheim"|23|31|',
        metadata={"dungeon_name": "Ransack of Drakheim", "dungeon_id": "23"},
    )

    end_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 27, 21),
        event_type=EventType.ZONE_CHANGE,
        raw_line='2025-11-26T10:27:21.385+08:00|ZONE_CHANGE|"The Stronghold"|17|1|',
        metadata={"dungeon_name": "The Stronghold", "dungeon_id": "17"},
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
        )

        session = RecordingSession(
            start_event=start_event,
            end_event=end_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
            start_time=start_event.timestamp.timestamp(),
        )

        with patch.object(recorder.enricher, "enrich_metadata", side_effect=lambda m, s, e: m):
            metadata = recorder._generate_metadata(session)

    assert metadata.completed is False
    assert metadata.success is False
    assert metadata.dungeon_name == "Ransack of Drakheim"
    assert metadata.dungeon_id == 23


def test_completed_dungeon_metadata(tmp_path):
    """Test that completed=True when end_event is DUNGEON_END."""
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 28, 3),
        event_type=EventType.ZONE_CHANGE,
        raw_line='test',
        metadata={"dungeon_name": "Silken Hollow", "dungeon_id": "24"},
    )

    end_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 39, 14),
        event_type=EventType.DUNGEON_END,
        raw_line='test',
        metadata={"dungeon_name": "Silken Hollow", "dungeon_id": "24", "difficulty_id": "38", "success": "1"},
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
        )

        session = RecordingSession(
            start_event=start_event,
            end_event=end_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
            start_time=start_event.timestamp.timestamp(),
        )

        with patch.object(recorder.enricher, "enrich_metadata", side_effect=lambda m, s, e: m):
            metadata = recorder._generate_metadata(session)

    assert metadata.completed is True
    assert metadata.success is True
    assert metadata.dungeon_name == "Silken Hollow"
    assert metadata.dungeon_id == 24


def test_lobby_abandonment_short_duration(tmp_path):
    """Test that completed=False when DUNGEON_END has duration < 10s (lobby abandonment)."""
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 27, 2, 545000),
        event_type=EventType.DUNGEON_START,
        raw_line='test',
        metadata={"dungeon_name": "Ransack of Drakheim", "dungeon_id": "23", "difficulty_id": "31"},
    )

    end_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 27, 2, 545000),
        event_type=EventType.DUNGEON_END,
        raw_line='test',
        metadata={
            "dungeon_name": "Ransack of Drakheim",
            "dungeon_id": "23",
            "difficulty_id": "31",
            "duration": "1886",
            "success": "0",
        },
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
        )

        session = RecordingSession(
            start_event=start_event,
            end_event=end_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
            start_time=start_event.timestamp.timestamp(),
        )

        with patch.object(recorder.enricher, "enrich_metadata", side_effect=lambda m, s, e: m):
            metadata = recorder._generate_metadata(session)

    assert metadata.completed is False
    assert metadata.success is False
    assert metadata.dungeon_name == "Ransack of Drakheim"
    assert metadata.dungeon_id == 23


def test_ffmpeg_metadata_result_abandoned(tmp_path):
    """Test that FFmpeg metadata writes RESULT=Abandoned when completed=False."""
    from fellowship_recorder.metadata import RecordingMetadata

    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 26, 58),
        event_type=EventType.ZONE_CHANGE,
        raw_line='test',
        metadata={"dungeon_name": "Test Dungeon", "dungeon_id": "23"},
    )

    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=False,
        success=False,
        start_time=datetime.now(),
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
        )

        session = RecordingSession(
            start_event=start_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
        )

        metadata_file = tmp_path / "test_metadata.txt"
        recorder._create_ffmpeg_metadata(session, metadata_file, metadata)

    assert metadata_file.exists()
    content = metadata_file.read_text()
    assert "RESULT=Abandoned" in content


def test_ffmpeg_metadata_result_success(tmp_path):
    """Test that FFmpeg metadata writes RESULT=Success when completed=True and success=True."""
    from fellowship_recorder.metadata import RecordingMetadata

    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 26, 58),
        event_type=EventType.ZONE_CHANGE,
        raw_line='test',
        metadata={"dungeon_name": "Test Dungeon", "dungeon_id": "23"},
    )

    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
        )

        session = RecordingSession(
            start_event=start_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
        )

        metadata_file = tmp_path / "test_metadata.txt"
        recorder._create_ffmpeg_metadata(session, metadata_file, metadata)

    assert metadata_file.exists()
    content = metadata_file.read_text()
    assert "RESULT=Success" in content


def test_ffmpeg_metadata_result_failed(tmp_path):
    """Test that FFmpeg metadata writes RESULT=Failed when completed=True and success=False."""
    from fellowship_recorder.metadata import RecordingMetadata

    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 26, 58),
        event_type=EventType.ZONE_CHANGE,
        raw_line='test',
        metadata={"dungeon_name": "Test Dungeon", "dungeon_id": "23"},
    )

    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=False,
        start_time=datetime.now(),
    )

    with patch("fellowship_recorder.recorder.is_gpu_screen_recorder_available", return_value=True):
        recorder = GpuScreenRecorder(
            output_dir=tmp_path,
            log_directory=tmp_path,
        )

        session = RecordingSession(
            start_event=start_event,
            process=MagicMock(),
            output_file=tmp_path / "test.mkv",
        )

        metadata_file = tmp_path / "test_metadata.txt"
        recorder._create_ffmpeg_metadata(session, metadata_file, metadata)

    assert metadata_file.exists()
    content = metadata_file.read_text()
    assert "RESULT=Failed" in content


def _make_session(tmp_path, process=None):
    """Build a session with a real temp file and a well-behaved mock process."""
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 27, 5),
        event_type=EventType.DUNGEON_START,
        raw_line="test",
        metadata={
            "dungeon_name": "Silken Hollow",
            "dungeon_id": "24",
            "difficulty_id": "31",
        },
    )

    if process is None:
        process = MagicMock()
        process.communicate.return_value = (b"", b"")
        process.returncode = 0

    output_file = tmp_path / "recording_temp.mp4"
    output_file.write_bytes(b"video")

    return RecordingSession(
        start_event=start_event,
        process=process,
        output_file=output_file,
        start_time=start_event.timestamp.timestamp(),
    )


def test_stop_recording_discard_deletes_file(tmp_path):
    """Test that discard=True removes the temp file and returns None."""
    recorder = GpuScreenRecorder(output_dir=tmp_path, log_directory=tmp_path)
    session = _make_session(tmp_path)
    recorder.active_session = session

    result = recorder.stop_recording(None, discard=True)

    assert result is None
    assert not session.output_file.exists()
    assert recorder.active_session is None


def test_stop_recording_without_end_event_saves_as_abandoned(tmp_path):
    """Test that stopping without an end event saves the file instead of discarding."""
    recorder = GpuScreenRecorder(output_dir=tmp_path, log_directory=tmp_path)
    session = _make_session(tmp_path)
    recorder.active_session = session

    result = recorder.stop_recording()

    assert result is not None
    assert result.exists()
    assert result.name.startswith("20251126_102705_Silken_Hollow")
    assert not session.output_file.exists()

    json_path = result.with_suffix(".json")
    assert json_path.exists()

    import json

    data = json.loads(json_path.read_text())
    assert data["completed"] is False
    assert data["success"] is False


def test_stop_recording_saves_after_kill_timeout(tmp_path):
    """Test that the recording is still finalized when the process must be killed."""
    import subprocess

    process = MagicMock()
    process.communicate.side_effect = subprocess.TimeoutExpired(cmd="gsr", timeout=10)

    recorder = GpuScreenRecorder(output_dir=tmp_path, log_directory=tmp_path)
    session = _make_session(tmp_path, process=process)
    recorder.active_session = session

    end_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 39, 14),
        event_type=EventType.DUNGEON_END,
        raw_line="test",
        metadata={"success": "1", "duration": "605000"},
    )

    result = recorder.stop_recording(end_event)

    process.kill.assert_called_once()
    assert result is not None
    assert result.exists()
    assert result.name.startswith("20251126_102705_Silken_Hollow")
    assert result.with_suffix(".json").exists()


def test_duration_prefers_log_duration(tmp_path):
    """Test that the game-reported duration wins over wall-clock time."""
    start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 27, 5),
        event_type=EventType.DUNGEON_START,
        raw_line="test",
        metadata={"dungeon_name": "Test", "dungeon_id": "24", "difficulty_id": "31"},
    )

    end_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 37, 20),
        event_type=EventType.DUNGEON_END,
        raw_line="test",
        metadata={"success": "1", "duration": "605000"},
    )

    recorder = GpuScreenRecorder(output_dir=tmp_path, log_directory=tmp_path)

    session = RecordingSession(
        start_event=start_event,
        end_event=end_event,
        process=MagicMock(),
        output_file=tmp_path / "test.mp4",
        start_time=start_event.timestamp.timestamp() - 20.0,
    )

    with patch.object(recorder.enricher, "enrich_metadata", side_effect=lambda m, s, e: m):
        metadata = recorder._generate_metadata(session)

    assert metadata.duration == 605.0


def test_update_session_metadata_updates_timestamp(tmp_path):
    """Test that update_session_metadata updates both metadata and timestamp.

    When recording starts on ZONE_CHANGE but DUNGEON_START arrives later,
    the timestamp should be updated so the filename uses DUNGEON_START time.
    """
    zone_change_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 26, 58),
        event_type=EventType.ZONE_CHANGE,
        raw_line="test",
        metadata={"dungeon_name": "Ransack of Drakheim", "dungeon_id": "23"},
    )

    dungeon_start_event = CombatLogEvent(
        timestamp=datetime(2025, 11, 26, 10, 27, 5),
        event_type=EventType.DUNGEON_START,
        raw_line="test",
        metadata={
            "dungeon_name": "Ransack of Drakheim",
            "dungeon_id": "23",
            "difficulty_id": "31",
            "mode": "0",
        },
    )

    recorder = GpuScreenRecorder(
        output_dir=tmp_path,
        log_directory=tmp_path,
    )

    session = RecordingSession(
        start_event=zone_change_event,
        process=MagicMock(),
        output_file=tmp_path / "temp.mp4",
    )
    recorder.active_session = session

    assert session.start_event.timestamp == datetime(2025, 11, 26, 10, 26, 58)

    recorder.update_session_metadata(dungeon_start_event)

    assert session.start_event.timestamp == datetime(2025, 11, 26, 10, 27, 5)
    assert session.start_event.metadata["difficulty_id"] == "31"
    assert session.start_event.metadata["mode"] == "0"

    filename = session.get_filename()
    assert filename.startswith("20251126_102705_")
