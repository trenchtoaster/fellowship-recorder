"""Affix mappings for Fellowship dungeons."""

from __future__ import annotations

from typing import TypedDict


class AffixInfo(TypedDict):
    """Information about a dungeon affix."""

    name: str
    type: str
    description: str


AFFIX_MAP: dict[int, AffixInfo] = {
    2: {
        "name": "Sahril's Madness",
        "type": "Ascension",
        "description": "Enemies receive 30% increased Threat from Damage Dealers and Healers.",
    },
    3: {
        "name": "Elheryn's Exile",
        "type": "Ascension",
        "description": "Enemy interruptable abilities and dispellable effects deal 20% more damage.",
    },
    4: {
        "name": "Vayr's Legacy",
        "type": "Ascension",
        "description": "Enemies have learned new abilities.",
    },
    5: {
        "name": "Asha's Dilemma",
        "type": "Ascension",
        "description": "Dungeons have a Time Limit. When expired, heroes gain bonus Spirit Generation but Dungeon Score is reduced.",
    },
    6: {
        "name": "Asha's Regret",
        "type": "Ascension",
        "description": "Dungeons have a Time Limit. When expired, loot is reduced 1 upgrade level and Dungeon Score is reduced.",
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
    10: {
        "name": "Challenge",
        "type": "Curse",
        "description": "Non-boss enemies deal 10% more damage and have 10% more health. Heroes gain +10% Spirit.",
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
    18: {
        "name": "Promoted Enemies",
        "type": "Implicit",
        "description": "Some mobs and bosses have +1 difficulty stats until the dungeon timer runs out.",
    },
    19: {
        "name": "Shadow Lord's Trial",
        "type": "Curse",
        "description": "Collect Shadow Orbs to summon Emissaries. Defeating them grants +20% damage, Haste, and Movement Speed.",
    },
    20: {
        "name": "Ghorn the Avalanche",
        "type": "Curse",
        "description": "Ghorn waits somewhere in the dungeon. Defeat him to gain Ghorn's Boon and 20 seconds back on the Dungeon Timer.",
    },
    21: {
        "name": "Krumbug the Naughty",
        "type": "Curse",
        "description": "Krumbug waits somewhere in the dungeon. Defeat him to gain his Bag of Tricks and 60 seconds back on the Dungeon Timer.",
    },
    22: {
        "name": "Eira the White Witch",
        "type": "Curse",
        "description": "Eira waits somewhere in the dungeon. Defeat her to gain The White Witch's Boon and 90 seconds back on the Dungeon Timer.",
    },
    23: {
        "name": "Pathfinder's Guidance",
        "type": "Ascension",
        "description": "Defeating highlighted enemies reaches the required Kill Score and leads to the boss. Fighting marked enemies grants Haste.",
    },
    24: {
        "name": "Anomalous Orbs",
        "type": "Curse",
        "description": "Anomalous Orbs spawn near enemies and cast Detonate, dealing heavy damage to all players if not interrupted.",
    },
    25: {
        "name": "Storm Shield",
        "type": "Curse",
        "description": "Players periodically charge with red lightning for 8s, then a massive bolt strikes all players. Storm Shield reduces damage taken by 50% while charged.",
    },
    27: {
        "name": "Truesight",
        "type": "Curse",
        "description": "Every 30% Kill Score an enemy drops a Truesight Orb, revealing the next Heskyr-marked enemy. Killing it grants +20% damage and healing.",
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
