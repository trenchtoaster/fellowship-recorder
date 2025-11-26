"""Configuration management using Pydantic."""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class FellowshipRecorderConfig(BaseModel):
    """Configuration for Fellowship Recorder."""

    log_directory: Path = Field(
        default=Path.home()
        / ".local/share/Steam/steamapps/common/Fellowship/fellowship/Saved/CombatLogs",
        description="Path to Fellowship combat log directory",
    )
    output_directory: Path = Field(
        default=Path.home() / "Videos/Fellowship",
        description="Directory to save recordings",
    )
    recording_quality: str = Field(
        default="high",
        description="Recording quality: low, medium, high, very_high, ultra",
    )
    recording_fps: int = Field(
        default=60,
        description="Recording framerate",
    )
    audio_device: str | None = Field(
        default="default",
        description="Audio device to capture (or None to disable)",
    )
    replay_buffer: int | None = Field(
        default=None,
        description="Replay buffer in seconds (None = normal recording mode)",
    )
    format: str = Field(
        default="mkv",
        description="Video format: mkv or mp4",
    )
    resolution: str = Field(
        default="1920x1080",
        description="Recording resolution in WxH format ('1920x1080', '2560x1440', '3840x2160')",
    )
    monitor: str = Field(
        default="DP-1",
        description="Monitor to record ('DP-1', 'HDMI-0', 'DP-2', etc.)",
    )
    min_difficulty: int = Field(
        default=0,
        ge=0,
        description="Minimum difficulty level to record (default: 0 = all difficulties)",
    )
    record_quick_play: bool = Field(
        default=False,
        description="Record Quick Play mode dungeons (default: False)",
    )
    dungeon_overrun: int = Field(
        default=5,
        ge=0,
        le=60,
        description="Continue recording for N seconds after dungeon ends",
    )
    inactivity_timeout: int = Field(
        default=300,
        description="Stop recording after N seconds of no combat log activity",
    )
    add_chapter_markers: bool = Field(
        default=True,
        description="Add chapter markers to video files (requires FFmpeg)",
    )
    boss_markers: bool = Field(
        default=True,
        description="Add chapter markers for boss encounters",
    )
    death_markers: bool = Field(
        default=True,
        description="Add chapter markers for player deaths",
    )
    death_chapter_offset: int = Field(
        default=5,
        ge=0,
        description="Seconds to offset death chapter markers backward (to see the death happen)",
    )
    generate_video_description: bool = Field(
        default=False,
        description="Auto-generate video description text file alongside recordings",
    )

    @field_validator("log_directory", "output_directory", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        """Expand tilde and convert string paths to Path objects.

        Args:
            v: Path as string or Path object

        Returns:
            Expanded Path object
        """
        if isinstance(v, str):
            return Path(v).expanduser()
        return v

    @classmethod
    def from_toml(cls, config_path: Path | None = None) -> FellowshipRecorderConfig:
        """Load configuration from TOML file.

        Args:
            config_path: Path to config file. If None, looks for config.toml in current directory.

        Returns:
            FellowshipRecorderConfig instance
        """
        if config_path is None:
            config_path = Path("config.toml")

        if not config_path.exists():
            logger.debug(f"No config file found at {config_path}, using defaults")
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            flat_config = {}
            if "paths" in data:
                flat_config["log_directory"] = data["paths"].get("log_directory")
                flat_config["output_directory"] = data["paths"].get("output_directory")

            if "recording" in data:
                rec = data["recording"]
                flat_config["recording_quality"] = rec.get("quality")
                flat_config["recording_fps"] = rec.get("fps")
                flat_config["audio_device"] = rec.get("audio_device")
                flat_config["format"] = rec.get("format")
                flat_config["resolution"] = rec.get("resolution")
                flat_config["monitor"] = rec.get("monitor")
                flat_config["replay_buffer"] = rec.get("replay_buffer")

            if "filters" in data:
                filt = data["filters"]
                flat_config["min_difficulty"] = filt.get("min_difficulty")
                flat_config["record_quick_play"] = filt.get("record_quick_play")

            if "timing" in data:
                timing = data["timing"]
                flat_config["dungeon_overrun"] = timing.get("dungeon_overrun")
                flat_config["inactivity_timeout"] = timing.get("inactivity_timeout")

            if "chapters" in data:
                chap = data["chapters"]
                flat_config["add_chapter_markers"] = chap.get("enabled")
                flat_config["boss_markers"] = chap.get("boss_markers")
                flat_config["death_markers"] = chap.get("death_markers")
                flat_config["death_chapter_offset"] = chap.get("death_chapter_offset")

            if "video" in data:
                vid = data["video"]
                flat_config["generate_video_description"] = vid.get(
                    "generate_description"
                )

            config_dict = {k: v for k, v in flat_config.items() if v is not None}
            return cls(**config_dict)

        except Exception as e:
            logger.error(f"Error loading {config_path}: {e}")
            logger.info("Using default configuration")
            return cls()

    def should_record(self, event_metadata: dict[str, str] | None = None) -> bool:
        """Check if we should record based on filters.

        Args:
            event_metadata: Event metadata containing difficulty, mode, etc.

        Returns:
            True if this activity should be recorded
        """
        if event_metadata is None:
            return True

        mode_str = event_metadata.get("mode")
        if mode_str == "1" and not self.record_quick_play:
            logger.info("Skipping Quick Play mode (record_quick_play is disabled)")
            return False

        difficulty_str = event_metadata.get("difficulty")
        if difficulty_str:
            try:
                difficulty = int(difficulty_str)
                if difficulty < self.min_difficulty:
                    logger.info(
                        f"Skipping difficulty {difficulty} (minimum: {self.min_difficulty})"
                    )
                    return False
            except ValueError:
                pass

        return True

    def get_overrun_time(self) -> int:
        """Get the overrun time for dungeons.

        Returns:
            Overrun time in seconds
        """
        return self.dungeon_overrun
