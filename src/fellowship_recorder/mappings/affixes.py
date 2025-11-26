"""Affix mappings for Fellowship dungeons."""

from __future__ import annotations

from typing import TypedDict


class AffixInfo(TypedDict):
    """Information about a dungeon affix."""

    name: str
    type: str
    description: str


AFFIX_MAP: dict[int, AffixInfo] = {
    4: {
        "name": "Vayr's Legacy",
        "type": "Ascension",
        "description": "Enemies have learned new abilities.",
    },
    6: {
        "name": "Asha's Dilemma",
        "type": "Ascension",
        "description": "Capstone Dungeons must be completed within a Time Limit. When expired, heroes gain bonus Spirit Generation but Dungeon Score is reduced.",
    },
    8: {
        "name": "Blood Shards",
        "type": "Curse",
        "description": "Dying enemies erupt Blood Shards damaging heroes. Heroes hit gain Expertise stacks.",
    },
    9: {
        "name": "Carnage",
        "type": "Curse",
        "description": "All incoming damage applies a bleed. Heroes heal for 10% of damage dealt. Bonus healing increases per boss defeated.",
    },
    11: {
        "name": "Binding Ice",
        "type": "Curse",
        "description": "Periodically, a hero is cursed. After 5s it erupts, damaging and rooting all heroes and enemies in radius.",
    },
    12: {
        "name": "Empowered Minions",
        "type": "Curse",
        "description": "Several enemies are empowered with +100% Health and +150% Power. Defeating them grants +20% Haste and Movement Speed.",
    },
    13: {
        "name": "Malevolent Shade",
        "type": "Curse",
        "description": "Shades appear reducing enemy damage taken by 50%. Defeating them restores 30% Health and 15% Mana.",
    },
    14: {
        "name": "Meteor Rain",
        "type": "Curse",
        "description": "Meteors periodically crash down on heroes. Each meteor grants 2 Spirit.",
    },
    15: {
        "name": "Stone Skin",
        "type": "Curse",
        "description": "Non-boss enemies have 30% increased health. They explode on death, damaging nearby enemies.",
    },
    16: {
        "name": "Ultimatum",
        "type": "Curse",
        "description": "Bosses deal 5% more damage and have 10% more health. Hero ability cooldowns reduced by 10%.",
    },
    19: {
        "name": "Shadow Lord's Trial",
        "type": "Curse",
        "description": "Collect Shadow Orbs to summon Emissaries. Defeating them grants +20% damage, Haste, and Movement Speed.",
    },
}


def get_affix_name(affix_id: int) -> str | None:
    """Get affix name from affix ID.

    Args:
        affix_id: Numeric affix ID from combat log

    Returns:
        Affix name or None if unknown
    """
    affix = AFFIX_MAP.get(affix_id)
    return affix["name"] if affix else None


def get_affix_info(affix_id: int) -> AffixInfo | None:
    """Get full affix information from affix ID.

    Args:
        affix_id: Numeric affix ID from combat log

    Returns:
        AffixInfo dict with name, type, and description, or None if unknown
    """
    return AFFIX_MAP.get(affix_id)


def get_affix_names(affix_ids: list[int]) -> list[str]:
    """Get affix names from a list of affix IDs.

    Args:
        affix_ids: List of numeric affix IDs from combat log (e.g., [6, 4])

    Returns:
        List of affix names
    """
    names: list[str] = []
    for affix_id in affix_ids:
        name = get_affix_name(affix_id)
        if name:
            names.append(name)
    return names
