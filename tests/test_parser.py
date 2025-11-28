"""Tests for Fellowship combat log parser."""

from datetime import datetime
from pathlib import Path

import pytest

from fellowship_recorder.parser import CombatLogEvent, CombatLogParser, EventType


@pytest.fixture
def parser():
    """Create a parser instance."""
    return CombatLogParser()


@pytest.fixture
def sample_log():
    """Get path to sample dungeon log."""
    return Path(__file__).parent / "sample_logs" / "dungeon_sample.txt"


def test_parse_logging_started(parser):
    """Test parsing LOGGING_STARTED event."""
    line = "2025-11-24T08:34:57.091+08:00|LOGGING_STARTED|4|0.2.4.1 cl:91506|1"
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.LOGGING_STARTED
    assert not event.is_start_event
    assert not event.is_end_event


def test_parse_zone_change(parser):
    """Test parsing ZONE_CHANGE event."""
    line = '2025-11-24T08:36:15.527+08:00|ZONE_CHANGE|"Ransack of Drakheim"|23|31|'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.ZONE_CHANGE
    assert event.metadata["dungeon_name"] == "Ransack of Drakheim"
    assert event.metadata["dungeon_id"] == "23"
    assert event.metadata["difficulty_id"] == "31"


def test_zone_change_leaving_stronghold_is_start_event(parser):
    """Test that ZONE_CHANGE leaving Stronghold is treated as a start event."""
    line = '2025-11-26T10:26:58.573+08:00|ZONE_CHANGE|"Ransack of Drakheim"|23|31|'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.ZONE_CHANGE
    assert event.is_start_event
    assert not event.is_end_event


def test_zone_change_entering_stronghold_is_end_event(parser):
    """Test that ZONE_CHANGE entering Stronghold is treated as an end event."""
    line = '2025-11-26T10:39:31.381+08:00|ZONE_CHANGE|"The Stronghold"|17|1|'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.ZONE_CHANGE
    assert not event.is_start_event
    assert event.is_end_event


def test_parse_dungeon_start(parser):
    """Test parsing DUNGEON_START event."""
    line = '2025-11-24T08:36:19.097+08:00|DUNGEON_START|"Ransack of Drakheim"|23|31|[6,4]|0'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.DUNGEON_START
    assert event.is_start_event
    assert not event.is_end_event

    assert event.metadata["dungeon_name"] == "Ransack of Drakheim"
    assert event.metadata["dungeon_id"] == "23"
    assert event.metadata["difficulty_id"] == "31"
    assert event.metadata["affixes"] == "[6,4]"
    assert event.metadata["mode"] == "0"


def test_parse_dungeon_end(parser):
    """Test parsing DUNGEON_END event."""
    line = '2025-11-24T08:52:36.577+08:00|DUNGEON_END|"Ransack of Drakheim"|23|31|[6,4]|1|972907|605.000000|1|0'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.DUNGEON_END
    assert not event.is_start_event
    assert event.is_end_event

    assert event.metadata["dungeon_name"] == "Ransack of Drakheim"
    assert event.metadata["dungeon_id"] == "23"
    assert event.metadata["difficulty_id"] == "31"
    assert event.metadata["affixes"] == "[6,4]"
    assert event.metadata["mode"] == "1"
    assert event.metadata["duration"] == "972907"
    assert event.metadata["success"] == "1"


def test_parse_player_death(parser):
    """Test that we can identify player death events."""
    line = '2025-11-24T08:50:15.235+08:00|UNIT_DEATH|Player-5000|"Player5"|Npc-1234567890-30|"Shadow Assassin"|2456|"Shadow Strike"|0|0.850000'

    assert "UNIT_DEATH" in line
    assert "Player-5000" in line


def test_parse_ally_death(parser):
    """Test parsing ALLY_DEATH lines."""
    line = '2025-11-24T08:50:15.235+08:00|ALLY_DEATH|Player-5000|"Player5"|Npc-1234567890-30|"Shadow Assassin"|2456|"Shadow Strike"|0|0.850000'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.ALLY_DEATH
    assert event.metadata["player_name"] == "Player5"


