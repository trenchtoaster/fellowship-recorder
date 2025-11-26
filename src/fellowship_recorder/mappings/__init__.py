"""Game data mappings for Fellowship."""

from __future__ import annotations

from .affixes import AFFIX_MAP, get_affix_info, get_affix_name, get_affix_names
from .difficulty import DifficultyTier, format_difficulty, get_difficulty_tier
from .dungeons import (
    DUNGEONS,
    DungeonCategory,
    DungeonInfo,
    format_target_time,
    get_dungeon_info,
    get_target_time,
)
from .heroes import HERO_ID_MAP, get_hero_name
from .mode import get_mode_name

__all__ = [
    "AFFIX_MAP",
    "get_affix_info",
    "get_affix_name",
    "get_affix_names",
    "DifficultyTier",
    "format_difficulty",
    "get_difficulty_tier",
    "DUNGEONS",
    "DungeonCategory",
    "DungeonInfo",
    "format_target_time",
    "get_dungeon_info",
    "get_target_time",
    "HERO_ID_MAP",
    "get_hero_name",
    "get_mode_name",
]
