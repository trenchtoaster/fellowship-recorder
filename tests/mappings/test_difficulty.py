"""Tests for difficulty tier conversion."""

import pytest
from pydantic import ValidationError

from fellowship_recorder.mappings import DifficultyTier, format_difficulty, get_difficulty_tier


class TestDifficultyTier:
    """Tests for DifficultyTier model."""

    def test_basic_tier_creation(self):
        """Test creating a basic difficulty tier."""
        tier = DifficultyTier(tier_name="Eternal", tier_level=45)
        assert tier.tier_name == "Eternal"
        assert tier.tier_level == 45
        assert tier.is_quick_play is False

    def test_quick_play_tier(self):
        """Test creating a quick play tier."""
        tier = DifficultyTier(tier_name="Quick Play", tier_level=1, is_quick_play=True)
        assert tier.tier_name == "Quick Play"
        assert tier.is_quick_play is True

    def test_tier_level_validation(self):
        """Test that tier_level must be >= 1."""
        with pytest.raises(ValidationError):
            DifficultyTier(tier_name="Test", tier_level=0)

        with pytest.raises(ValidationError):
            DifficultyTier(tier_name="Test", tier_level=-5)

    def test_str_regular_tier(self):
        """Test string representation of regular tier."""
        tier = DifficultyTier(tier_name="Eternal", tier_level=45)
        assert str(tier) == "Eternal 45"

    def test_str_quick_play(self):
        """Test string representation of quick play tier."""
        tier = DifficultyTier(tier_name="Quick Play", tier_level=2, is_quick_play=True)
        assert str(tier) == "Quick Play"


class TestGetDifficultyTier:
    """Tests for get_difficulty_tier function."""

    def test_contender_tiers(self):
        """Test Contender tier (levels 1-7)."""
        for level in range(1, 8):
            tier = get_difficulty_tier(level)
            assert tier.tier_name == "Contender"
            assert tier.tier_level == level
            assert tier.is_quick_play is False

    def test_adept_tiers(self):
        """Test Adept tier (levels 9-15)."""
        for level in range(9, 16):
            tier = get_difficulty_tier(level)
            assert tier.tier_name == "Adept"
            assert tier.tier_level == level - 8
            assert tier.is_quick_play is False

    def test_champion_tiers(self):
        """Test Champion tier (levels 17-23)."""
        for level in range(17, 24):
            tier = get_difficulty_tier(level)
            assert tier.tier_name == "Champion"
            assert tier.tier_level == level - 16
            assert tier.is_quick_play is False

    def test_paragon_tiers(self):
        """Test Paragon tier (levels 25-31)."""
        for level in range(25, 32):
            tier = get_difficulty_tier(level)
            assert tier.tier_name == "Paragon"
            assert tier.tier_level == level - 24
            assert tier.is_quick_play is False

    def test_eternal_tiers(self):
        """Test Eternal tier (levels 33+)."""
        test_levels = [33, 40, 50, 77, 100]
        for level in test_levels:
            tier = get_difficulty_tier(level)
            assert tier.tier_name == "Eternal"
            assert tier.tier_level == level - 32
            assert tier.is_quick_play is False

    def test_gap_levels(self):
        """Test gap levels return Unknown."""
        gap_levels = [8, 16, 24, 32]
        for level in gap_levels:
            tier = get_difficulty_tier(level)
            assert tier.tier_name == "Unknown"
            assert tier.tier_level == level
            assert tier.is_quick_play is False

    def test_quick_play_string_mode(self):
        """Test Quick Play mode with string mode parameter."""
        tier = get_difficulty_tier(1, mode="1")
        assert tier.tier_name == "Quick Play"
        assert tier.is_quick_play is True

    def test_quick_play_int_mode(self):
        """Test Quick Play mode with integer mode parameter."""
        tier = get_difficulty_tier(1, mode=1)
        assert tier.tier_name == "Quick Play"
        assert tier.is_quick_play is True

    def test_challenge_mode_string(self):
        """Test Challenge mode with string mode parameter."""
        tier = get_difficulty_tier(5, mode="0")
        assert tier.tier_name == "Contender"
        assert tier.tier_level == 5
        assert tier.is_quick_play is False

    def test_challenge_mode_int(self):
        """Test Challenge mode with integer mode parameter."""
        tier = get_difficulty_tier(5, mode=0)
        assert tier.tier_name == "Contender"
        assert tier.tier_level == 5
        assert tier.is_quick_play is False

    def test_none_mode_defaults_to_challenge(self):
        """Test that None mode defaults to challenge behavior."""
        tier = get_difficulty_tier(5, mode=None)
        assert tier.tier_name == "Contender"
        assert tier.tier_level == 5
        assert tier.is_quick_play is False


class TestFormatDifficulty:
    """Tests for format_difficulty function."""

    def test_format_none_difficulty(self):
        """Test formatting None difficulty."""
        assert format_difficulty(None) == "Unknown"

    def test_format_contender(self):
        """Test formatting Contender difficulty."""
        assert format_difficulty(5) == "Contender 5"

    def test_format_adept(self):
        """Test formatting Adept difficulty."""
        assert format_difficulty(12) == "Adept 4"

    def test_format_champion(self):
        """Test formatting Champion difficulty."""
        assert format_difficulty(20) == "Champion 4"

    def test_format_paragon(self):
        """Test formatting Paragon difficulty."""
        assert format_difficulty(31) == "Paragon 7"

    def test_format_eternal(self):
        """Test formatting Eternal difficulty."""
        assert format_difficulty(77) == "Eternal 45"

    def test_format_quick_play_string_mode(self):
        """Test formatting Quick Play with string mode."""
        assert format_difficulty(1, mode="1") == "Quick Play"

    def test_format_quick_play_int_mode(self):
        """Test formatting Quick Play with integer mode."""
        assert format_difficulty(1, mode=1) == "Quick Play"

    def test_format_challenge_mode(self):
        """Test formatting Challenge mode."""
        assert format_difficulty(31, mode="0") == "Paragon 7"

    def test_format_gap_level(self):
        """Test formatting gap level."""
        assert format_difficulty(8) == "Unknown 8"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_high_eternal_level(self):
        """Test very high eternal difficulty."""
        tier = get_difficulty_tier(200)
        assert tier.tier_name == "Eternal"
        assert tier.tier_level == 168

    def test_boundary_between_tiers(self):
        """Test boundaries between difficulty tiers."""
        assert get_difficulty_tier(7).tier_name == "Contender"
        assert get_difficulty_tier(8).tier_name == "Unknown"
        assert get_difficulty_tier(9).tier_name == "Adept"

        assert get_difficulty_tier(15).tier_name == "Adept"
        assert get_difficulty_tier(16).tier_name == "Unknown"
        assert get_difficulty_tier(17).tier_name == "Champion"

        assert get_difficulty_tier(23).tier_name == "Champion"
        assert get_difficulty_tier(24).tier_name == "Unknown"
        assert get_difficulty_tier(25).tier_name == "Paragon"

        assert get_difficulty_tier(31).tier_name == "Paragon"
        assert get_difficulty_tier(32).tier_name == "Unknown"
        assert get_difficulty_tier(33).tier_name == "Eternal"

    def test_quick_play_overrides_difficulty_tier(self):
        """Test that Quick Play mode overrides tier calculation regardless of difficulty number."""
        tier = get_difficulty_tier(1, mode="1")
        assert tier.tier_name == "Quick Play"
        assert tier.is_quick_play is True
