# Troubleshooting

## Installation

**"gpu-screen-recorder not found"**
```bash
yay -S gpu-screen-recorder  # Arch/AUR
```

**"uv not found"**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Configuration

**"Log directory does not exist"**

Default path: `~/.local/share/Steam/steamapps/common/Fellowship/fellowship/Saved/CombatLogs`

```bash
# Verify it exists
ls -la ~/.local/share/Steam/steamapps/common/Fellowship/fellowship/Saved/CombatLogs

# Find Fellowship if installed elsewhere
find ~/.local/share/Steam -name "Fellowship" -type d
```

**Find your monitor name:**
```bash
hyprctl monitors  # Wayland/Hyprland
xrandr           # X11
```

Update `config.toml`:
```toml
[recording]
monitor = "DP-1"  # Your monitor name
```

## Recording Issues

**Black/empty recordings**

Test gpu-screen-recorder:
```bash
gpu-screen-recorder -w DP-1 -s 1920x1080 -f 60 -q high -o test.mp4
# Record for a few seconds, Ctrl+C, check test.mp4
```

**Recording doesn't start**

1. Check logs are being written:
   ```bash
   ls -lht ~/.local/share/Steam/.../CombatLogs/ | head
   ```

2. Check difficulty threshold in `config.toml`:
   ```toml
   [filters]
   min_difficulty = 0  # 0 = record all
   ```

3. Check Quick Play setting:
   ```toml
   [filters]
   record_quick_play = true  # Enable to record Quick Play
   ```

**No chapter markers**

Requires FFmpeg:
```bash
sudo pacman -S ffmpeg

# Check chapters enabled
[chapters]
enabled = true
boss_markers = true
death_markers = true
```

Verify chapters exist:
```bash
ffprobe -show_chapters your_video.mkv
```

**No audio**

```toml
[recording]
audio_device = "default"  # Set to null or omit to disable audio
```

## Performance

**High CPU/disk usage**

Reduce quality:
```toml
[recording]
quality = "medium"  # Instead of high/ultra
fps = 30           # Instead of 60
format = "mkv"     # Better compression than mp4
```

## TUI Dashboard

**TUI not using my config**

The TUI searches these locations in order:
1. `~/.config/fellowship-recorder/config.toml`
2. `./config.toml` (current directory)

Copy your config to the XDG location:
```bash
mkdir -p ~/.config/fellowship-recorder
cp config.toml ~/.config/fellowship-recorder/
```

**Log directory warning in TUI**

The TUI shows "Log directory not found" if Fellowship isn't installed or the path is wrong. Check your config:
```bash
cat ~/.config/fellowship-recorder/config.toml | grep log_directory
ls -la "$(cat ~/.config/fellowship-recorder/config.toml | grep log_directory | cut -d'"' -f2)"
```

