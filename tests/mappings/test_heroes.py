"""Tests for hero mappings."""

from fellowship_recorder.mappings import HERO_ID_MAP, get_hero_name


class TestGetHeroName:
    """Test get_hero_name function."""

    def test_get_known_hero_name(self):
        """Test getting name for known heroes."""
        assert get_hero_name(2) == "Elarion"
        assert get_hero_name(7) == "Ardeos"
        assert get_hero_name(10) == "Tariq"
        assert get_hero_name(11) == "Mara"
        assert get_hero_name(13) == "Meiko"
        assert get_hero_name(14) == "Sylvie"
        assert get_hero_name(17) == "Rime"
        assert get_hero_name(20) == "Vigour"
        assert get_hero_name(22) == "Helena"

    def test_get_season_two_and_three_heroes(self):
        """Test heroes added in Seasons 2 and 3."""
        assert get_hero_name(9) == "Gunde"
        assert get_hero_name(24) == "Aeona"
        assert get_hero_name(25) == "Xavian"

    def test_get_unknown_hero_name(self):
        """Test getting name for unknown hero."""
        assert get_hero_name(999) == "Unknown"
        assert get_hero_name(1) == "Unknown"
        assert get_hero_name(-1) == "Unknown"

    def test_get_hero_id_zero(self):
        """Test getting hero ID 0 (no hero)."""
        assert get_hero_name(0) == "Unknown"


class TestHeroMap:
    """Test HERO_ID_MAP completeness."""

    def test_hero_map_contains_expected_heroes(self):
        """Test that HERO_ID_MAP contains expected hero IDs."""
        expected_ids = [2, 7, 9, 10, 11, 13, 14, 17, 20, 22, 24, 25]
        for hero_id in expected_ids:
            assert hero_id in HERO_ID_MAP

    def test_hero_names_are_strings(self):
        """Test that all hero names are strings."""
        for hero_id, hero_name in HERO_ID_MAP.items():
            assert isinstance(hero_name, str)
            assert len(hero_name) > 0

    def test_no_duplicate_hero_names(self):
        """Test that there are no duplicate hero names."""
        names = list(HERO_ID_MAP.values())
        assert len(names) == len(set(names))
