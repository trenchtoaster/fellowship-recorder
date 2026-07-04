# Fellowship Game Data Reference

Reference tables for difficulty tiers, heroes, and affixes used by Fellowship Recorder.

## Difficulty Tiers

| Difficulty ID | Tier | Display |
|--------------|------|---------|
| 1-7 | Contender | Contender 1-7 |
| 9-15 | Adept | Adept 1-7 |
| 17-23 | Champion | Champion 1-7 |
| 25-31 | Paragon | Paragon 1-7 |
| 33+ | Eternal | Eternal 1+ |

**Note:** Gaps at difficulty IDs 8, 16, 24, 32.

**Mode:** Challenge (mode=0) shows tier names, Quick Play (mode=1) shows "Quick Play".

## Dungeons

### Adventures
Shorter instances (~10-15 minutes)

| Dungeon ID | Name | Target Time |
|------------|------|-------------|
| 6 | Empyrean Sands | 12:24 |
| 8 | Wyrmheart | 13:26 |
| 11 | Everdawn Grove | 11:48 |
| 12 | Stormwatch | 14:08 |
| 15 | Sailor's Abyss | 11:57 |
| 21 | Urrak Markets | 13:01 |
| 24 | Silken Hollow | 13:32 |
| 25 | Godfall Quarry | 12:18 |
| 29 | Ruins of Regath | 15:00 |
| 31 | Scryer's Peak | 13:27 |

**Note:** Ruins of Regath and Scryer's Peak were added in Season 3 (Rise of the Heskyr, June 2026).

### Capstone Dungeons
Multi-boss instances (~25-30 minutes)

| Dungeon ID | Name | Target Time |
|------------|------|-------------|
| 5 | The Heart of Tuzari | 24:45 |
| 7 | Cithrel's Fall | 27:51 |
| 13 | Wraithtide Vault | 29:42 |
| 23 | Ransack of Drakheim | 29:00 |

**Note:** Target times are for Challenge mode completion bonuses.

### Pinnacle Dungeons
Weekly high-end challenges added in Season 3, with Normal/Hard/Nightmare tiers

| Dungeon ID | Name | Target Time |
|------------|------|-------------|
| 30 | Xul, The Blood Monolith | 28:20 |

## Heroes

| Hero ID | Hero Name |
|---------|-----------|
| 2 | Elarion |
| 7 | Ardeos |
| 9 | Gunde |
| 10 | Tariq |
| 11 | Mara |
| 13 | Meiko |
| 14 | Sylvie |
| 17 | Rime |
| 20 | Vigour |
| 22 | Helena |
| 24 | Aeona |
| 25 | Xavian |

**Note:** Aeona (healer) and Xavian (tank) were added in Season 2 (February 2026); Gunde (melee DPS) in Season 3 (June 2026).

## Affixes

Affix IDs match the `DungeonModifiers` GUIDs in the game data.

### Ascension Affixes

| ID | Name | Description |
|----|------|-------------|
| 2 | Sahril's Madness | Enemies receive 30% increased Threat from Damage Dealers and Healers. |
| 3 | Elheryn's Exile | Enemy interruptable abilities and dispellable effects deal 20% more damage. |
| 4 | Vayr's Legacy | Enemies have learned new abilities. |
| 5 | Asha's Dilemma | Dungeons have a Time Limit. When expired, heroes gain bonus Spirit Generation but Dungeon Score is reduced. |
| 6 | Asha's Regret | Dungeons have a Time Limit. When expired, loot is reduced 1 upgrade level and Dungeon Score is reduced. |
| 23 | Pathfinder's Guidance | Defeating highlighted enemies reaches the required Kill Score and leads to the boss. Fighting marked enemies grants Haste. |

**Note:** ID 6 was previously mislabeled "Asha's Dilemma" here — the game data (Seasons 2 and 3) has 5 = Dilemma (Spirit penalty) and 6 = Regret (loot penalty).

### Curse Affixes

| ID | Name | Description |
|----|------|-------------|
| 8 | Blood Shards | Dying enemies erupt Blood Shards damaging heroes. Heroes hit gain Expertise stacks. |
| 9 | Carnage | All incoming damage applies a bleed. Heroes heal for 10% of damage dealt. Bonus healing increases per boss defeated. (Removed in Season 3) |
| 10 | Challenge | Non-boss enemies deal 10% more damage and have 10% more health. Heroes gain +10% Spirit. |
| 11 | Binding Ice | Periodically, a hero is cursed. After 5s it erupts, damaging and rooting all heroes and enemies in radius. |
| 12 | Empowered Minions | Several enemies are empowered with +100% Health and +150% Power. Defeating them grants +20% Haste and Movement Speed. |
| 13 | Malevolent Shade | Shades appear reducing enemy damage taken by 50%. Defeating them restores 30% Health and 15% Mana. |
| 14 | Meteor Rain | Meteors periodically crash down on heroes. Each meteor grants 2 Spirit. |
| 15 | Stone Skin | Non-boss enemies have 30% increased health. They explode on death, damaging nearby enemies. |
| 16 | Ultimatum | Bosses deal 5% more damage and have 10% more health. Hero ability cooldowns reduced by 10%. |
| 19 | Shadow Lord's Trial | Collect Shadow Orbs to summon Emissaries. Defeating them grants +20% damage, Haste, and Movement Speed. |
| 20 | Ghorn the Avalanche | Winter event: defeat Ghorn for his Boon and +20s on the Dungeon Timer. |
| 21 | Krumbug the Naughty | Winter event: defeat Krumbug for his Bag of Tricks and +60s on the Dungeon Timer. |
| 22 | Eira the White Witch | Winter event: defeat Eira for The White Witch's Boon and +90s on the Dungeon Timer. |
| 24 | Anomalous Orbs | Anomalous Orbs spawn near enemies and cast Detonate, dealing heavy damage if not interrupted. |
| 25 | Storm Shield | Players periodically charge with lightning; a massive bolt strikes all players after 8s. Storm Shield halves damage taken while charged. |
| 27 | Truesight | Every 30% Kill Score an enemy drops a Truesight Orb, revealing the next Heskyr-marked enemy. Killing it grants +20% damage and healing. (Added in Season 3) |

### Implicit Affixes

| ID | Name | Description |
|----|------|-------------|
| 18 | Promoted Enemies | Some mobs and bosses have +1 difficulty stats until the dungeon timer runs out. |
