"""Parse combat log and generate metadata JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config import FellowshipRecorderConfig
from ..enrichment import MetadataEnricher
from ..metadata import RecordingMetadata
from ..parser import CombatLogParser, EventType


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

            if event.event_type == EventType.DUNGEON_START:
                current_run = {
                    "start_event": event,
                    "start_time": event.timestamp,
                }

            elif event.event_type == EventType.DUNGEON_END and current_run:
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

                completed = (
                    end_time is not None and end_time != current_run["start_time"]
                )

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


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse combat log and generate metadata JSON"
    )
    parser.add_argument(
        "log_file",
        type=Path,
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

    args = parser.parse_args()

    log_file = args.log_file
    if not log_file.exists() and not log_file.is_absolute():
        config = FellowshipRecorderConfig.from_toml()
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
            if not metadata.completed:
                result_str = "Abandoned"
            elif metadata.success:
                result_str = "Success"
            else:
                result_str = "Failed"

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
