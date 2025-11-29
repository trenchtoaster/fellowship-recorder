"""Main entry point for Fellowship Recorder."""

import argparse
import logging
import sys

from .config import FellowshipRecorderConfig


def run_headless() -> None:
    """Run the recorder in headless mode (no TUI)."""
    from .watcher import FellowshipRecorderWatcher

    config = FellowshipRecorderConfig.from_toml()
    watcher = FellowshipRecorderWatcher(config)
    watcher.start()


def run_tui() -> None:
    """Run the TUI dashboard."""
    from .tui import FellowshipRecorderTUI

    config = FellowshipRecorderConfig.from_toml()
    app = FellowshipRecorderTUI(config)
    app.run()


def main() -> None:
    """Parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(
        description="Automatic Fellowship dungeon recorder",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode without the TUI",
    )

    args = parser.parse_args()

    if args.headless:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(name)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        run_headless()
    else:
        logging.disable(logging.CRITICAL)
        run_tui()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
