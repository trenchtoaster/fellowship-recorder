# CLI Tools Reference

Command-line utilities for processing Fellowship combat logs and generating metadata.

## parse-log

Parse combat logs and generate metadata for dungeon runs. This can be used to parse existing logs without video and to see what the format of the metadata `.json` would be.

### Usage

```bash
parse-log LOG_FILE [OPTIONS]
```

`LOG_FILE` can be either:
- An absolute or relative path to a combat log file
- Just the filename (e.g., `CombatLog251125_090352.txt`) - will automatically check the `log_directory` from `config.toml`

### Options

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output JSON file (only if single run found) |
| `-l, --list` | List all dungeon runs found in the log |
| `-r, --run N` | Select specific run number (1-based index from --list) |
| `--json` | Output JSON to stdout instead of file |
| `--regenerate` | Regenerate all metadata JSONs from combat logs |

### Examples

**Parse a log file (with full path):**
```bash
parse-log ~/.local/share/Steam/steamapps/common/Fellowship/fellowship/Saved/CombatLogs/CombatLog251125_090352.txt
```

**Parse a log file (using filename only - reads from config.toml log_directory):**
```bash
parse-log CombatLog251125_090352.txt
```

**List all runs in a log:**
```bash
parse-log CombatLog251125_090352.txt --list
```

Output:
```
Found 2 dungeon run(s) in CombatLog251125_090352.txt:

1. Wyrmheart (Eternal 26) - Success
   Started: 2025-11-25T09:03:52.000Z
   Ended: 2025-11-25T09:11:44.000Z
   Duration: 472.0s
   Remaining Time: +334.0s
   Kill Score: 100.0%
   Affixes: Asha's Dilemma, Vayr's Legacy, Stone Skin, Carnage
   Bosses: 3
   Deaths: 2

2. Silken Hollow (Eternal 6) - Success
   Started: 2025-11-25T09:28:15.000Z
   Ended: 2025-11-25T09:39:26.000Z
   Duration: 671.0s
   Remaining Time: +141.0s
   Kill Score: 101.2%
   Affixes: Asha's Dilemma, Vayr's Legacy, Stone Skin, Empowered Minions
   Bosses: 1
   Deaths: 5
```

**Extract specific run:**
```bash
parse-log CombatLog251125_090352.txt --run 1 --output wyrmheart.json
```

**Output to stdout:**
```bash
parse-log CombatLog251125_090352.txt --run 2 --json | jq .
```

**Regenerate all metadata from logs:**
```bash
parse-log --regenerate
```

This parses all combat logs in the configured `log_directory` and generates JSON metadata files in `output_directory`. Useful for refreshing metadata after parser updates.

### Output Format

The generated JSON includes comprehensive metadata about the dungeon run:

```json
{
  "started_at": "2025-11-25T02:28:03.334Z",
  "ended_at": "2025-11-25T02:39:14.614Z",
  "duration": 671.280,
  "target_time": 812.0,
  "remaining_time": 140.720,
  "completed": true,
  "success": true,
  "dungeon_id": 24,
  "dungeon_name": "Silken Hollow",
  "difficulty_id": 38,
  "difficulty_name": "Eternal 6",
  "mode_id": "0",
  "mode_name": "Challenge",
  "affixes": [
    {
      "affix_id": 6,
      "affix_name": "Asha's Dilemma",
      "affix_type": "Ascension"
    },
    {
      "affix_id": 4,
      "affix_name": "Vayr's Legacy",
      "affix_type": "Ascension"
    },
    {
      "affix_id": 15,
      "affix_name": "Stone Skin",
      "affix_type": "Curse"
    },
    {
      "affix_id": 12,
      "affix_name": "Empowered Minions",
      "affix_type": "Curse"
    }
  ],
  "party": [
    {
      "player_id": "Player-1234567890",
      "player_name": "PlayerOne",
      "hero_id": 20,
      "hero_name": "Vigour",
      "is_recording_player": true,
      "item_level": 330.0
    },
    {
      "player_id": "Player-2345678901",
      "player_name": "PlayerTwo",
      "hero_id": 2,
      "hero_name": "Elarion",
      "is_recording_player": false,
      "item_level": 271.1
    },
    {
      "player_id": "Player-3456789012",
      "player_name": "PlayerThree",
      "hero_id": 17,
      "hero_name": "Rime",
      "is_recording_player": false,
      "item_level": 277.5
    },
    {
      "player_id": "Player-4567890123",
      "player_name": "PlayerFour",
      "hero_id": 13,
      "hero_name": "Meiko",
      "is_recording_player": false,
      "item_level": 323.6
    }
  ],
  "kill_objective": {
    "completed_at": "2025-11-25T02:36:11.008Z",
    "completion_offset": 487.674,
    "final_score": 101.18
  },
  "encounters": [
    {
      "boss_id": 33,
      "boss_name": "Vexira, Mother of Nightmares",
      "start_time_offset": 497.658,
      "end_time_offset": 671.259,
      "success": true
    }
  ],
  "deaths": [
    {
      "player_id": "Player-3456789012",
      "player_name": "PlayerThree",
      "hero_id": 17,
      "hero_name": "Rime",
      "occurred_at": "2025-11-25T02:31:47.966Z",
      "time_offset": 224.632
    },
    {
      "player_id": "Player-1234567890",
      "player_name": "PlayerOne",
      "hero_id": 20,
      "hero_name": "Vigour",
      "occurred_at": "2025-11-25T02:31:51.406Z",
      "time_offset": 228.072
    }
  ],
  "chapters": [
    {
      "title": "Death: Rime",
      "time_offset": 219.632
    },
    {
      "title": "Death: Vigour",
      "time_offset": 223.072
    },
    {
      "title": "Vexira, Mother of Nightmares (Kill)",
      "time_offset": 492.658
    }
  ],
  "unique_hash": "176c52baf9bd884d0403e29dace2cfe9"
}
```

---

## generate-description

Generate YouTube-style video descriptions from metadata.

### Usage

```bash
generate-description VIDEO_FILE [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output file path (default: print to stdout) |

### Examples

**Generate description:**
```bash
generate-description ~/Videos/20251125_002019_Heart_of_Tuzari_Eternal_2.mkv
```

Output:
```
The Heart of Tuzari - Eternal 2

Chapters:
0:00 Start
2:15 Moar'gore, Master of Sacrifice (Kill)
4:16 Death: Meiko
8:53 Vun'Kahr, the Thorned Maw (Kill)
12:45 Prophet Ez'rath (Kill)

Party: Vigour, Rime, Meiko, Elarion

Affixes: Stone Skin
```

**Save to file:**
```bash
generate-description video.mkv --output description.txt
```

### Description Format

The generated description includes:

1. **Title** - Dungeon name and difficulty
2. **Chapters** - YouTube-compatible timestamps for:
   - Boss encounters with attempt numbers or "Kill"
   - Player deaths (using hero names when available)
3. **Party** - List of hero names in the group
4. **Affixes** - Active curse affixes (excludes Ascension affixes)
