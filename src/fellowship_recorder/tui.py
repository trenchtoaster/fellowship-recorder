"""Terminal User Interface for Fellowship Recorder."""

from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    RichLog,
    Static,
)

from .config import FellowshipRecorderConfig
from .mappings import format_difficulty, get_target_time
from .metadata import RecordingMetadata
from .parser import CombatLogEvent, CombatLogParser, EventType
from .recorder import GpuScreenRecorder

if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent

logger = logging.getLogger(__name__)


class StatusIndicator(Static):
    """Large status indicator showing recording state."""

    is_recording = reactive(False)
    dungeon_name = reactive("")
    difficulty = reactive("")
    elapsed_time = reactive(0.0)

    def render(self) -> str:
        if self.is_recording:
            minutes = int(self.elapsed_time // 60)
            seconds = int(self.elapsed_time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            return f"[bold red]● RECORDING[/] {time_str}\n[cyan]{self.dungeon_name}[/] [dim]{self.difficulty}[/]"

        return "[bold green]● IDLE[/]\n[dim]Waiting for dungeon...[/]"


class RecentRecordings(Static):
    """Widget showing recent recordings."""

    def compose(self) -> ComposeResult:
        yield Label("[bold]Recent Recordings[/]", id="recordings-title")
        yield DataTable(id="recordings-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Time", "Dungeon", "Difficulty", "Duration", "Status")
        table.cursor_type = "row"


class LogEvents(Static):
    """Widget showing recent log events."""

    def compose(self) -> ComposeResult:
        yield Label("[bold]Log Events[/]", id="events-title")
        yield RichLog(id="events-log", highlight=True, markup=True, max_lines=100)


class ConfigSummary(Static):
    """Widget showing current configuration."""

    def __init__(self, config: FellowshipRecorderConfig) -> None:
        super().__init__()
        self.config = config

    def render(self) -> str:
        c = self.config
        return (
            f"[bold]Config[/]\n"
            f"[dim]Output:[/] {str(c.output_directory).replace(str(Path.home()), '~')}\n"
            f"[dim]Quality:[/] {c.recording_quality} @ {c.recording_fps}fps\n"
            f"[dim]Resolution:[/] {c.resolution}\n"
            f"[dim]Min Difficulty:[/] {c.min_difficulty}"
        )


class FellowshipRecorderTUI(App):
    """Main TUI application for Fellowship Recorder."""

    TITLE = "Fellowship Recorder"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: auto 1fr;
    }

    #status-container {
        column-span: 2;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    StatusIndicator {
        text-align: center;
        padding: 1;
    }

    #left-panel {
        padding: 1;
        border: solid $primary;
    }

    #right-panel {
        padding: 1;
        border: solid $primary;
    }

    #recordings-title, #events-title {
        padding-bottom: 1;
    }

    LogEvents {
        height: 100%;
    }

    RecentRecordings {
        height: 1fr;
    }

    DataTable {
        height: 100%;
    }

    RichLog {
        height: 1fr;
        border: none;
    }

    ConfigSummary {
        dock: bottom;
        height: auto;
        padding: 1;
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit", priority=True),
        Binding("r", "refresh_recordings", "Refresh", priority=True),
        Binding("c", "clear_display", "Clear Display", priority=True),
        Binding("o", "open_recording", "Open Video", priority=True),
        Binding("m", "open_metadata", "Open Metadata", priority=True),
        Binding("f", "open_folder", "Open Folder", priority=True),
        Binding("d", "delete_recording", "Delete Recording", priority=True),
    ]

    def __init__(self, config: FellowshipRecorderConfig | None = None) -> None:
        super().__init__()
        self.config = config or FellowshipRecorderConfig.from_toml()
        self.parser = CombatLogParser()
        self.recorder = GpuScreenRecorder(
            output_dir=self.config.output_directory,
            log_directory=self.config.log_directory,
            quality=self.config.recording_quality,
            fps=self.config.recording_fps,
            audio_device=self.config.audio_device,
            replay_buffer=self.config.replay_buffer,
            format=self.config.format,
            resolution=self.config.resolution,
            monitor=self.config.monitor,
            add_chapters=self.config.add_chapter_markers,
            boss_markers=self.config.boss_markers,
            death_markers=self.config.death_markers,
            chapter_offset=self.config.chapter_offset,
            overrun=self.config.get_overrun_time(),
            generate_video_description=self.config.generate_video_description,
        )
        self.file_positions: dict[Path, int] = {}
        self.recording_start_time: float | None = None
        self.current_metadata: dict[str, str] = {}
        self.last_activity_time = time.time()
        self.startup_time = time.time()
        self._observer = None
        self._current_kill_score: float = 0.0
        self._current_death_count: int = 0
        self._current_dungeon_mode: str | None = None
        self._recording_files: dict = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(StatusIndicator(), id="status-container")
        yield Vertical(LogEvents(), id="left-panel")
        yield Vertical(RecentRecordings(), ConfigSummary(self.config), id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._load_recent_recordings()
        self._start_watcher()
        self.set_interval(1.0, self._update_timer)
        self.set_interval(1.0, self._check_inactivity)
        self.call_after_refresh(self._initialize_file_positions)
        self.call_after_refresh(lambda: self.query_one("#recordings-table").focus())

    def _initialize_file_positions(self) -> None:
        """Initialize file positions to end of existing logs."""
        log_dir = self.config.log_directory

        if not log_dir.exists():
            self._log_event("[yellow]Warning:[/] Log directory not found")
            return

        for log_file in log_dir.glob("CombatLog*"):
            if log_file.is_file():
                with contextlib.suppress(Exception):
                    self.file_positions[log_file] = log_file.stat().st_size

        self._log_event(
            f"[green]Initialized[/] Watching {len(self.file_positions)} log file(s)"
        )

    def _load_recent_recordings(self) -> None:
        """Load recent recordings into the table."""
        table = self.query_one("#recordings-table", DataTable)
        table.clear()
        self._recording_files = {}

        output_dir = self.config.output_directory

        if not output_dir.exists():
            return

        recordings = []

        for json_file in output_dir.glob("*.json"):
            try:
                import json

                with json_file.open() as f:
                    data = json.load(f)

                meta = RecordingMetadata.model_validate(data)
                video_file = json_file.with_suffix("")

                for ext in [".mp4", ".mkv"]:
                    candidate = json_file.with_suffix(ext)

                    if candidate.exists():
                        video_file = candidate
                        break

                recordings.append((meta.started_at or "", meta, json_file, video_file))
            except Exception:
                continue

        recordings.sort(key=lambda x: x[0], reverse=True)

        for _, meta, json_file, video_file in recordings[:10]:
            started = (meta.started_at or "")[:10]
            dungeon = (meta.dungeon_name or "Unknown")[:20]
            diff = (meta.difficulty_name or "")[:15]
            dur_str = f"{int(meta.duration // 60)}:{int(meta.duration % 60):02d}"
            row_key = table.add_row(started, dungeon, diff, dur_str, meta.result_status)
            self._recording_files[row_key] = (json_file, video_file)

    def _start_watcher(self) -> None:
        """Start watching combat logs in a daemon thread."""
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        tui = self

        class TUILogHandler(FileSystemEventHandler):
            def __init__(self, app: FellowshipRecorderTUI) -> None:
                self.app = app

            def on_modified(self, event: FileSystemEvent) -> None:
                if event.is_directory:
                    return

                file_path = Path(str(event.src_path))

                if file_path.name.startswith("CombatLog"):
                    self.app.call_from_thread(self.app._process_log_file, file_path)

        log_dir = self.config.log_directory

        if not log_dir.exists():
            return

        observer = Observer()
        observer.daemon = True
        observer.schedule(TUILogHandler(tui), str(log_dir), recursive=False)
        observer.start()
        self._observer = observer

    def _process_log_file(self, file_path: Path) -> None:
        """Process new lines from a combat log file."""
        try:
            current_size = file_path.stat().st_size
            last_position = self.file_positions.get(file_path, 0)

            if current_size < last_position:
                last_position = 0

            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(last_position)
                new_lines = f.readlines()
                self.file_positions[file_path] = f.tell()

            for line in new_lines:
                self._process_line(line.strip())

        except FileNotFoundError:
            self.file_positions.pop(file_path, None)
        except Exception as e:
            self._log_event(f"[red]Error:[/] {e}")

    def _process_line(self, line: str) -> None:
        """Process a single combat log line."""
        event = self.parser.parse_line(line)

        if event is None:
            return

        time_since_startup = time.time() - self.startup_time

        if time_since_startup < 5.0:
            return

        self.last_activity_time = time.time()

        if event.event_type == EventType.DUNGEON_START:
            self._handle_dungeon_start(event)
        elif event.event_type == EventType.DUNGEON_END:
            self._handle_dungeon_end(event)
        elif event.event_type == EventType.ZONE_CHANGE:
            self._handle_zone_change(event)
        elif event.event_type == EventType.ENCOUNTER_START:
            self._handle_encounter_start(event)
        elif event.event_type == EventType.ENCOUNTER_END:
            self._handle_encounter_end(event)
        elif event.event_type == EventType.UNIT_DEATH:
            self._handle_unit_death(event)
        elif event.event_type == EventType.ALLY_DEATH:
            self._handle_ally_death(event)

    def _handle_dungeon_start(self, event: CombatLogEvent) -> None:
        """Handle DUNGEON_START event."""
        self._current_kill_score = 0.0
        self._current_death_count = 0
        self._current_dungeon_mode = event.metadata.get("mode")
        name = event.metadata.get("dungeon_name", "Unknown")
        diff_id = event.metadata.get("difficulty_id")
        mode = event.metadata.get("mode")
        diff = format_difficulty(int(diff_id), mode) if diff_id else ""
        self._log_event(f"[cyan]Dungeon:[/] {name} [dim]({diff})[/]")

        if self.recorder.is_recording():
            self.recorder.update_session_metadata(event)
        elif self.config.should_record(event.metadata):
            self._start_recording(event)

    def _handle_dungeon_end(self, event: CombatLogEvent) -> None:
        """Handle DUNGEON_END event."""
        name = event.metadata.get("dungeon_name", "Unknown")
        duration = event.metadata.get("duration", "0")
        dungeon_id = event.metadata.get("dungeon_id")
        success = event.metadata.get("success", "0") == "1"

        line1_parts = [name]
        rem_secs: float | None = None
        rem_str: str | None = None

        try:
            dur_secs = float(duration) / 1000.0
            dur_str = f"{int(dur_secs // 60)}:{int(dur_secs % 60):02d}"
            line1_parts.append(dur_str)

            target = (
                get_target_time(int(dungeon_id))
                if dungeon_id and self._current_dungeon_mode == "0"
                else None
            )

            if target:
                rem_secs = target - dur_secs

                if rem_secs >= 0:
                    rem_str = f"Remaining: [green]+{int(rem_secs // 60)}:{int(rem_secs % 60):02d}[/]"
                else:
                    rem_str = f"Remaining: [red]-{int(abs(rem_secs) // 60)}:{int(abs(rem_secs) % 60):02d}[/]"
        except (ValueError, TypeError):
            pass

        if success:
            result_prefix = "[green]Success:[/]"
        elif rem_secs is not None and rem_secs <= 0:
            result_prefix = "[red]Failed:[/]"
        else:
            result_prefix = "[yellow]Abandoned:[/]"

        self._log_event(f"{result_prefix} {' '.join(line1_parts)}")

        line2_parts = []

        if rem_str:
            line2_parts.append(rem_str)

        if self._current_kill_score > 0:
            line2_parts.append(f"Kill Score: [cyan]{self._current_kill_score:.1f}%[/]")

        if self._current_death_count > 0:
            line2_parts.append(f"Deaths: [red]{self._current_death_count}[/]")

        if line2_parts:
            self._log_event(f"  [dim]{' | '.join(line2_parts)}[/]")

        if self.recorder.is_recording():
            self._stop_recording(event)

    def _handle_zone_change(self, event: CombatLogEvent) -> None:
        """Handle ZONE_CHANGE event."""
        dungeon_id = event.metadata.get("dungeon_id", "")
        name = event.metadata.get("dungeon_name", "Unknown")

        if dungeon_id == "17":
            self._log_event("[dim]Returned to Stronghold[/]")

            if self.recorder.is_recording():
                self._stop_recording(event)
        else:
            self._log_event(f"[dim]Entering {name}[/]")
            self._log_event("[dim]─────────────────────────────────[/]")

    def _handle_encounter_start(self, event: CombatLogEvent) -> None:
        """Handle ENCOUNTER_START event."""
        boss = event.metadata.get("encounter_name", "Unknown")
        self._log_event(f"[magenta]Boss:[/] {boss} [dim]Engaged[/]")

    def _handle_encounter_end(self, event: CombatLogEvent) -> None:
        """Handle ENCOUNTER_END event."""
        boss = event.metadata.get("encounter_name", "Unknown")
        success = event.metadata.get("success", "0") == "1"
        result = "[green]Defeated[/]" if success else "[red]Wipe[/]"
        self._log_event(f"[magenta]Boss:[/] {boss} {result}")

    def _handle_unit_death(self, event: CombatLogEvent) -> None:
        """Handle UNIT_DEATH event."""
        kill_score = event.metadata.get("kill_score")

        if kill_score:
            with contextlib.suppress(ValueError):
                self._current_kill_score = float(kill_score) * 100

    def _handle_ally_death(self, event: CombatLogEvent) -> None:
        """Handle ALLY_DEATH event."""
        self._current_death_count += 1
        name = event.metadata.get("player_name", "Unknown")
        self._log_event(f"[red]Death:[/] {name}")

    def _start_recording(self, event: CombatLogEvent) -> None:
        """Start recording."""
        self.recorder.start_recording(event)
        self.recording_start_time = time.time()
        self.current_metadata = event.metadata

        status = self.query_one(StatusIndicator)
        status.is_recording = True
        status.dungeon_name = self.current_metadata.get(
            "dungeon_name", "Unknown Dungeon"
        )
        status.difficulty = self._format_current_difficulty()

        self._log_event("[bold green]Recording started[/]")

    def _format_current_difficulty(self) -> str:
        """Format the current run's difficulty for the status panel."""
        diff_id = self.current_metadata.get("difficulty_id")
        mode = self.current_metadata.get("mode")
        if not diff_id:
            return ""
        try:
            return format_difficulty(int(diff_id), mode)
        except (ValueError, TypeError):
            return ""

    def _stop_recording(
        self, event: CombatLogEvent | None, discard: bool = False
    ) -> None:
        """Stop recording."""
        result = self.recorder.stop_recording(event, discard=discard)
        self.recording_start_time = None

        status = self.query_one(StatusIndicator)
        status.is_recording = False
        status.elapsed_time = 0.0

        if result:
            self._log_event(f"[bold yellow]Saved:[/] {result.name}")
            self._log_event("[dim]─────────────────────────────────[/]")
        else:
            self._log_event("[bold yellow]Recording stopped[/]")
            self._log_event("[dim]─────────────────────────────────[/]")

        self._load_recent_recordings()

    def _update_timer(self) -> None:
        """Update the elapsed time display."""
        if self.recording_start_time is not None:
            status = self.query_one(StatusIndicator)
            status.elapsed_time = time.time() - self.recording_start_time

    def _check_inactivity(self) -> None:
        """Check for inactivity timeout."""
        if not self.recorder.is_recording():
            return

        time_since_activity = time.time() - self.last_activity_time

        if time_since_activity > self.config.inactivity_timeout:
            self._log_event(
                f"[yellow]Inactivity timeout ({self.config.inactivity_timeout}s)[/]"
            )
            self._stop_recording(None, discard=True)

    def _log_event(self, message: str) -> None:
        """Add a message to the event log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log = self.query_one("#events-log", RichLog)
        log.write(f"[dim]{timestamp}[/] {message}")

    def action_refresh_recordings(self) -> None:
        """Refresh the recordings list."""
        self._load_recent_recordings()
        self._log_event("[green]Refreshed recordings list[/]")

    def action_clear_display(self) -> None:
        """Clear the event log display."""
        log = self.query_one("#events-log", RichLog)
        log.clear()

    def _get_selected_recording(self) -> tuple[Path, Path] | None:
        """Get the selected recording's files."""
        table = self.query_one("#recordings-table", DataTable)

        if table.cursor_row is None:
            return None

        try:
            table.get_row_at(table.cursor_row)
        except Exception:
            return None

        cursor_key = list(self._recording_files.keys())[table.cursor_row]
        return self._recording_files.get(cursor_key)

    def action_open_recording(self) -> None:
        """Open the selected recording in default player."""
        files = self._get_selected_recording()

        if not files:
            self._log_event("[yellow]No recording selected[/]")
            return

        _, video_file = files

        if video_file.exists():
            subprocess.Popen(["xdg-open", str(video_file)])
            self._log_event(f"[green]Opening:[/] {video_file.name}")
        else:
            self._log_event(f"[red]Video not found:[/] {video_file.name}")

    def action_open_metadata(self) -> None:
        """Open the selected recording's metadata JSON file."""
        files = self._get_selected_recording()

        if not files:
            self._log_event("[yellow]No recording selected[/]")
            return

        json_file, _ = files

        if json_file.exists():
            editor = os.environ.get("EDITOR")

            if editor:
                with self.suspend():
                    subprocess.run([editor, str(json_file)])
            else:
                subprocess.Popen(["xdg-open", str(json_file)])

            self._log_event(f"[green]Opening:[/] {json_file.name}")
        else:
            self._log_event(f"[red]Metadata not found:[/] {json_file.name}")

    def action_open_folder(self) -> None:
        """Open the folder containing the selected recording."""
        files = self._get_selected_recording()

        if not files:
            self._log_event("[yellow]No recording selected[/]")
            return

        json_file, _ = files
        subprocess.Popen(["xdg-open", str(json_file.parent)])
        self._log_event(f"[green]Opening folder:[/] {json_file.parent}")

    def action_delete_recording(self) -> None:
        """Delete the selected recording and all associated files."""
        files = self._get_selected_recording()

        if not files:
            self._log_event("[yellow]No recording selected[/]")
            return

        json_file, _ = files
        stem = json_file.stem
        parent = json_file.parent
        deleted = []

        for file in parent.iterdir():
            if file.is_file() and file.stem == stem:
                file.unlink()
                deleted.append(file.name)

        if deleted:
            for name in deleted:
                self._log_event(f"[red]Deleted:[/] {name}")

            self._load_recent_recordings()
        else:
            self._log_event("[yellow]No files to delete[/]")

    def action_quit_app(self) -> None:
        """Stop recording and quit, saving any in-progress recording."""
        if self._observer:
            self._observer.stop()

        if self.recorder.is_recording():
            self.recorder.stop_recording()

        self.exit()


def main() -> None:
    """Entry point for TUI."""
    config = FellowshipRecorderConfig.from_toml()
    app = FellowshipRecorderTUI(config)
    app.run()


if __name__ == "__main__":
    main()
