"""Generate video descriptions from Fellowship recording metadata."""

import argparse
import json
import sys
from pathlib import Path

from .metadata import RecordingMetadata


def format_timestamp(seconds: float) -> str:
    """Convert seconds to timestamp format (M:SS or H:MM:SS).

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def generate_video_description(metadata: RecordingMetadata) -> str:
    """Generate video description from recording metadata.

    Args:
        metadata: Recording metadata with chapters

    Returns:
        Formatted video description
    """
    lines = []

    if metadata.dungeon_name:
        title_parts = [metadata.dungeon_name]
        if metadata.difficulty_name:
            title_parts.append(metadata.difficulty_name)
        lines.append(" - ".join(title_parts))
        lines.append("")

    if metadata.chapters:
        player_to_hero = {}
        if metadata.deaths:
            for death in metadata.deaths:
                if death.hero_name:
                    player_to_hero[death.player_name] = death.hero_name

        lines.append("Chapters:")
        lines.append("0:00 Start")
        for chapter in metadata.chapters:
            timestamp = format_timestamp(chapter.timestamp)
            title = chapter.title

            if title.startswith("Death: "):
                player_name = title[7:]
                if player_name in player_to_hero:
                    title = f"Death: {player_to_hero[player_name]}"

            lines.append(f"{timestamp} {title}")
        lines.append("")

    if metadata.party:
        hero_names = [p.hero_name or f"Hero {p.hero_id}" for p in metadata.party]
        lines.append(f"Party: {', '.join(hero_names)}")

    if metadata.affixes:
        curse_affixes = [a for a in metadata.affixes if a.affix_type != "Ascension"]
        if curse_affixes:
            affix_names = [a.affix_name for a in curse_affixes]
            lines.append(f"Affixes: {', '.join(affix_names)}")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point for video description generator."""
    parser = argparse.ArgumentParser(
        description="Generate video description from Fellowship recording metadata"
    )
    parser.add_argument(
        "video",
        type=Path,
        help="Path to video file (will look for corresponding .json file)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file (default: print to stdout)",
    )

    args = parser.parse_args()

    video_path = args.video
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    json_path = video_path.with_suffix(".json")
    if not json_path.exists():
        print(f"Error: Metadata file not found: {json_path}", file=sys.stderr)
        print("Expected a .json file with the same name as the video.", file=sys.stderr)
        sys.exit(1)

    try:
        with json_path.open() as f:
            data = json.load(f)
        metadata = RecordingMetadata.model_validate(data)
    except Exception as e:
        print(f"Error loading metadata: {e}", file=sys.stderr)
        sys.exit(1)

    description = generate_video_description(metadata)

    if args.output:
        args.output.write_text(description)
        print(f"Description written to: {args.output}")
    else:
        print(description)


if __name__ == "__main__":
    main()
