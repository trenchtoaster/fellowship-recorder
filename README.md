# Fellowship Recorder

Automatically record your Fellowship dungeon runs with automatic detection, chapter markers, and rich metadata.

- This currently only works on Linux
- "Enable Advanced Combat Logs" needs to be enabled within the Gameplay options in Fellowship

## Features

- **Automatic recording** - Detects dungeon start/end from combat logs
- **Smart naming** - `20251125_090352_Urrak_Markets_Eternal_26.mkv`
- **Chapter markers** - Boss encounters and player deaths (requires FFmpeg)
- **Rich metadata** - Party composition, deaths, affixes, difficulty tiers (JSON)
- **Configurable filters** - Record only specific difficulties or skip Quick Play
- **Lightweight** - Minimal resource usage, runs in background

## Quick Start

### 1. Install

**Latest release (recommended):**
```bash
git clone --branch v0.3.1 https://github.com/trenchtoaster/fellowship-recorder.git
cd fellowship-recorder
./setup.sh
```

**Development version:**
```bash
git clone https://github.com/trenchtoaster/fellowship-recorder.git
cd fellowship-recorder
./setup.sh
```

**Requirements:**
- Python 3.12+
- [gpu-screen-recorder](https://git.dec05eba.com/gpu-screen-recorder) (AUR: `yay -S gpu-screen-recorder`)
- FFmpeg (optional, for chapter markers: `sudo pacman -S ffmpeg`)
- Fellowship via Steam/Proton

### 2. Configure

```bash
cp config.toml.example config.toml
nvim config.toml  # Update log_directory and monitor at minimum
```

Default Fellowship logs location:
```
~/.local/share/Steam/steamapps/common/Fellowship/fellowship/Saved/CombatLogs
```

See `config.toml.example` for all configuration options.

### 3. Run

```bash
uv run fellowship-recorder
```

The watcher will:
- Monitor your combat logs
- Auto-start recording on dungeon entry
- Auto-stop when complete
- Save with descriptive filename + metadata JSON

## CLI Commands

Fellowship Recorder provides three CLI tools:

```bash
# Start the recorder
uv run fellowship-recorder

# Enable/disable autostart on login
uv run fellowship-recorder --enable-autostart
uv run fellowship-recorder --disable-autostart

# Parse combat logs (useful for processing existing logs)
uv run parse-log CombatLog.txt --list

# Generate video description from metadata
uv run generate-description video.mkv --output description.txt
```


## Output Files

Each recording creates two files:

**Video file** (`.mkv` or `.mp4`):
- Embedded chapter markers for boss fights and deaths
- Metadata tags (dungeon name, difficulty, result)

**Metadata file** (`.json`):
```json

See [CLI Reference](src/fellowship_recorder/cli/REFERENCE.md) for complete documentation.

```
## How It Works

1. Watches your Fellowship `CombatLogs` directory for changes
2. Parses combat log events (`DUNGEON_START`, `DUNGEON_END`, `ENCOUNTER_START`, `ALLY_DEATH`, etc.)
3. Controls gpu-screen-recorder to start/stop recording
4. Enriches metadata by scanning logs for party info, deaths, and affixes
5. Embeds chapter markers and metadata tags using FFmpeg

## Configuration

Edit `config.toml` to customize:

**Essential settings:**
- `log_directory` - Fellowship combat logs path
- `monitor` - Display to record (find with `hyprctl monitors` or `xrandr`)

**Recording settings:**
- `resolution`, `quality`, `fps`, `format`
- `audio_device` - Audio source to record (omit or set to `null` to disable audio)

**Filters:**
- `min_difficulty` - Only record dungeons above this difficulty (0 = all)
- `record_quick_play` - Record Quick Play mode (default: false)

**Timing:**
- `dungeon_overrun` - Extra seconds after dungeon ends (default: 5)
- `inactivity_timeout` - Stop after N seconds of no activity (default: 300)

**Chapters:**
- `boss_markers` - Add chapters for boss encounters
- `death_markers` - Add chapters for player deaths
- `chapter_offset` - Offset death markers backward in seconds

See `config.toml.example` for complete documentation.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for help with common issues.

## Documentation

- [CLI Reference](src/fellowship_recorder/cli/REFERENCE.md) - Detailed CLI tools documentation
- [Game Data Reference](src/fellowship_recorder/mappings/REFERENCE.md) - Difficulty tiers, heroes, and affixes
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Configuration](config.toml.example) - All configuration options

## Credits

Inspired by [Warcraft Recorder](https://github.com/aza547/wow-recorder) for Windows.

## License

MIT License
