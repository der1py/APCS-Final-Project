"""
Reusable dataset and room-feasibility analysis utilities.

This module provides a pure-Python implementation of
`analyze_room_assignment_risk` that can be used inside the solver
pipeline or independently by the runner.
"""
from collections import defaultdict
from typing import Dict, List, Set, Optional


def check_forced_room_bottleneck(group_sections: Dict[str, List[object]],
                                  group_allowed_rooms: Dict[str, List[str]],
                                  num_blocks: int = 8) -> Optional[Dict]:
    """
    Check for rooms that are mathematically oversubscribed (forced-room bottleneck).
    
    A forced-room section is one where the group has exactly 1 allowed room.
    If the number of forced-room groups assigned to a room exceeds the number of
    available blocks, the room is oversubscribed and the model will be infeasible.
    
    Args:
        group_sections: dict mapping group_id -> list of Section-like objects
        group_allowed_rooms: dict mapping group_id -> list of allowed room names
        num_blocks: number of available timetable blocks (default: 8)
    
    Returns:
        A dict with violation details if any room is oversubscribed, else None.
        Format: {
            'room_name': str,
            'capacity': int,
            'demand': int,
            'shortfall': int,
            'affected_groups': list of group_ids,
            'affected_sections': list of section_ids
        }
        If multiple rooms are oversubscribed, returns the first one found.
    """
    
    # Group forced-room sections by their sole allowed room
    room_to_forced_groups = defaultdict(list)
    
    for gid, allowed_rooms in group_allowed_rooms.items():
        if len(allowed_rooms) == 1:
            room = allowed_rooms[0]
            room_to_forced_groups[room].append(gid)
    
    # Check for bottlenecks
    for room, forced_groups in room_to_forced_groups.items():
        demand = len(forced_groups)
        capacity = num_blocks
        
        if demand > capacity:
            affected_sections = []
            for gid in forced_groups:
                for section in group_sections.get(gid, []):
                    affected_sections.append(getattr(section, "id", "<unknown>"))
            
            return {
                'room_name': room,
                'capacity': capacity,
                'demand': demand,
                'shortfall': demand - capacity,
                'affected_groups': forced_groups,
                'affected_sections': affected_sections,
            }
    
    return None


def classify_groups_by_room_risk(group_allowed_rooms: Dict[str, List[str]]):
    """Classify group ids into categories based on number of allowed rooms.

    Returns a dict with keys: 'dead', 'very_risky', 'low_flex', 'ok'
    mapping to lists of group ids.
    """
    dead = []
    very_risky = []
    low_flex = []
    ok = []

    for gid, rooms in group_allowed_rooms.items():
        c = len(rooms)
        if c == 0:
            dead.append(gid)
        elif c == 1:
            very_risky.append(gid)
        elif c == 2:
            low_flex.append(gid)
        else:
            ok.append(gid)

    return {
        "dead": dead,
        "very_risky": very_risky,
        "low_flex": low_flex,
        "ok": ok,
    }


def compute_group_room_stats(group_sections: Dict[str, List[object]],
                             group_allowed_rooms: Dict[str, List[str]],
                             group_primary_rooms: Dict[str, Set[str]]):
    """Compute summary statistics about groups and rooms.

    Returns a dict with totals and counts used by the main report.
    """
    total = len(group_sections)
    cls = classify_groups_by_room_risk(group_allowed_rooms)
    dead_count = len(cls["dead"]) if total else 0
    risky_count = len(cls["very_risky"]) + len(cls["low_flex"]) if total else 0
    safe_count = len(cls["ok"]) if total else 0

    return {
        "total": total,
        "dead_count": dead_count,
        "risky_count": risky_count,
        "safe_count": safe_count,
        "by_category": cls,
    }


