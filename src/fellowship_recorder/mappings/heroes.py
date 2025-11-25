"""Hero mappings for Fellowship."""

HERO_ID_MAP = {
    0: None,
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


def get_hero_name(hero_id: int) -> str | None:
    """Get hero name from hero ID.

    Args:
        hero_id: Numeric hero ID from combat log (COMBATANT_INFO event)

    Returns:
        Hero name or None if unknown
    """
    return HERO_ID_MAP.get(hero_id)
