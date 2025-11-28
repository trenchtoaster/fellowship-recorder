"""Tests for CLI parse_log module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from fellowship_recorder.cli.parse_log import (
    get_metadata_filename,
    parse_combat_log,
    regenerate_all_metadata,
)
from fellowship_recorder.metadata import RecordingMetadata


@pytest.fixture
def sample_log() -> Path:
    return Path(__file__).parent.parent / "sample_logs" / "dungeon_sample.txt"


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


class TestParseCombatLog:
    def test_parse_single_dungeon_run(self, sample_log: Path):
        runs = parse_combat_log(sample_log)

        assert len(runs) == 1
        assert runs[0].dungeon_name == "Ransack of Drakheim"
        assert runs[0].dungeon_id == 23
        assert runs[0].difficulty_id == 31
        assert runs[0].completed is True
        assert runs[0].success is True

    def test_parse_extracts_duration(self, sample_log: Path):
        runs = parse_combat_log(sample_log)

        assert len(runs) == 1
        assert runs[0].duration == pytest.approx(972.907, rel=0.01)

    def test_parse_extracts_affixes(self, sample_log: Path):
        runs = parse_combat_log(sample_log)

        assert len(runs) == 1
        assert runs[0].affixes is not None
        affix_ids = [a.affix_id for a in runs[0].affixes]
        assert 6 in affix_ids
        assert 4 in affix_ids

    def test_parse_extracts_timestamps(self, sample_log: Path):
        runs = parse_combat_log(sample_log)

        assert len(runs) == 1
        assert runs[0].started_at is not None
        assert runs[0].ended_at is not None
        assert "2025-11-24" in runs[0].started_at

    def test_parse_with_output_file(self, sample_log: Path, tmp_path: Path):
        output_file = tmp_path / "metadata.json"
        runs = parse_combat_log(sample_log, output_file)

        assert len(runs) == 1
        assert output_file.exists()

    def test_parse_empty_log(self, tmp_path: Path):
        empty_log = tmp_path / "empty.txt"
        empty_log.write_text("")

        runs = parse_combat_log(empty_log)

        assert len(runs) == 0

    def test_parse_log_without_dungeon_end(self, tmp_path: Path):
        incomplete_log = tmp_path / "incomplete.txt"
        incomplete_log.write_text(
            '2025-11-24T08:36:19.097+08:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0\n'
        )

        runs = parse_combat_log(incomplete_log)

        assert len(runs) == 0

    def test_parse_multiple_dungeon_runs(self, tmp_path: Path):
        multi_run_log = tmp_path / "multi_run.txt"
        multi_run_log.write_text(
            '2025-11-24T08:00:00.000+08:00|DUNGEON_START|"Dungeon A"|1|31|[6,4]|0\n'
            '2025-11-24T08:10:00.000+08:00|DUNGEON_END|"Dungeon A"|1|31|[6,4]|1|600000|600.0|1|0\n'
            '2025-11-24T09:00:00.000+08:00|DUNGEON_START|"Dungeon B"|2|31|[6,4]|0\n'
            '2025-11-24T09:15:00.000+08:00|DUNGEON_END|"Dungeon B"|2|31|[6,4]|1|900000|900.0|1|0\n'
        )

        runs = parse_combat_log(multi_run_log)

        assert len(runs) == 2
        assert runs[0].dungeon_name == "Dungeon A"
        assert runs[1].dungeon_name == "Dungeon B"

    def test_parse_does_not_write_multiple_runs_to_single_file(
        self, tmp_path: Path, capsys
    ):
        multi_run_log = tmp_path / "multi_run.txt"
        multi_run_log.write_text(
            '2025-11-24T08:00:00.000+08:00|DUNGEON_START|"Dungeon A"|1|31|[6,4]|0\n'
            '2025-11-24T08:10:00.000+08:00|DUNGEON_END|"Dungeon A"|1|31|[6,4]|1|600000|600.0|1|0\n'
            '2025-11-24T09:00:00.000+08:00|DUNGEON_START|"Dungeon B"|2|31|[6,4]|0\n'
            '2025-11-24T09:15:00.000+08:00|DUNGEON_END|"Dungeon B"|2|31|[6,4]|1|900000|900.0|1|0\n'
        )
        output_file = tmp_path / "output.json"

        runs = parse_combat_log(multi_run_log, output_file)

        assert len(runs) == 2
        assert not output_file.exists()
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_parse_failed_dungeon_run(self, tmp_path: Path):
        failed_log = tmp_path / "failed.txt"
        failed_log.write_text(
            '2025-11-24T08:00:00.000+08:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0\n'
            '2025-11-24T08:10:00.000+08:00|DUNGEON_END|"Test Dungeon"|23|31|[6,4]|0|600000|600.0|0|0\n'
        )

        runs = parse_combat_log(failed_log)

        assert len(runs) == 1
        assert runs[0].success is False

    def test_parse_zone_change_ends_run(self, tmp_path: Path):
        zone_change_log = tmp_path / "zone_change.txt"
        zone_change_log.write_text(
            '2025-11-24T08:00:00.000+08:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0\n'
            '2025-11-24T08:10:00.000+08:00|ZONE_CHANGE|"The Stronghold"|17|1|\n'
        )

        runs = parse_combat_log(zone_change_log)

        assert len(runs) == 1
        assert runs[0].completed is False


class TestGetMetadataFilename:
    def test_generates_filename_with_timestamp(self):
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Ransack of Drakheim",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            completed=True,
            success=True,
            start_time=datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc),
        )

        filename = get_metadata_filename(metadata)

        assert filename.endswith(".json")
        assert "Ransack_of_Drakheim" in filename
        assert "Paragon_7" in filename

    def test_sanitizes_special_characters(self):
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test: Dungeon/Name",
            dungeon_id=23,
            difficulty_id=31,
            duration=605.0,
            completed=True,
            success=True,
            start_time=datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc),
        )

        filename = get_metadata_filename(metadata)

        assert ":" not in filename
        assert "/" not in filename

    def test_handles_unknown_difficulty(self):
        metadata = RecordingMetadata.from_dungeon(
            dungeon_name="Test Dungeon",
            dungeon_id=23,
            difficulty_id=999,
            duration=605.0,
            completed=True,
            success=True,
            start_time=datetime(2025, 11, 24, 8, 36, 19, tzinfo=timezone.utc),
        )

        filename = get_metadata_filename(metadata)

        assert filename.endswith(".json")
        assert "Test_Dungeon" in filename


class TestRegenerateAllMetadata:
    def test_regenerates_from_log_files(
        self, sample_log: Path, temp_log_dir: Path, temp_output_dir: Path
    ):
        import shutil

        dest_log = temp_log_dir / "CombatLog_test.txt"
        shutil.copy(sample_log, dest_log)

        count = regenerate_all_metadata(temp_log_dir, temp_output_dir)

        assert count == 1
        json_files = list(temp_output_dir.glob("*.json"))
        assert len(json_files) == 1

    def test_skips_incomplete_runs(self, temp_log_dir: Path, temp_output_dir: Path):
        incomplete_log = temp_log_dir / "CombatLog_incomplete.txt"
        incomplete_log.write_text(
            '2025-11-24T08:00:00.000+08:00|DUNGEON_START|"Test Dungeon"|23|31|[6,4]|0\n'
            '2025-11-24T08:10:00.000+08:00|ZONE_CHANGE|"The Stronghold"|17|1|\n'
        )

        count = regenerate_all_metadata(temp_log_dir, temp_output_dir)

        assert count == 0
        json_files = list(temp_output_dir.glob("*.json"))
        assert len(json_files) == 0

    def test_handles_empty_directory(self, temp_log_dir: Path, temp_output_dir: Path):
        count = regenerate_all_metadata(temp_log_dir, temp_output_dir)

        assert count == 0

    def test_processes_multiple_log_files(
        self, temp_log_dir: Path, temp_output_dir: Path
    ):
        for i in range(3):
            log_file = temp_log_dir / f"CombatLog_{i}.txt"
            log_file.write_text(
                f'2025-11-24T0{i}:00:00.000+08:00|DUNGEON_START|"Dungeon {i}"|{i}|31|[6,4]|0\n'
                f'2025-11-24T0{i}:10:00.000+08:00|DUNGEON_END|"Dungeon {i}"|{i}|31|[6,4]|1|600000|600.0|1|0\n'
            )

        count = regenerate_all_metadata(temp_log_dir, temp_output_dir)

        assert count == 3
        json_files = list(temp_output_dir.glob("*.json"))
        assert len(json_files) == 3


class TestMain:
    def test_main_with_list_flag(self, sample_log: Path, capsys):
        with patch(
            "sys.argv", ["parse-log", str(sample_log), "--list"]
        ):
            from fellowship_recorder.cli.parse_log import main

            main()

        captured = capsys.readouterr()
        assert "Ransack of Drakheim" in captured.out
        assert "1." in captured.out

    def test_main_with_json_output(self, sample_log: Path, capsys):
        with patch(
            "sys.argv", ["parse-log", str(sample_log), "--run", "1", "--json"]
        ):
            from fellowship_recorder.cli.parse_log import main

            main()

        captured = capsys.readouterr()
        assert "Ransack of Drakheim" in captured.out
        assert "dungeon_id" in captured.out

    def test_main_with_output_file(self, sample_log: Path, tmp_path: Path):
        output_file = tmp_path / "output.json"

        with patch(
            "sys.argv",
            ["parse-log", str(sample_log), "--run", "1", "-o", str(output_file)],
        ):
            from fellowship_recorder.cli.parse_log import main

            main()

        assert output_file.exists()

    def test_main_nonexistent_file(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.txt"

        with patch("sys.argv", ["parse-log", str(nonexistent)]):
            with pytest.raises(SystemExit) as exc_info:
                from fellowship_recorder.cli.parse_log import main

                main()

            assert exc_info.value.code == 1

    def test_main_invalid_run_number(self, sample_log: Path):
        with patch("sys.argv", ["parse-log", str(sample_log), "--run", "99"]):
            with pytest.raises(SystemExit) as exc_info:
                from fellowship_recorder.cli.parse_log import main

                main()

            assert exc_info.value.code == 1

    def test_main_regenerate_flag(self, temp_log_dir: Path, temp_output_dir: Path):
        log_file = temp_log_dir / "CombatLog_test.txt"
        log_file.write_text(
            '2025-11-24T08:00:00.000+08:00|DUNGEON_START|"Test"|1|31|[6,4]|0\n'
            '2025-11-24T08:10:00.000+08:00|DUNGEON_END|"Test"|1|31|[6,4]|1|600000|600.0|1|0\n'
        )

        with patch(
            "fellowship_recorder.cli.parse_log.FellowshipRecorderConfig.from_toml"
        ) as mock_config:
            mock_config.return_value.log_directory = temp_log_dir
            mock_config.return_value.output_directory = temp_output_dir

            with patch("sys.argv", ["parse-log", "--regenerate"]):
                with pytest.raises(SystemExit) as exc_info:
                    from fellowship_recorder.cli.parse_log import main

                    main()

                assert exc_info.value.code == 0

        json_files = list(temp_output_dir.glob("*.json"))
        assert len(json_files) == 1
