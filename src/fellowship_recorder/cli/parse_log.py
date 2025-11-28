"""Parse combat log and generate metadata JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config import FellowshipRecorderConfig
from ..enrichment import MetadataEnricher
from ..metadata import RecordingMetadata
from ..parser import CombatLogParser, EventType
from ..recorder import sanitize_filename


def parse_combat_log(
    log_file: Path, output_file: Path | None = None
) -> list[RecordingMetadata]:
    """Parse combat log and extract metadata for all dungeon runs.

    Args:
        log_file: Path to combat log file
        output_file: Optional output file for JSON (if only one run found)

    Returns:
        List of RecordingMetadata for each dungeon run found
    """
    parser = CombatLogParser()
    enricher = MetadataEnricher(log_file.parent)
    runs: list[RecordingMetadata] = []
    current_run = None

    with log_file.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            event = parser.parse_line(line.strip())
            if event is None:
                continue

            if event.is_start_event:
                if current_run is None:
                    current_run = {
                        "start_event": event,
                        "start_time": event.timestamp,
                    }
                elif event.event_type == EventType.DUNGEON_START:
                    current_dungeon = current_run["start_event"].metadata.get(
                        "dungeon_id"
                    )
                    new_dungeon = event.metadata.get("dungeon_id")
                    if current_dungeon == new_dungeon:
                        current_run["start_event"] = event
                        current_run["start_time"] = event.timestamp

            elif event.is_end_event and current_run:
                end_event = event
                end_time = event.timestamp

                duration_str = end_event.metadata.get("duration")
                duration = (
                    float(duration_str) / 1000.0
                    if duration_str
                    else (end_time - current_run["start_time"]).total_seconds()
                )

                success_str = end_event.metadata.get("success", "0")
                success = bool(int(float(success_str)))

                completed = end_event.event_type == EventType.DUNGEON_END

                metadata = RecordingMetadata.from_dungeon(
                    dungeon_name=current_run["start_event"].metadata.get(
                        "dungeon_name", "Unknown"
                    ),
                    dungeon_id=int(
                        current_run["start_event"].metadata.get("dungeon_id", 0)
                    ),
                    difficulty_id=int(
                        current_run["start_event"].metadata.get("difficulty_id", 0)
                    ),
                    duration=duration,
                    completed=completed,
                    success=success,
                    start_time=current_run["start_time"],
                    end_time=end_time,
                    mode_id=current_run["start_event"].metadata.get("mode"),
                    affixes=[
                        int(x)
                        for x in current_run["start_event"]
                        .metadata.get("affixes", "")
                        .strip("[]")
                        .split(",")
                        if x.strip()
                    ],
                )

                metadata = enricher.enrich_metadata(
                    metadata,
                    current_run["start_time"],
                    end_time,
                )

                chapters = metadata.generate_chapters()
                if chapters:
                    metadata.chapters = chapters

                runs.append(metadata)
                current_run = None

    if output_file and len(runs) == 1:
        runs[0].to_json(output_file)
        print(f"Metadata written to: {output_file}")
    elif output_file and len(runs) > 1:
        print(
            f"Warning: Found {len(runs)} dungeon runs in log, not writing to single file"
        )
        print("Use --list to see all runs")

    return runs


def get_metadata_filename(metadata: RecordingMetadata) -> str:
    """Generate filename for metadata based on run info."""
    from datetime import datetime

    started_at = metadata.started_at or ""
    utc_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    local_time = utc_time.astimezone()
    timestamp = local_time.strftime("%Y%m%d_%H%M%S")
    dungeon = sanitize_filename(metadata.dungeon_name or "Unknown")
    difficulty = sanitize_filename(metadata.difficulty_name or "Unknown")
    return f"{timestamp}_{dungeon}_{difficulty}.json"


def regenerate_all_metadata(log_directory: Path, output_directory: Path) -> int:
    """Regenerate all metadata JSONs from combat logs.

    Args:
        log_directory: Directory containing combat logs
        output_directory: Directory to write JSON files

    Returns:
        Number of metadata files written
    """
    count = 0
    for log_file in sorted(log_directory.glob("CombatLog*.txt")):
        runs = parse_combat_log(log_file)
        for run in runs:
            if not run.completed:
                continue

            filename = get_metadata_filename(run)

            output_path = output_directory / filename
            run.to_json(output_path)
            print(f"  {filename}")
            count += 1
    return count


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse combat log and generate metadata JSON"
    )
    parser.add_argument(
        "log_file",
        type=Path,
        nargs="?",
        help="Path to combat log file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON file (only if single run found)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all dungeon runs found",
    )
    parser.add_argument(
        "-r",
        "--run",
        type=int,
        help="Select specific run number (1-based index from --list)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON to stdout instead of file",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate all metadata JSONs from combat logs",
    )

    args = parser.parse_args()
    config = FellowshipRecorderConfig.from_toml()

    if args.regenerate:
        print(f"Parsing logs from: {config.log_directory}")
        print(f"Writing metadata to: {config.output_directory}\n")
        count = regenerate_all_metadata(config.log_directory, config.output_directory)
        print(f"\nGenerated {count} metadata file(s)")
        sys.exit(0)

    if not args.log_file:
        parser.print_help()
        sys.exit(1)

    log_file = args.log_file
    if not log_file.exists() and not log_file.is_absolute():
        config_log_file = config.log_directory / log_file

        if config_log_file.exists():
            log_file = config_log_file

    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}", file=sys.stderr)
        sys.exit(1)

    runs = parse_combat_log(
        log_file, args.output if not args.list and not args.run else None
    )

    if args.run:
        if args.run < 1 or args.run > len(runs):
            print(
                f"Error: Run {args.run} not found. Valid range: 1-{len(runs)}",
                file=sys.stderr,
            )
            sys.exit(1)

        selected_run = runs[args.run - 1]

        if args.json:
            print(selected_run.model_dump_json(indent=2, exclude_none=True))
        elif args.output:
            selected_run.to_json(args.output)
            print(f"Run {args.run} metadata written to: {args.output}")
        else:
            print(selected_run.model_dump_json(indent=2, exclude_none=True))

    elif args.list or (not args.output and len(runs) > 0):
        print(f"\nFound {len(runs)} dungeon run(s) in {args.log_file.name}:\n")
        for i, metadata in enumerate(runs, 1):
            result_str = metadata.result_status

            print(
                f"{i}. {metadata.dungeon_name} ({metadata.difficulty_name}) - {result_str}"
            )
            print(f"   Started: {metadata.started_at}")
            print(f"   Ended: {metadata.ended_at}")
            print(f"   Duration: {metadata.duration:.1f}s")

            if metadata.remaining_time is not None:
                sign = "+" if metadata.remaining_time >= 0 else ""
                print(f"   Remaining Time: {sign}{metadata.remaining_time:.1f}s")

            if (
                metadata.kill_objective
                and metadata.kill_objective.final_score is not None
            ):
                print(f"   Kill Score: {metadata.kill_objective.final_score:.1f}%")

            if metadata.affixes:
                affix_names = ", ".join(affix.affix_name for affix in metadata.affixes)
                print(f"   Affixes: {affix_names}")

            print(
                f"   Bosses: {len(metadata.encounters) if metadata.encounters else 0}"
            )
            print(f"   Deaths: {len(metadata.deaths) if metadata.deaths else 0}")
            print()


if __name__ == "__main__":
    main()
