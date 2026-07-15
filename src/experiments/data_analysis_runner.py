"""Standalone runner for dataset room-feasibility analysis.

Loads the cleaned course JSON and reconstructs simple group structures
so analysis can run without invoking the CP-SAT solver.
"""
import json
import sys
import io
import contextlib
from pathlib import Path

# Ensure the top-level `src` directory is on sys.path so imports like
# `models.section` and `analysis.data_analysis` resolve when the runner is
# executed as a script.
_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.section import Section
from analysis.data_analysis import analyze_room_assignment_risk, check_forced_room_bottleneck
from data.data_loader import load_simultaneous_blocking_rules


def load_course_stats(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_groups_from_course_stats(courses):
    """Constructs group_sections, group_allowed_rooms, group_primary_rooms
    using the same simultaneous blocking group logic as the solver.
    """
    if isinstance(courses, dict):
        course_items = courses.items()
    else:
        course_items = ((c.get("code"), c) for c in courses)

    course_lookup = {}
    sections = []
    course_to_sections = {}

    for code, data in course_items:
        if not isinstance(data, dict):
            continue

        code = code or data.get("code")
        if not code:
            continue

        num_sections = int(data.get("num_sections", data.get("section_count", 0)) or 0)
        course_lookup[code] = data
        sections_for_course = []

        for i in range(1, num_sections + 1):
            sec_id = f"{code}_{i}"
            sec = Section(id=sec_id, course_code=code, time_slot=-1)
            sections.append(sec)
            sections_for_course.append(sec)

        if sections_for_course:
            course_to_sections[code] = sections_for_course

    blocking_rules = load_simultaneous_blocking_rules()

    sim_groups = {}
    section_to_group = {}
    group_counter = 0

    for c1, c2 in blocking_rules.get("Simultaneous", []):
        if c1 not in course_to_sections or c2 not in course_to_sections:
            continue

        sec_list_1 = course_to_sections[c1]
        sec_list_2 = course_to_sections[c2]
        min_len = min(len(sec_list_1), len(sec_list_2))

        for i in range(min_len):
            s1 = sec_list_1[i]
            s2 = sec_list_2[i]

            g1 = section_to_group.get(s1.id)
            g2 = section_to_group.get(s2.id)

            if g1 is None and g2 is None:
                gid = f"sim_{group_counter}"
                group_counter += 1
                sim_groups[gid] = {s1.id, s2.id}
                section_to_group[s1.id] = gid
                section_to_group[s2.id] = gid
            elif g1 is not None and g2 is None:
                sim_groups[g1].add(s2.id)
                section_to_group[s2.id] = g1
            elif g1 is None and g2 is not None:
                sim_groups[g2].add(s1.id)
                section_to_group[s1.id] = g2
            elif g1 != g2:
                for sid in sim_groups[g2]:
                    sim_groups[g1].add(sid)
                    section_to_group[sid] = g1
                del sim_groups[g2]

    for sec in sections:
        if sec.id not in section_to_group:
            gid = f"sim_{group_counter}"
            group_counter += 1
            sim_groups[gid] = {sec.id}
            section_to_group[sec.id] = gid

    section_by_id = {s.id: s for s in sections}

    group_sections = {
        gid: [section_by_id[sid] for sid in sids]
        for gid, sids in sim_groups.items()
    }

    group_allowed_rooms = {}
    group_primary_rooms = {}

    for gid, s_list in group_sections.items():
        first_course = course_lookup[s_list[0].course_code]
        allowed = set(first_course.get("rooms", [])) | set(first_course.get("backUpRooms", []))
        primary = set(first_course.get("rooms", []))

        for s in s_list[1:]:
            c = course_lookup[s.course_code]
            allowed &= set(c.get("rooms", [])) | set(c.get("backUpRooms", []))
            primary &= set(c.get("rooms", []))

        group_allowed_rooms[gid] = sorted(allowed)
        group_primary_rooms[gid] = primary

    return group_sections, group_allowed_rooms, group_primary_rooms


def main():
    # src directory containing packages like `models` and `analysis`
    src_dir = Path(__file__).resolve().parent.parent
    course_path = src_dir / "data" / "cleaned data" / "clean_courses_stats.json"

    if not course_path.exists():
        print("clean_courses_stats.json not found at:", course_path)
        return

    courses = load_course_stats(course_path)

    group_sections, group_allowed_rooms, group_primary_rooms = build_groups_from_course_stats(courses)

    # Capture printed output
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        # Run forced-room bottleneck check first (hard constraint)
        bottleneck_violation = check_forced_room_bottleneck(group_sections, group_allowed_rooms, num_blocks=8)
        if bottleneck_violation:
            print("\n" + "=" * 90)
            print("ERROR: FORCED_ROOM_BOTTLENECK")
            print("=" * 90)
            print(f"\nRoom: {bottleneck_violation['room_name']}")
            print(f"Capacity: {bottleneck_violation['capacity']}")
            print(f"Demand: {bottleneck_violation['demand']}")
            print(f"Shortfall: {bottleneck_violation['shortfall']}")
            print(f"\nAffected Groups:")
            for gid in bottleneck_violation['affected_groups']:
                print(f"  {gid}")
            print(f"\nAffected Sections:")
            for sid in bottleneck_violation['affected_sections']:
                print(f"  {sid}")
            print("\n" + "=" * 90 + "\n")
        
        # Run room assignment risk analysis
        analyze_room_assignment_risk(
            group_sections,
            group_allowed_rooms,
            group_primary_rooms,
        )

    output = buf.getvalue()

    out_file = src_dir / "analysis" / "analysis_output.txt"
    with out_file.open("w", encoding="utf-8") as f:
        f.write(output)

    print(output)
    print("Analysis complete. Output written to analysis_output.txt")

if __name__ == "__main__":
    main()
