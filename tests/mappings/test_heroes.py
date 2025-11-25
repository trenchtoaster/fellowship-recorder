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

    def test_get_unknown_hero_name(self):
        """Test getting name for unknown hero."""
        assert get_hero_name(999) is None
        assert get_hero_name(1) is None
        assert get_hero_name(-1) is None

    def test_get_hero_id_zero(self):
        """Test getting hero ID 0 (no hero)."""
        assert get_hero_name(0) is None


class TestHeroMap:
    """Test HERO_ID_MAP completeness."""

    def test_hero_map_contains_expected_heroes(self):
        """Test that HERO_ID_MAP contains expected hero IDs."""
        expected_ids = [0, 2, 7, 10, 11, 13, 14, 17, 20, 22]
        for hero_id in expected_ids:
            assert hero_id in HERO_ID_MAP

    def test_hero_names_are_strings_or_none(self):
        """Test that all hero names are strings or None."""
        for hero_id, hero_name in HERO_ID_MAP.items():
            assert hero_name is None or isinstance(hero_name, str)
            if hero_name is not None:
                assert len(hero_name) > 0

    def test_no_duplicate_hero_names(self):
        """Test that there are no duplicate hero names."""
        names = [name for name in HERO_ID_MAP.values() if name is not None]
        assert len(names) == len(set(names))
