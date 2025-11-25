"""Controller for gpu-screen-recorder."""

import logging
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enrichment import MetadataEnricher
from .mappings import format_difficulty
from .metadata import Chapter, RecordingMetadata
from .parser import CombatLogEvent

logger = logging.getLogger(__name__)

_gpu_screen_recorder_available: bool | None = None


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in Linux-friendly filenames."""
    name = re.sub(r"[^\w\-+.]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def is_gpu_screen_recorder_available() -> bool:
    """Check if gpu-screen-recorder is installed and available.

    Returns:
        True if gpu-screen-recorder command is available, False otherwise
    """
    global _gpu_screen_recorder_available

    if _gpu_screen_recorder_available is not None:
        return _gpu_screen_recorder_available

    _gpu_screen_recorder_available = shutil.which("gpu-screen-recorder") is not None
    return _gpu_screen_recorder_available


class RecordingSession(BaseModel):
    """Active recording session."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    start_event: CombatLogEvent = Field(
        description="Combat log event that triggered recording"
    )
    end_event: CombatLogEvent | None = Field(
        default=None, description="Combat log event that ended recording"
    )
    process: Any = Field(description="GPU screen recorder subprocess handle")
    output_file: Path = Field(description="Path to temporary recording file")
    start_time: float = Field(
        default_factory=time.time, description="Unix timestamp when recording started"
    )
    format: str = Field(
        default="mp4", description="Video container format (mp4 or mkv)"
    )
    chapters: list[Chapter] = Field(
        default_factory=list,
        description="Chapter markers for encounters within the recording",
    )

    def get_filename(self) -> str:
        """Generate a descriptive filename for this recording."""
        timestamp = self.start_event.timestamp.strftime("%Y%m%d_%H%M%S")

        dungeon = sanitize_filename(
            self.start_event.metadata.get("dungeon_name", "Unknown")
        )
        difficulty_raw = self.start_event.metadata.get("difficulty_id")
        mode = self.start_event.metadata.get("mode")

        try:
            difficulty_int = int(difficulty_raw) if difficulty_raw else None
            difficulty_formatted = format_difficulty(difficulty_int, mode)
            difficulty_str = sanitize_filename(difficulty_formatted)
        except (ValueError, TypeError):
            difficulty_str = "Unknown"

        return f"{timestamp}_{dungeon}_{difficulty_str}.{self.format}"


