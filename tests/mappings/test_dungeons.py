"""Tests for dungeon mappings."""

from fellowship_recorder.mappings.dungeons import (
    DUNGEONS,
    DungeonCategory,
    DungeonInfo,
    format_target_time,
    get_dungeon_info,
    get_target_time,
)


def test_dungeon_info_model():
    """Test DungeonInfo model creation."""
    dungeon = DungeonInfo(
        dungeon_id=24,
        name="Silken Hollow",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=812,
    )

    assert dungeon.dungeon_id == 24
    assert dungeon.name == "Silken Hollow"
    assert dungeon.category == DungeonCategory.ADVENTURE
    assert dungeon.target_time_seconds == 812
    assert dungeon.target_time_milliseconds == 812000


def test_dungeon_info_format_target_time():
    """Test DungeonInfo target time formatting."""
    dungeon = DungeonInfo(
        dungeon_id=24,
        name="Silken Hollow",
        category=DungeonCategory.ADVENTURE,
        target_time_seconds=812,
    )

    assert dungeon.format_target_time() == "13:32"


def test_dungeon_info_no_target_time():
    """Test DungeonInfo with no target time."""
    dungeon = DungeonInfo(
        dungeon_id=999,
        name="Unknown Dungeon",
        category=DungeonCategory.DUNGEON,
        target_time_seconds=None,
    )

    assert dungeon.target_time_seconds is None
    assert dungeon.target_time_milliseconds is None
    assert dungeon.format_target_time() == "Unknown"


def test_get_dungeon_info_by_int():
    """Test getting dungeon info by integer ID."""
    dungeon = get_dungeon_info(24)

    assert dungeon is not None
    assert dungeon.dungeon_id == 24
    assert dungeon.name == "Silken Hollow"
    assert dungeon.category == DungeonCategory.ADVENTURE


def test_get_dungeon_info_by_string():
    """Test getting dungeon info by string ID."""
    dungeon = get_dungeon_info("24")

    assert dungeon is not None
    assert dungeon.dungeon_id == 24
    assert dungeon.name == "Silken Hollow"


def test_get_dungeon_info_unknown():
    """Test getting dungeon info for unknown ID."""
    dungeon = get_dungeon_info(999)
    assert dungeon is None


def test_get_dungeon_info_invalid_string():
    """Test getting dungeon info with invalid string ID."""
    dungeon = get_dungeon_info("invalid")
    assert dungeon is None


def test_get_target_time():
    """Test getting target time for a dungeon."""
    target_time = get_target_time(24)
    assert target_time == 812


def test_get_target_time_string_id():
    """Test getting target time with string ID."""
    target_time = get_target_time("24")
    assert target_time == 812


def test_get_target_time_unknown():
    """Test getting target time for unknown dungeon."""
    target_time = get_target_time(999)
    assert target_time is None


def test_format_target_time():
    """Test formatting target time."""
    formatted = format_target_time(24)
    assert formatted == "13:32"


def test_format_target_time_unknown():
    """Test formatting target time for unknown dungeon."""
    formatted = format_target_time(999)
    assert formatted == "Unknown"


def test_adventure_dungeons():
    """Test that all adventure dungeons are properly categorized."""
    adventure_ids = [6, 8, 11, 12, 15, 21, 24, 25, 29, 31]

    for dungeon_id in adventure_ids:
        dungeon = DUNGEONS.get(dungeon_id)
        assert dungeon is not None, f"Dungeon {dungeon_id} not found"
        assert dungeon.category == DungeonCategory.ADVENTURE


def test_regular_dungeons():
    """Test that all regular dungeons are properly categorized."""
    regular_ids = [5, 7, 13, 23]

    for dungeon_id in regular_ids:
        dungeon = DUNGEONS.get(dungeon_id)
        assert dungeon is not None, f"Dungeon {dungeon_id} not found"
        assert dungeon.category == DungeonCategory.DUNGEON
        assert dungeon.target_time_seconds is not None


def test_pinnacle_dungeons():
    """Test that pinnacle dungeons are properly categorized."""
    dungeon = DUNGEONS.get(30)
    assert dungeon is not None
    assert dungeon.name == "Xul, The Blood Monolith"
    assert dungeon.category == DungeonCategory.PINNACLE


def test_known_target_times_are_positive():
    """Test that every known target time is a positive number."""
    for dungeon in DUNGEONS.values():
        if dungeon.target_time_seconds is not None:
            assert dungeon.target_time_seconds > 0


def test_season_one_dungeons_have_target_times():
    """Test that all pre-Season 3 dungeons still have their target times."""
    for dungeon_id, dungeon in DUNGEONS.items():
        if dungeon_id < 29:
            assert dungeon.target_time_seconds is not None, (
                f"Dungeon {dungeon_id} missing target time"
            )
