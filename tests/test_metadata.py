"""Tests for metadata generation."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from fellowship_recorder.metadata import RecordingMetadata


def test_dungeon_metadata(tmp_path):
    """Test dungeon metadata generation."""
    start_time = datetime(2025, 11, 24, 8, 36, 19)
    duration = 605.0
    end_time = start_time + timedelta(seconds=duration)

    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Ransack of Drakheim",
        dungeon_id=23,
        difficulty_id=31,
        duration=duration,
        completed=True,
        success=True,
        start_time=start_time,
        end_time=end_time,
    )

    json_path = tmp_path / "test.json"
    metadata.to_json(json_path)

    assert json_path.exists()

    with json_path.open() as f:
        data = json.load(f)

    assert data["dungeon_name"] == "Ransack of Drakheim"
    assert data["dungeon_id"] == 23
    assert data["difficulty_id"] == 31
    assert data["duration"] == 605.0
    assert data["completed"] is True
    assert data["success"] is True
    assert "unique_hash" in data
    assert "started_at" in data
    assert "ended_at" in data


def test_metadata_unique_hash():
    """Test that unique hashes are generated consistently."""
    start_time = datetime(2025, 11, 24, 8, 36, 19)

    metadata1 = RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=start_time,
    )

    metadata2 = RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=start_time,
    )

    assert metadata1.unique_hash == metadata2.unique_hash

    metadata3 = RecordingMetadata.from_dungeon(
        dungeon_name="Test Dungeon",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime(2025, 11, 24, 9, 36, 19),
    )

    assert metadata1.unique_hash != metadata3.unique_hash


def test_metadata_different_dungeons():
    """Test that different dungeons generate different hashes."""
    start_time = datetime(2025, 11, 24, 8, 36, 19)

    metadata1 = RecordingMetadata.from_dungeon(
        dungeon_name="Dungeon A",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=start_time,
    )

    metadata2 = RecordingMetadata.from_dungeon(
        dungeon_name="Dungeon B",
        dungeon_id=24,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=start_time,
    )

    assert metadata1.unique_hash != metadata2.unique_hash


def test_metadata_json_excludes_none():
    """Test that None values are excluded from JSON output."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=None,
        difficulty_id=None,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    json_str = metadata.model_dump_json(exclude_none=True)
    data = json.loads(json_str)

    assert "dungeon_id" not in data
    assert "difficulty_id" not in data
    assert "duration" in data


def test_metadata_party():
    """Test metadata with party members."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    assert metadata.party == []

    from fellowship_recorder.metadata import Player

    combatant = Player(player_id="Player-1234", player_name="TestPlayer", hero_id=1)
    metadata.party.append(combatant)

    assert len(metadata.party) == 1
    assert metadata.party[0].player_id == "Player-1234"
    assert metadata.party[0].player_name == "TestPlayer"
    assert metadata.party[0].hero_id == 1


def test_metadata_deaths():
    """Test metadata with deaths."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    assert metadata.deaths is None

    from fellowship_recorder.metadata import Death

    death = Death(
        player_id="Player-1234",
        player_name="Player1",
        hero_id=1,
        occurred_at="2025-11-24T08:36:19Z",
        time_offset=60.0,
    )
    metadata.deaths = [death]

    assert len(metadata.deaths) == 1
    assert metadata.deaths[0].player_name == "Player1"
    assert metadata.deaths[0].time_offset == 60.0


