"""Tests for mode mappings."""

from fellowship_recorder.mappings import get_mode_name


class TestGetModeName:
    """Test get_mode_name function."""

    def test_challenge_mode_string(self):
        """Test Challenge mode with string input."""
        assert get_mode_name("0") == "Challenge"

    def test_challenge_mode_int(self):
        """Test Challenge mode with int input."""
        assert get_mode_name(0) == "Challenge"

    def test_quick_play_mode_string(self):
        """Test Quick Play mode with string input."""
        assert get_mode_name("1") == "Quick Play"

    def test_quick_play_mode_int(self):
        """Test Quick Play mode with int input."""
        assert get_mode_name(1) == "Quick Play"

    def test_none_mode(self):
        """Test None mode returns Unknown."""
        assert get_mode_name(None) == "Unknown"

    def test_unknown_mode(self):
        """Test unknown mode returns Unknown."""
        assert get_mode_name(2) == "Unknown"
        assert get_mode_name("2") == "Unknown"
        assert get_mode_name("999") == "Unknown"
        assert get_mode_name("invalid") == "Unknown"

