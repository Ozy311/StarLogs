# Event Types Reference

This document provides a comprehensive reference for all event types supported by the StarLogs parser, including damage type classifications, NPC detection patterns, and frontend mappings.

## Table of Contents

- [Event Types Overview](#event-types-overview)
- [Damage Type Classifications](#damage-type-classifications)
- [NPC Detection Patterns](#npc-detection-patterns)
- [Frontend Event Type Mapping](#frontend-event-type-mapping)
- [Corpse Event Consolidation](#corpse-event-consolidation)

---

## Event Types Overview

The parser recognizes the following event types (defined in `event_parser.py`):

| EventType Enum | String Value | Description |
|----------------|--------------|-------------|
| `DISCONNECT` | `disconnect` | Client disconnected from server |
| `KILL` | `kill` | Generic kill event (NPC-on-NPC, fallback) |
| `DEATH` | `death` | Player was killed (by NPC or vehicle destruction) |
| `PVE_KILL` | `pve_kill` | Player killed NPC (vehicle combat) |
| `PVP_KILL` | `pvp_kill` | Player killed player (vehicle combat) |
| `FPS_PVE_KILL` | `fps_pve_kill` | Player killed NPC (on foot) |
| `FPS_PVP_KILL` | `fps_pvp_kill` | Player killed player (on foot) |
| `FPS_DEATH` | `fps_death` | Player was killed (on foot) |
| `SUICIDE` | `suicide` | Player killed themselves |
| `ACTOR_STALL` | `actor_stall` | Game disconnect/crash/stall |
| `VEHICLE_DESTROY_SOFT` | `vehicle_destroy_soft` | Vehicle disabled/crippled (level 0→1) |
| `VEHICLE_DESTROY_FULL` | `vehicle_destroy_full` | Vehicle fully destroyed (→2) |
| `CORPSE` | `corpse` | Player corpse state (death confirmation) |
| `UNKNOWN` | `unknown` | Unrecognized event type |

---

## Damage Type Classifications

The parser uses damage types from game logs to classify kill events. Here's how each damage type is handled:

### Bullet Damage Type

**Damage Type:** `Bullet`

**Classification:** FPS combat (on foot)

**Event Types:**
- `FPS_PVE_KILL` - Player killed NPC on foot
- `FPS_PVP_KILL` - Player killed player on foot
- `FPS_DEATH` - Player was killed by NPC on foot

**Example Log:**
```
<Actor Death> CActor::Kill: 'PlayerVictim' [123] in zone 'Area51' killed by 'PlayerKiller' [456] using 'Weapon_Ballistic_01' [Class Bullet] with damage type 'Bullet' from direction x: 1.0, y: 0.0, z: 0.0
```

### VehicleDestruction Damage Type

**Damage Type:** `VehicleDestruction`

**Classification:** Player died in their vehicle (not traditional vehicle combat)

**Event Types:**
- `DEATH` - Player victim died in their vehicle
- `PVE_KILL` - NPC victim died, player gets credit

**Example Log:**
```
<Actor Death> CActor::Kill: 'Chrissyy' [123] in zone 'Crusader_789' killed by 'Djjus' [456] using 'Unknown' [Class unknown] with damage type 'VehicleDestruction' from direction x: 1.0, y: 0.0, z: 0.0
```

**Notes:**
- VehicleDestruction indicates the player died while inside a vehicle
- Different from normal vehicle combat kills
- Commonly occurs when ship is destroyed and player dies from the explosion

### Other Damage Types

**Vehicle Combat:**
- Energy weapons (e.g., `Energy`, `Laser`)
- Ballistic weapons (e.g., `Ballistic`)
- Missiles (e.g., `Missile`, `Torpedo`)
- Collision (e.g., `Collision`)

**Classification:** Vehicle combat

**Event Types:**
- `PVE_KILL` - Player killed NPC (vehicle)
- `PVP_KILL` - Player killed player (vehicle)
- `DEATH` - Player killed by NPC (vehicle)

---

## NPC Detection Patterns

The parser uses multiple strategies to detect NPCs vs. players.

### Explicit NPC Indicators

The following patterns in entity names indicate an NPC:

```python
NPC_INDICATORS = [
    'PU_Pilots',          # Standard pilot NPCs
    'PU_',                # PersistentUniverse prefix
    'AI_CRIM',            # AI criminals
    'AI_',                # Generic AI prefix
    '_NPC_',              # NPC marker
    'Criminal-Pilot',     # Criminal NPCs
    'Security-',          # Security NPCs
    'Pirate-',            # Pirate NPCs
    '-Pilot_Light_',      # Light fighter pilots
    '-Pilot_Medium_',     # Medium fighter pilots
    '-Pilot_Heavy_',      # Heavy fighter pilots
    'NPC_Archetypes',     # Archetype NPCs (new in Game Build 10480022)
    'Kopion_'             # Combat pets (new in Game Build 10480022)
]
```

### New NPC Patterns (Added)

**NPC_Archetypes Pattern:**
- Matches: `NPC_Archetypes-Male-Human-FrontierFighters_soldier_6897206313090`
- Matches: `NPC_Archetypes-Male-Human-FrontierFighters_juggernaut_6897206313089`
- Matches: `NPC_Archetypes-Male-Human-FrontierFighters_techie_6893714486630`

**Kopion_ Pattern:**
- Matches: `Kopion_CombatPet_FrontierFighters_6893714486786`

### Fallback Heuristics

If no explicit indicator matches, the parser uses fallback heuristics:

1. **Long Name Check:** Names longer than 40 characters are assumed to be NPCs
   - Player names are typically 3-20 characters
   - NPC names are often much longer with IDs

2. **Hyphen Pattern Check:** Names with 3 or more hyphens are assumed to be NPCs
   - Example: `NPC_Archetypes-Male-Human-FrontierFighters_...`
   - Player names rarely have multiple hyphens

**Code Reference:** `event_parser.py:186-207`

---

## Frontend Event Type Mapping

This table shows how parser EventTypes map to frontend display handlers in `app.js`.

| EventType (Parser) | Frontend Handler | Filter Property | Badge Class | Badge Label | Counter |
|-------------------|------------------|-----------------|-------------|-------------|---------|
| `disconnect` | Line 1097-1101 | `filters.disconnects` | `dc` | "Disconnect" | None |
| `kill` | No handler | None | None | N/A | None |
| `death` | Line 1057-1063 | `filters.deaths` | `death` | "Death" | None |
| `pve_kill` | Line 1025-1032 | `filters.pve` | `pve` | "Ship PvE" | None |
| `pvp_kill` | Line 1033-1040 | `filters.pvp` | `pvp` | "Ship PvP" | None |
| `fps_pve_kill` | Line 1041-1048 | `filters.fps_pve` | `fps-pve` | "FPS PvE" | None |
| `fps_pvp_kill` | Line 1049-1056 | `filters.fps_pvp` | `fps-pvp` | "FPS PvP" | None |
| `fps_death` | Line 1064-1070 | `filters.fps_death` | `fps-death` | "FPS Death" | None |
| `suicide` | Line 1114-1124 | `filters.suicide` | `suicide` | "Suicide" | `counters.suicide` |
| `actor_stall` | Line 1102-1113 | `filters.disconnects` | `stall` | "Actor Stall" | `counters.stalls` |
| `vehicle_destroy_soft` | Line 1071-1083 | `filters.vehicle_soft` | `vehicle-soft` | "Soft Death" | None |
| `vehicle_destroy_full` | Line 1084-1096 | `filters.vehicle_full` | `vehicle-full` | "Destroyed" | None |
| `corpse` | Line 1125-1144 | `filters.corpse` | `corpse` | "Corpse 💀" | `counters.corpse` |
| `unknown` | No handler | None | None | N/A | None |

**Notes:**
- The `kill` EventType is a generic fallback for NPC-on-NPC combat and is not displayed in the frontend
- `disconnect` and `actor_stall` both map to `filters.disconnects`
- All event types have corresponding filter properties except `kill` and `unknown`

**Code References:**
- Event handlers: `app.js:1025-1144`
- Filter application: `app.js:1335-1352`

---

## Corpse Event Consolidation

### Overview

Corpse events in game logs often come in groups of 3 consecutive entries for the same player. The parser consolidates these into a single rich event.

### Example Log Entries

```
<[ActorState] Corpse> Player 'EzrianaAnmut': DoesLocationContainHospital: Searching...
<[ActorState] Corpse> Player 'EzrianaAnmut': Hospital found within landing zone
<[ActorState] Corpse> Player 'EzrianaAnmut': IsCorpseEnabled: No
```

### Consolidation Behavior

**Before consolidation:** 3 separate events

**After consolidation:** 1 event with:
- `player`: Player name
- `status`: First status message (for backwards compatibility)
- `status_messages`: Array of all status messages
- `message_count`: Number of messages (typically 3)

### Implementation Details

**Parser Side (`event_parser.py`):**
1. Corpse events are buffered in `self.corpse_buffer` (dict by player name)
2. Each corpse log line adds to the buffer for that player
3. When 3 messages are collected, a consolidated event is emitted
4. `flush_corpse_buffers()` method emits any incomplete buffers at end of parsing

**Frontend Side (`app.js`):**
1. Displays player name and "became a corpse" summary
2. Shows all status messages joined with " • " separator if multiple exist
3. Falls back to single `status` field for backwards compatibility

**Code References:**
- Parser buffer: `event_parser.py:108`
- Parser consolidation: `event_parser.py:132-156`
- Emit method: `event_parser.py:219-251`
- Flush method: `event_parser.py:253-266`
- Frontend display: `app.js:1125-1144`

### Testing

Run the test suite to verify consolidation:

```bash
python3 test_parser_fixes.py
```

The test creates 3 sequential corpse events and verifies they consolidate into 1 event with all messages captured.

---

## Version History

### Version 1.0 (2025-11-08)

**Initial documentation with comprehensive fixes:**

1. **VehicleDestruction Classification** - Added special handling for VehicleDestruction damage type
   - Player victims → `DEATH` event
   - NPC victims → `PVE_KILL` event

2. **NPC Detection Enhancement** - Added missing NPC patterns
   - `NPC_Archetypes` pattern for archetype NPCs
   - `Kopion_` pattern for combat pets
   - Fallback heuristics (>40 char names, ≥3 hyphens)

3. **Corpse Event Consolidation** - Implemented buffering and consolidation
   - Groups 3 sequential corpse events into 1 rich event
   - Preserves all status messages
   - Frontend displays consolidated details

4. **Frontend Mapping Audit** - Verified all EventType mappings
   - All event types have correct handlers
   - All filters properly mapped
   - Badges and counters working correctly

---

## Contributing

When adding new event types or modifying existing ones:

1. Update `EventType` enum in `event_parser.py`
2. Add parsing logic in appropriate method
3. Add frontend handler in `app.js` (lines ~1025-1144)
4. Add filter mapping in `applyFilterToEvent()` (lines ~1335-1352)
5. Update this reference document
6. Add test cases to `test_parser_fixes.py`

---

## See Also

- `event_parser.py` - Parser implementation
- `app.js` - Frontend event display
- `test_parser_fixes.py` - Test suite for parser fixes