def test_parse_sample_log(parser, sample_log):
    """Test parsing the entire sample log file."""
    events = []

    with open(sample_log) as f:
        for line in f:
            event = parser.parse_line(line.strip())
            if event:
                events.append(event)

    assert len(events) > 0

    start_events = [e for e in events if e.event_type == EventType.DUNGEON_START]
    end_events = [e for e in events if e.event_type == EventType.DUNGEON_END]

    assert len(start_events) == 1
    assert len(end_events) == 1

    start = start_events[0]
    end = end_events[0]

    assert start.metadata["dungeon_name"] == end.metadata["dungeon_name"]
    assert start.metadata["dungeon_id"] == end.metadata["dungeon_id"]
    assert start.metadata["difficulty_id"] == end.metadata["difficulty_id"]


def test_timestamp_parsing(parser):
    """Test ISO 8601 timestamp parsing with timezone."""
    line = '2025-11-24T08:36:19.097+08:00|DUNGEON_START|"Ransack of Drakheim"|23|31|[6,4]|0'
    event = parser.parse_line(line)

    assert event is not None
    assert event.timestamp.year == 2025
    assert event.timestamp.month == 11
    assert event.timestamp.day == 24
    assert event.timestamp.hour == 8
    assert event.timestamp.minute == 36


def test_ignore_unknown_events(parser):
    """Test that unknown events return None."""
    line = '2025-11-24T08:37:42.220+08:00|ABILITY_DAMAGE|Player-2000|"Player2"|Npc-228589728-8|"Drakheim Guard"|126|"Starfall Volley"|0|0|0|-1|0|1668|Magical|Hit|...'
    event = parser.parse_line(line)

    assert event is None


def test_empty_line(parser):
    """Test parsing empty line."""
    event = parser.parse_line("")
    assert event is None


def test_malformed_line(parser):
    """Test parsing malformed line."""
    event = parser.parse_line("this is not a valid log line")
    assert event is None


def test_ignore_combat_events(parser):
    """Test that parser ignores non-recordable combat events."""
    combat_lines = [
        '2025-11-24T08:35:09.914+08:00|ABILITY_PERIODIC_DAMAGE|Environment-0|"Environment"|Player-3182440752|"mackreal"|144|"Burning"|1|200|0|-1|0|200|Magical|Hit|0|0|0|0.000000|0.000000|0.000000|[]|107892|108092|0|3728.554688|53033.015625|0.343750|[(1,1440.00,1440.00),(4,13.13,100.00),(5,4.00,4.00)]',
        '2025-11-24T08:35:10.045+08:00|ABILITY_ACTIVATED|Player-1567633680|"Kuraudo"|1721|"Mount Bloodfang Matriarch"|0|UnrecognizedType-0|"0"|179222|179222|0|1705.914062|53063.234375|5.822248|[(3,0.00,27852.70),(4,43.17,100.00)]',
        '2025-11-24T08:35:16.991+08:00|EFFECT_REMOVED|Player-1567633680|"Kuraudo"|Player-1567633680|"Kuraudo"|1|"Mounted"|0.000000|0|DEBUFF|179222|179222|0|1693.789062|46295.273438|4.259748|[(3,0.00,27852.70),(4,46.38,100.00)]|1721|"Mount Bloodfang Matriarch"|-1',
        '2025-11-24T08:35:17.627+08:00|ABILITY_DAMAGE|Player-1567633680|"Kuraudo"|Npc-228589728-5|"Training Dummy"|2357|"Razor Shrapnel"|985|0|0|-1|0|2197|Physical|Hit|179222|179222|0|1491.578125|45883.351562|4.259748|[(3,0.00,27852.70),(4,47.61,100.00)]|1337|1337|0|1080.367188|45263.492188|1.562500|[]',
    ]

    for line in combat_lines:
        event = parser.parse_line(line)
        assert event is None, f"Expected None for combat event line: {line[:50]}..."


