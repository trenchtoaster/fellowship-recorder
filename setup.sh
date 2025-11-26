#!/usr/bin/env bash
set -e

echo "========================================"
echo "Fellowship Recorder - Setup"
echo "========================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"

    echo ""
    echo "uv installed successfully"
    echo ""
    echo "IMPORTANT: Add uv to your PATH permanently by running:"
    echo ""

    # Detect shell and provide appropriate command
    if [ -n "$BASH_VERSION" ]; then
        echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        echo "  source ~/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
        echo "  source ~/.zshrc"
    else
        echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.profile"
        echo "  source ~/.profile"
    fi
    echo ""
    echo "Or open a new terminal for PATH to take effect."
    echo ""
else
    echo "uv is already installed"
fi

echo ""
echo "Checking system dependencies..."
echo ""

# Check for gpu-screen-recorder
if ! command -v gpu-screen-recorder &> /dev/null; then
    echo "WARNING: gpu-screen-recorder is not installed"
    echo "  Please install it from: https://git.dec05eba.com/gpu-screen-recorder"
    echo "  Or your distribution's package manager"
    echo ""
else
    echo "gpu-screen-recorder is installed"
fi

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: ffmpeg is not installed"
    echo "  Please install it using your distribution's package manager:"
    echo "    Arch: sudo pacman -S ffmpeg"
    echo "    Ubuntu/Debian: sudo apt install ffmpeg"
    echo "    Fedora: sudo dnf install ffmpeg"
    echo ""
else
    echo "ffmpeg is installed"
fi

echo ""
echo "Setting up project and dependencies..."
uv sync
uv pip install -e .

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy the example config: cp config.toml.example config.toml"
echo "2. Edit config.toml and configure your paths (monitor, Fellowship log directory, etc.)"
echo "3. Run: uv run fellowship-recorder"
echo ""
echo "Optional:"
echo "- Enable auto-start on login: uv run fellowship-recorder --enable-autostart"
echo "- View all CLI tools: uv run fellowship-recorder --help"
echo ""
