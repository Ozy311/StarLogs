#!/usr/bin/env python3
"""
Test script for parser fixes:
1. VehicleDestruction damage type classification
2. NPC detection (NPC_Archetypes, Kopion_)
3. Corpse event consolidation
"""

import sys
from event_parser import EventParser, EventType

def test_vehicle_destruction():
    """Test VehicleDestruction damage type classification"""
    print("\n=== Testing VehicleDestruction Classification ===")
    parser = EventParser()

    # Test case 1: Player killed by VehicleDestruction (should be DEATH)
    test_line = "<2025-10-25T12:00:00.000Z> <Actor Death> CActor::Kill: 'Chrissyy' [123456] in zone 'Crusader_789' killed by 'Djjus' [789012] using 'Unknown' [Class unknown] with damage type 'VehicleDestruction' from direction x: 1.0, y: 0.0, z: 0.0"

    event = parser.parse_line(test_line)
    if event:
        print(f"✓ Event Type: {event.type.value}")
        print(f"  Victim: {event.details['victim']}")
        print(f"  Killer: {event.details['killer']}")
        print(f"  Damage Type: {event.details['damage_type']}")

        if event.type == EventType.DEATH:
            print("✓ PASS: VehicleDestruction correctly classified as DEATH")
        else:
            print(f"✗ FAIL: Expected DEATH, got {event.type.value}")
            return False
    else:
        print("✗ FAIL: No event parsed")
        return False

    # Test case 2: NPC killed by VehicleDestruction (should be PVE_KILL)
    test_line2 = "<2025-10-25T12:00:00.000Z> <Actor Death> CActor::Kill: 'PU_Pirate_123' [123456] in zone 'Crusader_789' killed by 'PlayerName' [789012] using 'Unknown' [Class unknown] with damage type 'VehicleDestruction' from direction x: 1.0, y: 0.0, z: 0.0"

    event2 = parser.parse_line(test_line2)
    if event2:
        print(f"\n✓ Event Type: {event2.type.value}")
        print(f"  Victim: {event2.details['victim']}")
        print(f"  Killer: {event2.details['killer']}")

        if event2.type == EventType.PVE_KILL:
            print("✓ PASS: NPC VehicleDestruction correctly classified as PVE_KILL")
        else:
            print(f"✗ FAIL: Expected PVE_KILL, got {event2.type.value}")
            return False
    else:
        print("✗ FAIL: No event parsed")
        return False

    return True


def test_npc_detection():
    """Test NPC detection for new patterns"""
    print("\n=== Testing NPC Detection ===")
    parser = EventParser()

    # Test NPC_Archetypes pattern
    npc_names = [
        'NPC_Archetypes-Male-Human-FrontierFighters_soldier_6897206313090',
        'NPC_Archetypes-Male-Human-FrontierFighters_juggernaut_6897206313089',
        'Kopion_CombatPet_FrontierFighters_6893714486786',
    ]

    for npc_name in npc_names:
        is_npc = parser._is_npc(npc_name)
        if is_npc:
            print(f"✓ PASS: '{npc_name[:50]}...' detected as NPC")
        else:
            print(f"✗ FAIL: '{npc_name[:50]}...' NOT detected as NPC")
            return False

    # Test FPS kill against NPC_Archetypes (should be FPS_PVE_KILL)
    test_line = "<2025-10-25T12:00:00.000Z> <Actor Death> CActor::Kill: 'NPC_Archetypes-Male-Human-FrontierFighters_soldier_6897206313090' [123456] in zone 'Crusader_789' killed by 'PlayerName' [789012] using 'Unknown' [Class Bullet] with damage type 'Bullet' from direction x: 1.0, y: 0.0, z: 0.0"

    event = parser.parse_line(test_line)
    if event:
        print(f"\n✓ Event Type: {event.type.value}")
        print(f"  Victim: {event.details['victim'][:50]}...")
        print(f"  Killer: {event.details['killer']}")

        if event.type == EventType.FPS_PVE_KILL:
            print("✓ PASS: NPC_Archetypes FPS kill correctly classified as FPS_PVE_KILL")
        else:
            print(f"✗ FAIL: Expected FPS_PVE_KILL, got {event.type.value}")
            return False
    else:
        print("✗ FAIL: No event parsed")
        return False

    # Test fallback heuristics
    print("\n--- Testing Fallback Heuristics ---")

    # Very long name (>40 chars)
    long_name = "A" * 45
    if parser._is_npc(long_name):
        print(f"✓ PASS: Long name (>40 chars) detected as NPC")
    else:
        print(f"✗ FAIL: Long name NOT detected as NPC")
        return False

    # Hyphen-heavy pattern (>=3 hyphens)
    hyphen_name = "Foo-Bar-Baz-Qux_123"
    if parser._is_npc(hyphen_name):
        print(f"✓ PASS: Hyphen-heavy name detected as NPC")
    else:
        print(f"✗ FAIL: Hyphen-heavy name NOT detected as NPC")
        return False

    # Normal player name should NOT be detected
    player_name = "PlayerName123"
    if not parser._is_npc(player_name):
        print(f"✓ PASS: Normal player name NOT detected as NPC")
    else:
        print(f"✗ FAIL: Normal player name incorrectly detected as NPC")
        return False

    return True


