# CLI Tools Reference

Command-line utilities for processing Fellowship combat logs and generating metadata.

## parse-log

Parse combat logs and generate metadata for dungeon runs. This can be used to parse existing logs without video and to see what the format of the metadata `.json` would be.

### Usage

```bash
uv run parse-log LOG_FILE [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output JSON file (only if single run found) |
| `-l, --list` | List all dungeon runs found in the log |
| `-r, --run N` | Select specific run number (1-based index from --list) |
| `--json` | Output JSON to stdout instead of file |

### Examples

**Parse a log file:**
```bash
uv run parse-log ~/.local/share/Steam/steamapps/common/Fellowship/fellowship/Saved/CombatLogs/CombatLog251125_090352.txt
```

**List all runs in a log:**
```bash
uv run parse-log CombatLog251125_090352.txt --list
```

Output:
```
Found 3 dungeon run(s) in CombatLog251125_090352.txt:

1. Wyrmheart (Eternal 26) - ✓ Success
   Started: 2025-11-25T09:03:52Z
   Duration: 472.0s
   Bosses: 3
   Deaths: 2

2. Urrak Markets (Paragon 7) - ✗ Failed
   Started: 2025-11-25T09:15:20Z
   Duration: 180.0s
   Bosses: 1
   Deaths: 5
```

**Extract specific run:**
```bash
uv run parse-log CombatLog251125_090352.txt --run 1 --output wyrmheart.json
```

**Output to stdout:**
```bash
uv run parse-log CombatLog251125_090352.txt --run 2 --json | jq .
```

### Output Format

The generated JSON includes comprehensive metadata about the dungeon run:

```json
{
  "started_at": "2025-11-25T00:20:19.986Z",
  "ended_at": "2025-11-25T00:31:09.569Z",
  "duration": 649.583008,
  "result": true,
  "dungeon_id": 5,
  "dungeon_name": "The Heart of Tuzari",
  "difficulty_id": 34,
  "difficulty_name": "Eternal 2",
  "mode_id": "0",
  "mode_name": "Challenge",
  "affixes": [
    {
      "affix_id": 6,
      "affix_name": "Asha's Dilemma",
      "affix_type": "Ascension"
    },
    {
      "affix_id": 15,
      "affix_name": "Stone Skin",
      "affix_type": "Curse"
    }
  ],
  "party": [
    {
      "player_id": "Player-1234",
      "player_name": "Player1",
      "hero_id": 20,
      "hero_name": "Vigour",
      "is_recording_player": true,
      "item_level": 330.0
    },
    {
      "player_id": "Player-5678",
      "player_name": "Player2",
      "hero_id": 17,
      "hero_name": "Rime",
      "is_recording_player": false,
      "item_level": 325.7
    }
  ],
  "encounters": [
    {
      "boss_id": 10,
      "boss_name": "Moar'gore, Master of Sacrifice",
      "start_time_offset": 135.815,
      "end_time_offset": 257.409,
      "success": true
    },
    {
      "boss_id": 11,
      "boss_name": "Vun'Kahr, the Thorned Maw",
      "start_time_offset": 533.195,
      "end_time_offset": 648.254,
      "success": true
    }
  ],
  "deaths": [
    {
      "player_id": "Player-5678",
      "player_name": "Player2",
      "hero_id": 17,
      "hero_name": "Rime",
      "occurred_at": "2025-11-25T00:24:36.828Z",
      "time_offset": 256.842
    }
  ],
  "chapters": [
    {
      "title": "Moar'gore, Master of Sacrifice (Kill)",
      "time_offset": 135.815
    },
    {
      "title": "Death: Rime",
      "time_offset": 256.842
    },
    {
      "title": "Vun'Kahr, the Thorned Maw (Kill)",
      "time_offset": 533.195
    }
  ],
  "unique_hash": "d4dc3af2483704c9a8a4b5df6a1078e0"
}
```

---

## generate-description

Generate YouTube-style video descriptions from metadata.

### Usage

```bash
uv run generate-description VIDEO_FILE [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output file path (default: print to stdout) |

### Examples

**Generate description:**
```bash
uv run generate-description ~/Videos/20251125_002019_Heart_of_Tuzari_Eternal_2.mkv
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
uv run generate-description video.mkv --output description.txt
```

### Description Format

The generated description includes:

1. **Title** - Dungeon name and difficulty
2. **Chapters** - YouTube-compatible timestamps for:
   - Boss encounters with attempt numbers or "Kill"
   - Player deaths (using hero names when available)
3. **Party** - List of hero names in the group
4. **Affixes** - Active curse affixes (excludes Ascension affixes)
