"""Tests for affix mappings."""

from fellowship_recorder.mappings import (
    AFFIX_MAP,
    get_affix_info,
    get_affix_name,
    get_affix_names,
)


class TestGetAffixName:
    """Test get_affix_name function."""

    def test_get_known_affix_name(self):
        """Test getting name for a known affix."""
        assert get_affix_name(4) == "Vayr's Legacy"
        assert get_affix_name(6) == "Asha's Dilemma"
        assert get_affix_name(8) == "Blood Shards"
        assert get_affix_name(19) == "Shadow Lord's Trial"

    def test_get_unknown_affix_name(self):
        """Test getting name for an unknown affix."""
        assert get_affix_name(999) is None
        assert get_affix_name(0) is None
        assert get_affix_name(-1) is None


class TestGetAffixInfo:
    """Test get_affix_info function."""

    def test_get_known_affix_info(self):
        """Test getting full info for a known affix."""
        info = get_affix_info(8)
        assert info is not None
        assert info["name"] == "Blood Shards"
        assert info["type"] == "Curse"
        assert "Blood Shards" in info["description"]

    def test_get_unknown_affix_info(self):
        """Test getting info for an unknown affix."""
        assert get_affix_info(999) is None
        assert get_affix_info(0) is None

    def test_affix_info_structure(self):
        """Test that all affixes have required fields."""
        for affix_id, info in AFFIX_MAP.items():
            assert "name" in info
            assert "type" in info
            assert "description" in info
            assert isinstance(info["name"], str)
            assert isinstance(info["type"], str)
            assert isinstance(info["description"], str)


class TestGetAffixNames:
    """Test get_affix_names function."""

    def test_get_multiple_affix_names(self):
        """Test getting names for multiple affixes."""
        names = get_affix_names([6, 4, 8])
        assert names == ["Asha's Dilemma", "Vayr's Legacy", "Blood Shards"]

    def test_get_empty_list(self):
        """Test getting names for empty list."""
        assert get_affix_names([]) == []

    def test_get_mixed_known_unknown(self):
        """Test getting names with some unknown IDs."""
        names = get_affix_names([6, 999, 4])
        assert names == ["Asha's Dilemma", "Vayr's Legacy"]

    def test_get_all_unknown(self):
        """Test getting names for all unknown IDs."""
        names = get_affix_names([999, 998, 997])
        assert names == []


class TestAffixMap:
    """Test AFFIX_MAP completeness."""

    def test_affix_map_contains_expected_affixes(self):
        """Test that AFFIX_MAP contains expected affix IDs."""
        expected_ids = [4, 6, 8, 9, 11, 12, 13, 14, 15, 16, 19]
        for affix_id in expected_ids:
            assert affix_id in AFFIX_MAP

    def test_affix_types(self):
        """Test that affixes have valid types."""
        valid_types = {"Ascension", "Curse"}
        for info in AFFIX_MAP.values():
            assert info["type"] in valid_types