def test_parser_robustness_with_invalid_data(parser):
    """Test that parser doesn't crash on various invalid inputs."""
    invalid_lines = [
        "",
        "|",
        "|||",
        "941",
        "Y_PERIODIC_DAMAGE",
        "2025-11-24T08:35:09.914+08:00",
        "2025-11-24T08:35:09.914+08:00|",
        "invalid_timestamp|DUNGEON_START|test",
        "2025-99-99T99:99:99.999+99:99|DUNGEON_START|test",
    ]

    for line in invalid_lines:
        event = parser.parse_line(line)
        assert event is None, f"Expected None for invalid line: {line}"


def test_combat_log_event_pydantic():
    """Test CombatLogEvent as Pydantic model."""
    event = CombatLogEvent(
        timestamp=datetime(2025, 11, 24, 14, 30, 45),
        event_type=EventType.DUNGEON_START,
        raw_line='2025-11-24T08:36:19.097+08:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0',
        metadata={"dungeon_name": "Test Dungeon", "difficulty_id": "31"},
    )

    assert event.is_start_event
    assert not event.is_end_event

    assert event.model_dump()["event_type"] == EventType.DUNGEON_START
    assert event.metadata["dungeon_name"] == "Test Dungeon"


def test_combat_log_event_validation():
    """Test that Pydantic validates types."""
    event = CombatLogEvent(
        timestamp=datetime.now(),
        event_type=EventType.DUNGEON_END,
        raw_line="test",
        metadata={"dungeon_name": "Test Zone"},
    )

    assert event.event_type == EventType.DUNGEON_END


def test_combat_log_event_mutability():
    """Test that Pydantic models can be modified."""
    event = CombatLogEvent(
        timestamp=datetime.now(),
        event_type=EventType.DUNGEON_START,
        raw_line="test",
        metadata={},
    )

    event.metadata["new_key"] = "new_value"
    assert event.metadata["new_key"] == "new_value"


def test_event_type_enum():
    """Test EventType enum values."""
    assert EventType.DUNGEON_START.value == "DUNGEON_START"
    assert EventType.DUNGEON_END.value == "DUNGEON_END"
    assert EventType.ENCOUNTER_START.value == "ENCOUNTER_START"
    assert EventType.ENCOUNTER_END.value == "ENCOUNTER_END"
    assert EventType.ZONE_CHANGE.value == "ZONE_CHANGE"
    assert EventType.LOGGING_STARTED.value == "LOGGING_STARTED"


def test_parse_unit_death_with_kill_score(parser):
    """Test parsing UNIT_DEATH event with kill_score."""
    line = '2025-11-24T08:50:15.235+08:00|UNIT_DEATH|Npc-1234567890-30|"Drakheim Warlord"|Player-5000|"Player5"|1312|"Heartseeker Barrage"|0|0.85'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.UNIT_DEATH
    assert event.metadata["unit_name"] == "Drakheim Warlord"
    assert event.metadata["kill_score"] == "0.85"


def test_parse_unit_death_no_kill_score(parser):
    """Test parsing UNIT_DEATH event with missing kill_score field."""
    line = '2025-11-24T08:50:15.235+08:00|UNIT_DEATH|Npc-1234567890-30|"Goblin"'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.UNIT_DEATH
    assert "kill_score" not in event.metadata


def test_parse_unit_death_shadowlord(parser):
    """Test parsing UNIT_DEATH event for Shadow Lord Emissary."""
    line = '2025-11-24T08:50:15.235+08:00|UNIT_DEATH|Npc-12345678|"Emissary of the Shadow Lord"|Player-1|"TestPlayer"|1312|"Heartseeker Barrage"|0|0.0'
    event = parser.parse_line(line)

    assert event is not None
    assert event.event_type == EventType.UNIT_DEATH
    assert event.metadata["unit_name"] == "Emissary of the Shadow Lord"
    assert event.metadata["kill_score"] == "0.0"
