"""Hero mappings for Fellowship."""

from __future__ import annotations

HERO_ID_MAP: dict[int, str] = {
    2: "Elarion",
    7: "Ardeos",
    10: "Tariq",
    11: "Mara",
    13: "Meiko",
    14: "Sylvie",
    17: "Rime",
    20: "Vigour",
    22: "Helena",
}


def get_hero_name(hero_id: int) -> str:
    """Get hero name from hero ID.

    Args:
        hero_id: Numeric hero ID from combat log (COMBATANT_INFO event)

    Returns:
        Hero name or "Unknown" if not mapped
    """
    return HERO_ID_MAP.get(hero_id, "Unknown")
