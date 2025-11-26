"""File watcher for Fellowship combat logs."""

import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import FellowshipRecorderConfig
from .parser import CombatLogParser
from .recorder import GpuScreenRecorder

logger = logging.getLogger(__name__)


class CombatLogHandler(FileSystemEventHandler):
    """Handles file system events for Fellowship combat logs."""

    def __init__(self, config: FellowshipRecorderConfig):
        """Initialize handler.

        Args:
            config: Application configuration
        """
        self.config = config
        self.parser = CombatLogParser()
        self.recorder = GpuScreenRecorder(
            output_dir=config.output_directory,
            log_directory=config.log_directory,
            quality=config.recording_quality,
            fps=config.recording_fps,
            audio_device=config.audio_device,
            replay_buffer=config.replay_buffer,
            format=config.format,
            resolution=config.resolution,
            monitor=config.monitor,
            add_chapters=config.add_chapter_markers,
            overrun=config.get_overrun_time(),
            generate_video_description=config.generate_video_description,
        )
        self.file_positions: dict[Path, int] = {}
        self.last_activity_time = time.time()
        self.startup_time = time.time()
        self.startup_grace_period = 5.0
        self.pending_stop_time: float | None = None
        self.pending_end_event = None

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))

        if not file_path.name.startswith("CombatLog"):
            return

        self._process_log_file(file_path)

    def _process_log_file(self, file_path: Path) -> None:
        """Process new lines from a combat log file.

        Args:
            file_path: Path to the log file
        """
        try:
            current_size = file_path.stat().st_size

            last_position = self.file_positions.get(file_path, 0)

            if current_size < last_position:
                last_position = 0

            if file_path not in self.file_positions:
                logger.debug(f"Reading new file {file_path.name} from beginning")
            elif last_position == 0:
                logger.debug(f"File {file_path.name} was reset (size {current_size})")

            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(last_position)
                new_lines = f.readlines()
                self.file_positions[file_path] = f.tell()

            for line in new_lines:
                self._process_line(line.strip())

        except FileNotFoundError:
            self.file_positions.pop(file_path, None)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    def _process_line(self, line: str) -> None:
        """Process a single combat log line.

        Args:
            line: Raw combat log line
        """
        event = self.parser.parse_line(line)
        if event is None:
            return

        time_since_startup = time.time() - self.startup_time
        if time_since_startup < self.startup_grace_period:
            return

        if event.event_type.value != "UNIT_DEATH":
            logger.info(f"Detected: {event.event_type.value}")

        self.last_activity_time = time.time()

        if event.is_start_event:
            if self.config.should_record(event.metadata):
                logger.info("Starting recording for dungeon")
                logger.info(f"Metadata: {event.metadata}")
                self.recorder.start_recording(event)

        elif event.is_end_event and self.recorder.is_recording():
            overrun_time = self.config.get_overrun_time()
            if overrun_time > 0:
                self.pending_stop_time = time.time() + overrun_time
                self.pending_end_event = event
                logger.info(f"Dungeon ended, stopping in {overrun_time}s to capture overrun")
            else:
                self._stop_recording_with_event(event)

    def check_inactivity_timeout(self) -> None:
        """Check if we should stop recording due to inactivity."""
        if not self.recorder.is_recording():
            return

        if self.pending_stop_time is not None:
            return

        time_since_activity = time.time() - self.last_activity_time

        if time_since_activity > self.config.inactivity_timeout:
            logger.info(f"No activity for {self.config.inactivity_timeout}s, stopping recording")
            self._stop_recording_with_event(None)

    def check_pending_stop(self) -> None:
        """Stop recording when the configured overrun period has elapsed."""
        if not self.recorder.is_recording() or self.pending_stop_time is None:
            return

        if time.time() >= self.pending_stop_time:
            logger.info("Overrun period elapsed, stopping recording")
            self._stop_recording_with_event(self.pending_end_event)

    def _stop_recording_with_event(self, end_event):
        """Stop the recorder and clear pending state."""
        if self.recorder.is_recording():
            logger.info("Stopping recording")
            self.recorder.stop_recording(end_event)

        self.pending_stop_time = None
        self.pending_end_event = None


class FellowshipRecorderWatcher:
    """Main watcher application."""

    def __init__(self, config: FellowshipRecorderConfig):
        """Initialize watcher.

        Args:
            config: Application configuration
        """
        self.config = config
        self.handler = CombatLogHandler(config)
        self.observer = Observer()

    def _initialize_file_positions(self) -> None:
        """Initialize file positions to the end of existing log files.

        This prevents replaying old events when the watcher starts.
        """
        log_dir = self.config.log_directory
        initialized_count = 0

        for log_file in log_dir.glob("CombatLog*"):
            if log_file.is_file():
                try:
                    file_size = log_file.stat().st_size
                    self.handler.file_positions[log_file] = file_size
                    initialized_count += 1
                except Exception as e:
                    logger.warning(f"Could not initialize position for {log_file}: {e}")

        if initialized_count > 0:
            logger.info(f"Initialized {initialized_count} existing log file(s) to skip old events")

    def start(self) -> None:
        """Start watching the combat log directory."""
        log_dir = self.config.log_directory

        if not log_dir.exists():
            logger.error(f"Log directory does not exist: {log_dir}")
            logger.error("Please configure the correct path in config.toml")
            return

        logger.info(f"Watching: {log_dir}")
        logger.info(f"Output: {self.config.output_directory}")
        logger.info("Waiting for Fellowship activity...")

        self._initialize_file_positions()

        self.observer.schedule(self.handler, str(log_dir), recursive=False)
        self.observer.start()

        try:
            while True:
                time.sleep(1)
                self.handler.check_pending_stop()
                self.handler.check_inactivity_timeout()

        except KeyboardInterrupt:
            logger.info("\nStopping...")
            if self.handler.recorder.is_recording():
                logger.info("Saving current recording...")
                self.handler.recorder.stop_recording()
            self.observer.stop()

        self.observer.join()
