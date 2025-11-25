"""Main entry point for Fellowship Recorder."""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from .config import FellowshipRecorderConfig
from .watcher import FellowshipRecorderWatcher

logger = logging.getLogger(__name__)


def enable_autostart() -> None:
    """Enable auto-start of Fellowship Recorder using systemd user service."""
    print("Enabling Fellowship Recorder auto-start...")
    print()

    # Find the project root (where fellowship-recorder.service should be)
    project_root = Path(__file__).parent.parent.parent
    service_source = project_root / "fellowship-recorder.service"

    if not service_source.exists():
        print(f"Error: Service file not found at {service_source}")
        print(
            "Please ensure you're running this from the fellowship-recorder-linux directory."
        )
        sys.exit(1)

    # Create systemd user directory if it doesn't exist
    systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_user_dir.mkdir(parents=True, exist_ok=True)

    service_dest = systemd_user_dir / "fellowship-recorder.service"

    # Copy service file
    print(f"Copying service file to {service_dest}")
    shutil.copy2(service_source, service_dest)

    # Update WorkingDirectory in the service file to use actual project path
    service_content = service_dest.read_text()
    service_content = service_content.replace(
        "WorkingDirectory=%h/fellowship-recorder-linux",
        f"WorkingDirectory={project_root}",
    )
    service_dest.write_text(service_content)

    # Reload systemd daemon
    print("Reloading systemd daemon...")
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error reloading systemd daemon: {e.stderr}")
        sys.exit(1)

    # Enable the service
    print("Enabling fellowship-recorder.service...")
    try:
        subprocess.run(
            ["systemctl", "--user", "enable", "fellowship-recorder.service"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error enabling service: {e.stderr}")
        sys.exit(1)

    # Start the service
    print("Starting fellowship-recorder.service...")
    try:
        subprocess.run(
            ["systemctl", "--user", "start", "fellowship-recorder.service"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error starting service: {e.stderr}")
        sys.exit(1)

    print()
    print("✓ Auto-start enabled successfully!")
    print()
    print("The Fellowship Recorder service will now start automatically on login.")
    print()
    print("Useful commands:")
    print("  Check status:  systemctl --user status fellowship-recorder.service")
    print("  View logs:     journalctl --user -u fellowship-recorder.service -f")
    print("  Disable:       uv run fellowship-recorder --disable-autostart")


def disable_autostart() -> None:
    """Disable auto-start of Fellowship Recorder."""
    print("Disabling Fellowship Recorder auto-start...")
    print()

    # Stop the service
    print("Stopping fellowship-recorder.service...")
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", "fellowship-recorder.service"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        # Service might not be running, that's okay
        print(f"Note: {e.stderr.strip()}")

    # Disable the service
    print("Disabling fellowship-recorder.service...")
    try:
        subprocess.run(
            ["systemctl", "--user", "disable", "fellowship-recorder.service"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error disabling service: {e.stderr}")
        sys.exit(1)

    print()
    print("✓ Auto-start disabled successfully!")
    print()
    print(
        "The Fellowship Recorder service will no longer start automatically on login."
    )
    print("To re-enable: uv run fellowship-recorder --enable-autostart")


def run_recorder() -> None:
    """Run the Fellowship Recorder application."""
    print("Fellowship Recorder for Linux")
    print("=============================")
    print()

    config_path = Path("config.toml")
    if config_path.exists():
        print(f"Loading configuration from {config_path}")
        config = FellowshipRecorderConfig.from_toml(config_path)
    else:
        print("No config.toml found, using default settings...")
        config = FellowshipRecorderConfig()

    print("Configuration:")
    print(f"  Log Directory:    {config.log_directory}")
    print(f"  Output Directory: {config.output_directory}")
    print(f"  Monitor:          {config.monitor}")
    print(f"  Resolution:       {config.resolution}")
    print(f"  Quality:          {config.recording_quality}")
    print(f"  FPS:              {config.recording_fps}")
    print(f"  Format:           {config.format}")
    print(f"  Audio:            {config.audio_device or 'disabled'}")
    if config.replay_buffer:
        print(f"  Replay Buffer:    {config.replay_buffer}s")
    print(f"  Min Difficulty:   {config.min_difficulty}")
    print()

    watcher = FellowshipRecorderWatcher(config)
    watcher.start()


def main() -> None:
    """Parse arguments and run the appropriate command."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(
        description="Fellowship Recorder for Linux - Automatically record your Fellowship dungeon runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--enable-autostart",
        action="store_true",
        help="Enable auto-start of Fellowship Recorder on login using systemd",
    )
    parser.add_argument(
        "--disable-autostart",
        action="store_true",
        help="Disable auto-start of Fellowship Recorder",
    )

    args = parser.parse_args()

    if args.enable_autostart and args.disable_autostart:
        print("Error: Cannot use --enable-autostart and --disable-autostart together")
        sys.exit(1)

    if args.enable_autostart:
        enable_autostart()
    elif args.disable_autostart:
        disable_autostart()
    else:
        run_recorder()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