def analyze_room_assignment_risk(group_sections,
                                 group_allowed_rooms,
                                 group_primary_rooms):
    """
    Prints a risk analysis report for room assignment feasibility.

    This function is pure Python and has no dependencies on OR-Tools or
    solver variables. It only inspects the provided mappings and the
    Section-like objects contained in `group_sections`.

    Args:
        group_sections: dict mapping group_id -> list of Section-like objects
        group_allowed_rooms: dict mapping group_id -> list of allowed room names
        group_primary_rooms: dict mapping group_id -> set of primary room names
    """

    # Classify groups by risk
    classified = classify_groups_by_room_risk(group_allowed_rooms)

    dead_groups = classified["dead"]
    very_risky_groups = classified["very_risky"]
    low_flex_groups = classified["low_flex"]
    ok_groups = classified["ok"]

    # Print header
    print("\n" + "=" * 90)
    print("ROOM ASSIGNMENT RISK ANALYSIS")
    print("=" * 90 + "\n")

    # Helper function to print group details
    def print_group_details(gid, risk_label):
        allowed = group_allowed_rooms.get(gid, [])
        primary = group_primary_rooms.get(gid, set())
        sections = group_sections.get(gid, [])
        section_codes = [getattr(s, "course_code", None) for s in sections]

        print(f"  Group ID:              {gid}")
        print(f"  Risk Level:            {risk_label}")
        print(f"  Num Allowed Rooms:     {len(allowed)}")
        print(f"  Allowed Rooms:         {allowed if allowed else 'NONE'}")
        print(f"  Primary Rooms:         {sorted(primary) if primary else 'NONE'}")
        print(f"  Sections in Group:     {len(sections)}")
        print(f"  Courses:               {section_codes}")

    # Print DEAD groups (0 rooms)
    if dead_groups:
        print("🚨 INFEASIBLE / DEAD GROUPS (0 allowed rooms)")
        print("-" * 90)
        for gid in dead_groups:
            sections = group_sections.get(gid, [])
            print(f"Dead Group: {gid}")
            for s in sections:
                sid = getattr(s, "id", "<unknown>")
                code = getattr(s, "course_code", "<unknown>")
                print(f"  {sid} ({code})")
            print("  Diagnostic Hint: Likely caused by intersection of course room constraints.")
            print("                   (Primary and/or backup rooms don't overlap)")
            print()

    # Print VERY RISKY groups (1 room)
    if very_risky_groups:
        print("⚠️  VERY RISKY GROUPS (exactly 1 allowed room)")
        print("-" * 90)
        for gid in very_risky_groups:
            print_group_details(gid, "⚠️  VERY RISKY")
            print()

    # Print summary statistics
    print("\n" + "=" * 90)
    print("SUMMARY STATISTICS")
    print("=" * 90)

    stats = compute_group_room_stats(group_sections, group_allowed_rooms, group_primary_rooms)
    total = stats["total"]
    dead_count = stats["dead_count"]
    risky_count = stats["risky_count"]
    safe_count = stats["safe_count"]

    pct = (lambda n: (100 * n / total) if total else 0)

    print(f"  Total Groups:                 {total}")
    print(f"  🚨 Dead Groups (0 rooms):     {dead_count} ({pct(dead_count):.1f}%)")
    print(f"  ⚠️  Risky Groups (1-2 rooms): {risky_count} ({pct(risky_count):.1f}%)")
    print(f"  🟡 Safe Groups (3+ rooms):    {safe_count} ({pct(safe_count):.1f}%)")

    if dead_count > 0:
        print(f"\n  ⚠️  CRITICAL: {dead_count} dead group(s) → Model will be INFEASIBLE")
    elif risky_count > 0:
        print(f"\n  ⚠️  WARNING: {risky_count} risky group(s) → May cause infeasibility")
    else:
        print(f"\n  ✅ All groups have sufficient room flexibility")

    print("\n" + "=" * 90 + "\n")


__all__ = [
    "check_forced_room_bottleneck",
    "analyze_room_assignment_risk",
    "classify_groups_by_room_risk",
    "compute_group_room_stats",
]
