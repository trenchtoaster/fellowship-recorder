"""Parse combat log and generate metadata JSON."""

import argparse
import sys
from pathlib import Path

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
    runs = []
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
                result = bool(int(success_str))

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
                    result=result,
                    start_time=current_run["start_time"],
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

    if not args.log_file.exists():
        print(f"Error: Log file not found: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    runs = parse_combat_log(
        args.log_file, args.output if not args.list and not args.run else None
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
            result_str = "✓ Success" if metadata.result else "✗ Failed"
            print(
                f"{i}. {metadata.dungeon_name} ({metadata.difficulty_name}) - {result_str}"
            )
            print(f"   Started: {metadata.started_at}")
            print(f"   Ended: {metadata.ended_at}")
            print(f"   Duration: {metadata.duration:.1f}s")
            print(
                f"   Bosses: {len(metadata.encounters) if metadata.encounters else 0}"
            )
            print(f"   Deaths: {len(metadata.deaths) if metadata.deaths else 0}")
            print()


if __name__ == "__main__":
    main()