def test_corpse_consolidation():
    """Test corpse event consolidation"""
    print("\n=== Testing Corpse Event Consolidation ===")
    parser = EventParser()

    # Simulate three consecutive corpse events
    corpse_lines = [
        "<2025-10-25T12:00:00.000Z> <[ActorState] Corpse> Player 'EzrianaAnmut' <remote client>: DoesLocationContainHospital: Searching... [Team_",
        "<2025-10-25T12:00:00.100Z> <[ActorState] Corpse> Player 'EzrianaAnmut' <remote client>: Hospital found within landing zone [Team_",
        "<2025-10-25T12:00:00.200Z> <[ActorState] Corpse> Player 'EzrianaAnmut' <remote client>: IsCorpseEnabled: No [Team_",
    ]

    events = []
    for line in corpse_lines:
        event = parser.parse_line(line)
        if event:
            events.append(event)

    print(f"Number of events emitted: {len(events)}")

    if len(events) == 1:
        print("✓ PASS: Three corpse lines consolidated into 1 event")
        event = events[0]
        print(f"  Player: {event.details['player']}")
        print(f"  Status Messages: {len(event.details['status_messages'])}")

        if len(event.details['status_messages']) == 3:
            print("✓ PASS: All 3 status messages captured")
            for i, msg in enumerate(event.details['status_messages'], 1):
                print(f"    {i}. {msg}")
        else:
            print(f"✗ FAIL: Expected 3 status messages, got {len(event.details['status_messages'])}")
            return False
    else:
        print(f"✗ FAIL: Expected 1 consolidated event, got {len(events)}")
        return False

    # Test flushing buffer for incomplete corpse events
    print("\n--- Testing Buffer Flush ---")
    parser2 = EventParser()

    # Add only 2 corpse events (incomplete)
    for line in corpse_lines[:2]:
        event = parser2.parse_line(line)
        if event:
            print(f"✗ FAIL: Event emitted before 3 messages collected")
            return False

    # Flush buffer
    flushed_events = parser2.flush_corpse_buffers()
    if len(flushed_events) == 1:
        print(f"✓ PASS: Incomplete corpse event flushed (2 messages)")
        print(f"  Status Messages: {len(flushed_events[0].details['status_messages'])}")
    else:
        print(f"✗ FAIL: Expected 1 flushed event, got {len(flushed_events)}")
        return False

    return True


def test_suicide_event():
    """Test suicide event to ensure variables are defined correctly"""
    print("\n=== Testing Suicide Event (Variable Scope Fix) ===")
    parser = EventParser()

    # Test suicide event - this previously failed due to undefined variables
    test_line = "<2025-10-25T12:00:00.000Z> <Actor Death> CActor::Kill: 'PlayerName' [123456] in zone 'Crusader_789' killed by 'PlayerName' [123456] using 'Unknown' [Class unknown] with damage type 'Collision' from direction x: 0.0, y: 0.0, z: 0.0"

    event = parser.parse_line(test_line)
    if event:
        print(f"✓ Event Type: {event.type.value}")
        print(f"  Victim: {event.details['victim']}")
        print(f"  Killer: {event.details['killer']}")

        if event.type == EventType.SUICIDE:
            print("✓ PASS: Suicide correctly classified")
        else:
            print(f"✗ FAIL: Expected SUICIDE, got {event.type.value}")
            return False

        # Verify that is_pvp, is_pve, is_death, is_fps are present (they use the previously undefined variables)
        if 'is_pvp' in event.details and 'is_pve' in event.details and 'is_death' in event.details and 'is_fps' in event.details:
            print("✓ PASS: All detail flags present (is_pvp, is_pve, is_death, is_fps)")
        else:
            print("✗ FAIL: Missing detail flags")
            return False
    else:
        print("✗ FAIL: No event parsed")
        return False

    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Parser Fixes Test Suite")
    print("=" * 60)

    results = {
        'VehicleDestruction Classification': test_vehicle_destruction(),
        'NPC Detection': test_npc_detection(),
        'Corpse Consolidation': test_corpse_consolidation(),
        'Suicide Event (Variable Scope)': test_suicide_event(),
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