class GpuScreenRecorder:
    """Wrapper for gpu-screen-recorder command."""

    def __init__(
        self,
        output_dir: Path,
        log_directory: Path,
        quality: str = "high",
        fps: int = 60,
        audio_device: str | None = None,
        replay_buffer: int | None = None,
        format: str = "mp4",
        resolution: str = "3840x2160",
        monitor: str = "DP-1",
        add_chapters: bool = True,
        overrun: int = 0,
        generate_video_description: bool = False,
    ):
        """Initialize recorder.

        Args:
            output_dir: Directory to save recordings
            log_directory: Path to Fellowship combat log directory
            quality: Recording quality (low, medium, high, very_high, ultra)
            fps: Frames per second
            audio_device: Audio device to capture
            replay_buffer: If set, use replay buffer mode (seconds)
            format: Video format (mp4 or mkv)
            resolution: Recording resolution in WxH format
            monitor: Monitor to record ("DP-1", "HDMI-0", etc.)
            add_chapters: Whether to add chapter markers to videos
            overrun: Seconds to keep recording after a dungeon ends
            generate_video_description: Auto-generate video description text file
        """
        self.output_dir = output_dir
        self.log_directory = log_directory
        self.quality = quality
        self.fps = fps
        self.audio_device = audio_device
        self.replay_buffer = replay_buffer
        self.format = format
        self.resolution = resolution
        self.monitor = monitor
        self.add_chapters = add_chapters
        self.overrun = overrun
        self.generate_video_description = generate_video_description
        self.active_session: RecordingSession | None = None
        self.enricher = MetadataEnricher(log_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def start_recording(self, event: CombatLogEvent) -> RecordingSession | None:
        """Start a new recording session.

        Args:
            event: Combat log event that triggered recording

        Returns:
            RecordingSession if started successfully, None otherwise
        """
        if not is_gpu_screen_recorder_available():
            logger.error("gpu-screen-recorder not found in PATH")
            logger.error(
                "Install it from: https://git.dec05eba.com/gpu-screen-recorder"
            )
            return None

        if self.active_session is not None:
            logger.warning(f"Already recording: {self.active_session.output_file}")
            return None

        if not event.is_start_event:
            return None

        temp_file = (
            self.output_dir / f"recording_{datetime.now().timestamp()}.{self.format}"
        )
        cmd = self._build_command(temp_file)

        try:
            dungeon_name = event.metadata.get("dungeon_name", "Unknown")
            logger.info(f"Starting recording: {dungeon_name}")
            logger.info(f"Command: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            time.sleep(0.5)

            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(
                    f"Process exited immediately with code {process.returncode}"
                )
                logger.error(f"stdout: {stdout.decode()}")
                logger.error(f"stderr: {stderr.decode()}")
                return None

            self.active_session = RecordingSession(
                start_event=event,
                process=process,
                output_file=temp_file,
                format=self.format,
            )

            return self.active_session

        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return None

    def stop_recording(self, end_event: CombatLogEvent | None = None) -> Path | None:
        """Stop the current recording session.

        Returns:
            Path to the final recording file, or None if no session active
        """
        if self.active_session is None:
            logger.warning("No active recording to stop")
            return None

        session = self.active_session
        session.end_event = end_event
        self.active_session = None

        try:
            session.process.terminate()
            stdout, stderr = session.process.communicate(timeout=10)

            if session.process.returncode != 0:
                logger.error(
                    f"Process exited with code {session.process.returncode}"
                )
                if stderr:
                    logger.error(f"stderr: {stderr.decode()}")

            if not session.output_file.exists():
                logger.warning(
                    f"Output file does not exist: {session.output_file}"
                )
                return None

            final_name = session.get_filename()
            final_path = self.output_dir / final_name

            counter = 1
            while final_path.exists():
                name_parts = final_name.rsplit(".", 1)
                final_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                final_path = self.output_dir / final_name
                counter += 1

            session.output_file.rename(final_path)
            logger.info(f"Recording saved: {final_path}")

            metadata = self._generate_metadata(session)

            if self.add_chapters:
                final_path = self._add_chapters_to_video(session, final_path, metadata)

            self._save_metadata(metadata, final_path)

            if self.generate_video_description:
                self._save_video_description(metadata, final_path)

            return final_path

        except subprocess.TimeoutExpired:
            logger.warning("Process did not stop gracefully, killing...")
            session.process.kill()
            session.process.wait()
            return session.output_file

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return session.output_file

    def _add_chapters_to_video(
        self, session: RecordingSession, video_path: Path, metadata: RecordingMetadata
    ) -> Path:
        """Add chapter markers and metadata tags to video using FFmpeg.

        Args:
            session: Recording session with chapters
            video_path: Path to the video file
            metadata: Recording metadata with affixes, heroes, etc.

        Returns:
            Path to the final video
        """
        if not shutil.which("ffmpeg"):
            logger.warning("FFmpeg not found, skipping chapter markers and tags")
            return video_path

        try:
            metadata_file = video_path.with_suffix(".ffmetadata")
            temp_output = video_path.with_suffix(f".chapters{video_path.suffix}")

            self._create_ffmpeg_metadata(session, metadata_file, metadata)

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-i",
                str(metadata_file),
                "-map_metadata",
                "1",
                "-codec",
                "copy",
                "-y",
                str(temp_output),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            )

            metadata_file.unlink()

            if result.returncode == 0 and temp_output.exists():
                video_path.unlink()
                temp_output.rename(video_path)
                logger.info(f"Added {len(session.chapters)} chapter markers and metadata tags")
            else:
                if temp_output.exists():
                    temp_output.unlink()
                logger.error(
                    f"Failed to add chapters/tags: FFmpeg returned {result.returncode}"
                )

        except Exception as e:
            logger.error(f"Error adding chapters/tags: {e}")

        return video_path

    def _create_ffmpeg_metadata(
        self, session: RecordingSession, metadata_path: Path, metadata: RecordingMetadata
    ) -> None:
        """Create FFmpeg metadata file with global tags and chapters.

        Args:
            session: Recording session (for backwards compatibility)
            metadata_path: Where to write the metadata file
            metadata: Recording metadata with chapters, affixes, heroes, etc.
        """
        with metadata_path.open("w") as f:
            f.write(";FFMETADATA1\n")

            if metadata.dungeon_name:
                f.write(f"title={metadata.dungeon_name}")
                if metadata.difficulty_name:
                    f.write(f" - {metadata.difficulty_name}")
                f.write("\n")

            if metadata.party:
                hero_names = [p.hero_name for p in metadata.party if p.hero_name]
                if hero_names:
                    f.write(f"artist={', '.join(hero_names)}\n")

            if metadata.affixes:
                interesting_affixes = [
                    a.affix_name for a in metadata.affixes
                    if a.affix_id not in [4, 6]
                ]
                if interesting_affixes:
                    f.write(f"comment={', '.join(interesting_affixes)}\n")

            if metadata.difficulty_name:
                f.write(f"DIFFICULTY={metadata.difficulty_name}\n")

            result_str = "Success" if metadata.result else "Failed"
            f.write(f"RESULT={result_str}\n")

            if metadata.chapters:
                for i, chapter in enumerate(metadata.chapters):
                    start_ms = int(chapter.timestamp * 1000)

                    if i + 1 < len(metadata.chapters):
                        end_ms = int(metadata.chapters[i + 1].timestamp * 1000)
                    else:
                        end_ms = int(metadata.duration * 1000)

                    f.write("\n[CHAPTER]\n")
                    f.write("TIMEBASE=1/1000\n")
                    f.write(f"START={start_ms}\n")
                    f.write(f"END={end_ms}\n")
                    f.write(f"title={chapter.title}\n")

    def _generate_metadata(self, session: RecordingSession) -> RecordingMetadata:
        """Generate metadata for a recording session.

        Args:
            session: The recording session

        Returns:
            RecordingMetadata object with enriched data
        """
        measured_duration = time.time() - session.start_time
        event = session.start_event
        end_time = (
            session.end_event.timestamp
            if session.end_event is not None
            else event.timestamp + timedelta(seconds=measured_duration)
        )

        log_duration: float | None = None
        if session.end_event:
            raw_duration = session.end_event.metadata.get("duration")
            if raw_duration:
                try:
                    log_duration = float(raw_duration)
                except ValueError:
                    log_duration = None

        duration = (
            max(measured_duration, log_duration)
            if log_duration is not None
            else measured_duration
        )

        metadata = RecordingMetadata.from_dungeon(
            dungeon_name=self._get_value("dungeon_name", session) or "Unknown",
            dungeon_id=self._parse_int(self._get_value("dungeon_id", session)),
            difficulty_id=self._parse_int(self._get_value("difficulty_id", session)),
            duration=duration,
            result=self._parse_success_flag(session),
            start_time=event.timestamp,
            mode_id=self._get_value("mode", session),
            affixes=self._parse_affixes(self._get_value("affixes", session)),
        )

        metadata = self.enricher.enrich_metadata(
            metadata,
            event.timestamp,
            end_time,
        )

        metadata.overrun = self.overrun
        metadata.chapters = session.chapters if session.chapters else None
        return metadata

    def _save_metadata(self, metadata: RecordingMetadata, video_path: Path) -> None:
        """Save metadata to JSON file.

        Args:
            metadata: The recording metadata
            video_path: Path to the video file
        """
        try:
            json_path = video_path.with_suffix(".json")
            metadata.to_json(json_path)
            logger.info(f"Metadata saved: {json_path}")

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def _save_video_description(
        self, metadata: RecordingMetadata, video_path: Path
    ) -> None:
        """Save video description to text file.

        Args:
            metadata: The recording metadata
            video_path: Path to the video file
        """
        try:
            from .description import generate_video_description

            description = generate_video_description(metadata)
            txt_path = video_path.with_suffix(".txt")
            txt_path.write_text(description)
            logger.info(f"Video description saved: {txt_path}")

        except Exception as e:
            logger.error(f"Error saving video description: {e}")

    def _parse_int(self, value: str | None) -> int | None:
        """Convert a string to int, returning None on failure."""
        if value is None:
            return None
        try:
            return int(float(value))
        except ValueError:
            return None

    def _parse_affixes(self, value: str | None) -> list[int] | None:
        """Parse affixes string '[6,4]' into list [6, 4]."""
        if value is None or value == "[]":
            return None
        try:
            import json

            return json.loads(value)
        except (ValueError, json.JSONDecodeError):
            return None

    def _parse_success_flag(self, session: RecordingSession) -> bool:
        """Return result flag based on the end event metadata."""
        end_event = session.end_event
        if end_event is None:
            return True

        success_flag = end_event.metadata.get("success")
        if success_flag is None:
            return True

        return success_flag == "1"

    def _get_value(self, key: str, session: RecordingSession) -> str | None:
        """Get metadata value with preference to the end event."""
        if session.end_event and key in session.end_event.metadata:
            return session.end_event.metadata.get(key)
        return session.start_event.metadata.get(key)

    def _build_command(self, output_file: Path) -> list[str]:
        """Build the gpu-screen-recorder command.

        Args:
            output_file: Where to save the recording

        Returns:
            Command as list of arguments
        """
        cmd = [
            "gpu-screen-recorder",
            "-w",
            self.monitor,
            "-s",
            self.resolution,
            "-f",
            str(self.fps),
            "-q",
            self.quality,
            "-o",
            str(output_file),
        ]

        if self.audio_device:
            cmd.extend(["-a", self.audio_device])

        if self.replay_buffer:
            cmd.extend(["-r", str(self.replay_buffer)])

        return cmd

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.active_session is not None

    def add_chapter(self, title: str, offset: float = 0.0) -> None:
        """Add a chapter marker to the current recording.

        Args:
            title: Chapter title
            offset: Seconds to offset the chapter backward (default: 0)
        """
        if self.active_session is None:
            return

        timestamp = time.time() - self.active_session.start_time - offset
        # Ensure timestamp doesn't go negative
        timestamp = max(0.0, timestamp)
        self.active_session.chapters.append(Chapter(title=title, timestamp=timestamp))
