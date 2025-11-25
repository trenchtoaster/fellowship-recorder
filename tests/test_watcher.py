"""Tests for combat log watcher."""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from fellowship_recorder.config import FellowshipRecorderConfig
from fellowship_recorder.parser import CombatLogEvent, EventType
from fellowship_recorder.watcher import CombatLogHandler, FellowshipRecorderWatcher


@pytest.fixture
def config(tmp_path):
    """Create a test configuration."""
    log_dir = tmp_path / "logs"
    output_dir = tmp_path / "output"
    log_dir.mkdir()
    output_dir.mkdir()

    return FellowshipRecorderConfig(
        log_directory=log_dir,
        output_directory=output_dir,
        min_difficulty=0,
        inactivity_timeout=300,
        dungeon_overrun=5,
        add_chapter_markers=True,
        boss_markers=True,
        death_markers=True,
    )


@pytest.fixture
def mock_recorder():
    """Create a mock GpuScreenRecorder."""
    return MagicMock()


@pytest.fixture
def handler(config, mock_recorder):
    """Create a CombatLogHandler with mocked recorder."""
    with patch("fellowship_recorder.watcher.GpuScreenRecorder", return_value=mock_recorder):
        handler = CombatLogHandler(config)
        handler.startup_time = 0
        return handler


class TestCombatLogHandler:
    """Test CombatLogHandler."""

    def test_handler_initialization(self, config):
        """Test handler can be initialized."""
        with patch("fellowship_recorder.watcher.GpuScreenRecorder"):
            handler = CombatLogHandler(config)
            assert handler.config == config
            assert handler.parser is not None
            assert handler.file_positions == {}

    def test_process_log_file_new_file(self, handler, tmp_path):
        """Test processing a new log file."""
        log_file = tmp_path / "logs" / "CombatLog241125_083000.txt"
        log_file.write_text("2025-11-24T08:36:19.000+00:00|LOGGING_STARTED|4|0.2.4.1|1\n")

        handler._process_log_file(log_file)

        assert log_file in handler.file_positions
        assert handler.file_positions[log_file] > 0

    def test_process_log_file_incremental(self, handler, tmp_path):
        """Test processing incremental updates to log file."""
        log_file = tmp_path / "logs" / "CombatLog241125_083000.txt"
        log_file.write_text("Line 1\n")

        handler._process_log_file(log_file)
        first_position = handler.file_positions[log_file]

        with log_file.open("a") as f:
            f.write("Line 2\n")

        handler._process_log_file(log_file)
        second_position = handler.file_positions[log_file]

        assert second_position > first_position

    def test_process_log_file_reset(self, handler, tmp_path):
        """Test handling log file that gets reset/truncated."""
        log_file = tmp_path / "logs" / "CombatLog241125_083000.txt"
        log_file.write_text("Long initial content\n")

        handler._process_log_file(log_file)
        initial_position = handler.file_positions[log_file]

        log_file.write_text("Short\n")

        handler._process_log_file(log_file)

        assert handler.file_positions[log_file] < initial_position

    def test_process_line_dungeon_start(self, handler, mock_recorder):
        """Test processing dungeon start event."""
        mock_recorder.is_recording.return_value = False

        line = '2025-11-24T08:36:19.000+00:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0'
        handler._process_line(line)

        mock_recorder.start_recording.assert_called_once()

    def test_process_line_dungeon_start_below_threshold(self, handler, mock_recorder):
        """Test that dungeons below difficulty threshold are not recorded."""
        handler.config.min_difficulty = 50
        mock_recorder.is_recording.return_value = False

        with patch.object(handler.parser, 'parse_line') as mock_parse:
            from fellowship_recorder.parser import CombatLogEvent, EventType
            from datetime import datetime, timezone

            mock_event = CombatLogEvent(
                timestamp=datetime.now(timezone.utc),
                event_type=EventType.DUNGEON_START,
                raw_line="test",
                metadata={"difficulty": "30"},
            )
            mock_parse.return_value = mock_event

            handler._process_line("test line")

        mock_recorder.start_recording.assert_not_called()

    def test_process_line_dungeon_end(self, handler, mock_recorder):
        """Test processing dungeon end event."""
        mock_recorder.is_recording.return_value = True
        handler.config.dungeon_overrun = 0

        line = '2025-11-24T08:52:36.000+00:00|DUNGEON_END|"Test Dungeon"|23|31|[6,4]|1|972907|605.0|1|0'
        handler._process_line(line)

        mock_recorder.stop_recording.assert_called_once()

    def test_process_line_dungeon_end_with_overrun(self, handler, mock_recorder):
        """Test dungeon end with overrun delay."""
        mock_recorder.is_recording.return_value = True
        handler.config.dungeon_overrun = 5

        line = '2025-11-24T08:52:36.000+00:00|DUNGEON_END|"Test Dungeon"|23|31|[6,4]|1|972907|605.0|1|0'
        handler._process_line(line)

        mock_recorder.stop_recording.assert_not_called()
        assert handler.pending_stop_time is not None

    def test_check_inactivity_timeout(self, handler, mock_recorder):
        """Test inactivity timeout stops recording."""
        mock_recorder.is_recording.return_value = True
        handler.config.inactivity_timeout = 1

        handler.last_activity_time = time.time() - 2

        handler.check_inactivity_timeout()

        mock_recorder.stop_recording.assert_called_once()

    def test_check_inactivity_no_timeout_when_active(self, handler, mock_recorder):
        """Test inactivity timeout doesn't trigger when active."""
        mock_recorder.is_recording.return_value = True
        handler.config.inactivity_timeout = 300

        handler.last_activity_time = time.time()

        handler.check_inactivity_timeout()

        mock_recorder.stop_recording.assert_not_called()

    def test_check_inactivity_no_timeout_when_not_recording(self, handler, mock_recorder):
        """Test inactivity timeout doesn't trigger when not recording."""
        mock_recorder.is_recording.return_value = False
        handler.config.inactivity_timeout = 1

        handler.last_activity_time = time.time() - 2

        handler.check_inactivity_timeout()

        mock_recorder.stop_recording.assert_not_called()

    def test_check_pending_stop(self, handler, mock_recorder):
        """Test pending stop executes after overrun period."""
        mock_recorder.is_recording.return_value = True

        handler.pending_stop_time = time.time() - 1
        handler.pending_end_event = Mock()

        handler.check_pending_stop()

        mock_recorder.stop_recording.assert_called_once()
        assert handler.pending_stop_time is None
        assert handler.pending_end_event is None

    def test_check_pending_stop_not_yet(self, handler, mock_recorder):
        """Test pending stop doesn't execute before overrun period."""
        mock_recorder.is_recording.return_value = True

        handler.pending_stop_time = time.time() + 10

        handler.check_pending_stop()

        mock_recorder.stop_recording.assert_not_called()

    def test_startup_grace_period(self, handler, mock_recorder):
        """Test events during startup grace period are ignored."""
        handler.startup_time = time.time()
        handler.startup_grace_period = 5.0

        line = '2025-11-24T08:36:19.000+00:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0'
        handler._process_line(line)

        mock_recorder.start_recording.assert_not_called()

    def test_process_line_updates_activity_time(self, handler):
        """Test processing line updates last activity time."""
        initial_time = handler.last_activity_time

        time.sleep(0.01)

        line = '2025-11-24T08:36:19.000+00:00|LOGGING_STARTED|4|0.2.4.1|1'
        handler._process_line(line)

        assert handler.last_activity_time > initial_time

    def test_process_line_malformed(self, handler, mock_recorder):
        """Test malformed lines don't crash handler."""
        handler._process_line("")
        handler._process_line("invalid line")
        handler._process_line("|||||||")

        mock_recorder.start_recording.assert_not_called()


