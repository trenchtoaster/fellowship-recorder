"""Game mode conversion for Fellowship dungeons."""


def get_mode_name(mode: str | int | None) -> str:
    """Convert mode ID to user-friendly name.

    Args:
        mode: Mode flag from logs (0=challenge, 1=quick_play, None=unknown)

    Returns:
        Mode name string ("Challenge", "Quick Play", or "Unknown")
    """
    if mode == "1" or mode == 1:
        return "Quick Play"
    elif mode == "0" or mode == 0:
        return "Challenge"
    else:
        return "Unknown"