def test_metadata_affixes(tmp_path):
    """Test metadata with affixes."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Wyrmheart",
        dungeon_id=8,
        difficulty_id=30,
        duration=472.0,
        completed=True,
        success=True,
        start_time=datetime(2025, 11, 25, 6, 51, 14),
        affixes=[6, 4, 8, 19],
    )

    assert metadata.affixes is not None
    assert len(metadata.affixes) == 4

    assert metadata.affixes[0].affix_id == 6
    assert metadata.affixes[0].affix_name == "Asha's Dilemma"
    assert metadata.affixes[1].affix_id == 4
    assert metadata.affixes[1].affix_name == "Vayr's Legacy"
    assert metadata.affixes[2].affix_id == 8
    assert metadata.affixes[2].affix_name == "Blood Shards"
    assert metadata.affixes[3].affix_id == 19
    assert metadata.affixes[3].affix_name == "Shadow Lord's Trial"

    json_path = tmp_path / "test_affixes.json"
    metadata.to_json(json_path)

    with json_path.open() as f:
        data = json.load(f)

    assert "affixes" in data
    assert len(data["affixes"]) == 4
    assert data["affixes"][0]["affix_id"] == 6
    assert data["affixes"][0]["affix_name"] == "Asha's Dilemma"


def test_generate_chapters():
    """Test chapter generation from encounters and deaths."""
    from fellowship_recorder.metadata import Death, Encounter

    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=600.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    metadata.encounters = [
        Encounter(boss_id=1, boss_name="Boss 1", start_time_offset=10.0, end_time_offset=50.0, success=False),
        Encounter(boss_id=1, boss_name="Boss 1", start_time_offset=60.0, end_time_offset=100.0, success=True),
        Encounter(boss_id=2, boss_name="Boss 2", start_time_offset=120.0, end_time_offset=180.0, success=True),
    ]

    metadata.deaths = [
        Death(player_id="P1", player_name="Player1", hero_id=1, hero_name="Rime", occurred_at="2025-11-24T08:36:19Z", time_offset=30.0),
        Death(player_id="P2", player_name="Player2", hero_id=2, occurred_at="2025-11-24T08:36:49Z", time_offset=80.0),
    ]

    chapters = metadata.generate_chapters()

    assert len(chapters) == 5

    assert chapters[0].title == "Boss 1 (Attempt 1)"
    assert chapters[0].time_offset == 5.0

    assert chapters[1].title == "Death: Rime"
    assert chapters[1].time_offset == 25.0

    assert chapters[2].title == "Boss 1 (Kill)"
    assert chapters[2].time_offset == 55.0

    assert chapters[3].title == "Death: Player2"
    assert chapters[3].time_offset == 75.0

    assert chapters[4].title == "Boss 2 (Kill)"
    assert chapters[4].time_offset == 115.0


def test_generate_chapters_empty():
    """Test chapter generation with no encounters or deaths."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    chapters = metadata.generate_chapters()
    assert chapters == []


def test_completed_and_success_flags():
    """Test completed and success flag combinations."""
    metadata_success = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )
    assert metadata_success.completed is True
    assert metadata_success.success is True

    metadata_failed = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=False,
        start_time=datetime.now(),
    )
    assert metadata_failed.completed is True
    assert metadata_failed.success is False

    metadata_abandoned = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=False,
        success=False,
        start_time=datetime.now(),
    )
    assert metadata_abandoned.completed is False
    assert metadata_abandoned.success is False


def test_remaining_time_challenge_mode():
    """Test remaining_time and target_time for challenge mode dungeons.

    Silken Hollow (dungeon_id=24) has target_time=812 seconds.
    Duration of 700 seconds should leave 112 seconds remaining.
    """
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Silken Hollow",
        dungeon_id=24,
        difficulty_id=30,
        duration=700.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
        mode_id="0",
    )

    assert metadata.target_time == 812.0
    assert metadata.remaining_time is not None
    assert metadata.remaining_time == 112.0


def test_remaining_time_quick_play():
    """Test that target_time and remaining_time are None for quick play mode."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Silken Hollow",
        dungeon_id=24,
        difficulty_id=30,
        duration=700.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
        mode_id="1",
    )

    assert metadata.target_time is None
    assert metadata.remaining_time is None


def test_remaining_time_unknown_dungeon():
    """Test that target_time and remaining_time are None when target time is unknown."""
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Unknown Dungeon",
        dungeon_id=999,
        difficulty_id=30,
        duration=700.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
        mode_id="0",
    )

    assert metadata.target_time is None
    assert metadata.remaining_time is None


def test_remaining_time_negative():
    """Test remaining_time when dungeon takes longer than target time.

    Godfall Quarry (dungeon_id=25) has target_time=738 seconds.
    Duration of 800 seconds should result in -62 seconds remaining.
    """
    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Godfall Quarry",
        dungeon_id=25,
        difficulty_id=30,
        duration=800.0,
        completed=True,
        success=False,
        start_time=datetime.now(),
        mode_id="0",
    )

    assert metadata.target_time == 738.0
    assert metadata.remaining_time is not None
    assert metadata.remaining_time == -62.0


def test_kill_objective_model():
    """Test KillObjective model in metadata."""
    from fellowship_recorder.metadata import KillObjective

    metadata = RecordingMetadata.from_dungeon(
        dungeon_name="Test",
        dungeon_id=23,
        difficulty_id=31,
        duration=100.0,
        completed=True,
        success=True,
        start_time=datetime.now(),
    )

    kill_objective = KillObjective(
        completed_at="2025-11-24T08:40:00.000Z",
        completion_offset=240.0,
        final_score=101.5,
    )

    metadata.kill_objective = kill_objective

    assert metadata.kill_objective is not None
    assert metadata.kill_objective.completed_at == "2025-11-24T08:40:00.000Z"
    assert metadata.kill_objective.completion_offset == 240.0
    assert metadata.kill_objective.final_score == 101.5