class TestFellowshipRecorderWatcher:
    """Test FellowshipRecorderWatcher."""

    def test_watcher_initialization(self, config):
        """Test watcher can be initialized."""
        with patch("fellowship_recorder.watcher.Observer"):
            watcher = FellowshipRecorderWatcher(config)
            assert watcher.config == config
            assert watcher.handler is not None

    def test_initialize_file_positions(self, config):
        """Test file position initialization."""
        log_file1 = config.log_directory / "CombatLog241125_083000.txt"
        log_file2 = config.log_directory / "CombatLog241125_090000.txt"

        log_file1.write_text("Some old content\n")
        log_file2.write_text("More old content\n")

        with patch("fellowship_recorder.watcher.Observer"):
            watcher = FellowshipRecorderWatcher(config)
            watcher._initialize_file_positions()

        assert log_file1 in watcher.handler.file_positions
        assert log_file2 in watcher.handler.file_positions
        assert watcher.handler.file_positions[log_file1] > 0
        assert watcher.handler.file_positions[log_file2] > 0

    def test_initialize_file_positions_empty_dir(self, config):
        """Test file position initialization with no existing files."""
        with patch("fellowship_recorder.watcher.Observer"):
            watcher = FellowshipRecorderWatcher(config)
            watcher._initialize_file_positions()

        assert len(watcher.handler.file_positions) == 0

    def test_start_missing_log_directory(self, config):
        """Test start with missing log directory."""
        config.log_directory.rmdir()

        with patch("fellowship_recorder.watcher.Observer"):
            watcher = FellowshipRecorderWatcher(config)
            watcher.start()

    def test_inactivity_no_timeout_during_pending_stop(self, handler, mock_recorder):
        """Test inactivity timeout doesn't trigger during pending stop."""
        mock_recorder.is_recording.return_value = True
        handler.config.inactivity_timeout = 1
        handler.pending_stop_time = time.time() + 10

        handler.last_activity_time = time.time() - 2

        handler.check_inactivity_timeout()

        mock_recorder.stop_recording.assert_not_called()
