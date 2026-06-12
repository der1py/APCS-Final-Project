"""Export simultaneous/enrollment groups from a saved master timetable pickle.

This is a diagnostic-only runner. It does not rebuild or modify the master
timetable; it loads the saved pickle, derives current student enrollments using
the existing student assignment phase, and writes a compact CSV for inspecting
group block/room sharing.
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from data.data_loader import load_simultaneous_blocking_rules
from export_timetable_runner import (
    load_master_timetable,
    load_validated_data,
    validate_master_timetable,
)
from solver.student_timetable_cpsat import build_student_timetables


SRC_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SRC_DIR / "output"
PICKLE_PATH = OUTPUT_DIR / "master_timetable.pkl"
OUTPUT_PATH = OUTPUT_DIR / "view_groups.csv"
NO_ROOM_FOUND = "NO ROOM FOUND"


def build_simultaneous_groups(master_timetable):
    """Build sim_* groups with the same rule pairing used by the solver."""

    sim_groups = {}
    section_to_group = {}
    group_counter = 0
    blocking_rules = load_simultaneous_blocking_rules()
    course_to_sections = master_timetable.course_to_sections

    for c1, c2 in blocking_rules.get("Simultaneous", []):
        if c1 not in course_to_sections:
            continue

        if c2 not in course_to_sections:
            continue

        sec_list_1 = course_to_sections[c1]
        sec_list_2 = course_to_sections[c2]

        for i in range(min(len(sec_list_1), len(sec_list_2))):
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

    for section in master_timetable.sections:
        if section.id in section_to_group:
            continue

        gid = f"sim_{group_counter}"
        group_counter += 1
        sim_groups[gid] = {section.id}
        section_to_group[section.id] = gid

    group_sections = {
        gid: [
            master_timetable.section_by_id[section_id]
            for section_id in sorted(section_ids)
        ]
        for gid, section_ids in sim_groups.items()
    }

    return group_sections


def get_section_primary_block(master_timetable, section):
    if section.id in master_timetable.section_to_block:
        return master_timetable.section_to_block[section.id]

    occupied_blocks = getattr(section, "occupied_blocks", None)
    if occupied_blocks:
        return occupied_blocks[0]

    return getattr(section, "time_slot", None)


def get_group_block(master_timetable, sections):
    blocks = [
        get_section_primary_block(master_timetable, section)
        for section in sections
    ]

    for block in blocks:
        if block is not None and block != -1:
            return block

    return None


def get_group_room(sections):
    for section in sections:
        room = getattr(section, "room_id", None)
        if room:
            return str(room)

    return NO_ROOM_FOUND


def group_id_sort_key(group_id):
    match = re.fullmatch(r"sim_(\d+)", group_id)
    if match:
        return int(match.group(1))

    return group_id


def make_course_name_map(courses, master_timetable):
    course_names = {
        course.code: course.name
        for course in courses
    }

    for code, course in getattr(master_timetable, "course_lookup", {}).items():
        if code not in course_names:
            course_names[code] = getattr(course, "name", code)

    return course_names


def build_group_rows(master_timetable, courses, section_enrollment):
    group_sections = build_simultaneous_groups(master_timetable)
    course_names = make_course_name_map(courses, master_timetable)
    group_metadata = {}
    room_block_to_groups = defaultdict(list)

    for group_id, sections in group_sections.items():
        block = get_group_block(master_timetable, sections)
        room = get_group_room(sections)
        total_students = sum(
            section_enrollment.get(section.id, 0)
            for section in sections
        )

        group_metadata[group_id] = {
            "block": block,
            "room": room,
            "sections": sections,
            "total_students": total_students,
        }

        room_block_to_groups[(room, block)].append(group_id)

    for group_ids in room_block_to_groups.values():
        group_ids.sort(key=group_id_sort_key)

    sorted_group_ids = sorted(
        group_metadata,
        key=lambda group_id: (
            group_metadata[group_id]["block"]
            if group_metadata[group_id]["block"] is not None
            else 999,
            group_metadata[group_id]["room"],
            group_id_sort_key(group_id),
        )
    )

    rows = []

    for group_id in sorted_group_ids:
        metadata = group_metadata[group_id]
        block = metadata["block"]
        room = metadata["room"]
        sections = metadata["sections"]
        total_students = metadata["total_students"]

        sharing_groups = [
            other_group_id
            for other_group_id in room_block_to_groups[(room, block)]
            if other_group_id != group_id
        ]

        sharing_text = (
            f"{len(sharing_groups)} groups: {', '.join(sharing_groups)}"
            if sharing_groups
            else "0 groups:"
        )

        section_texts = []
        for section in sections:
            course_name = course_names.get(section.course_code, section.course_code)
            section_texts.append(f"{course_name} ({section.id})")

        rows.append(
            [
                (
                    f"{group_id} "
                    f"(BLOCK {block}) "
                    f"(ROOM {room}) "
                    f"({total_students} STUDENTS) "
                    f"({len(sections)} SECTIONS)"
                ),
                sharing_text,
                ", ".join(section_texts),
            ]
        )

    return rows


def export_view_groups_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Group / Section Info", "Room-Sharing Groups", "Sections"])
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export simultaneous/enrollment group diagnostics."
    )
    parser.add_argument(
        "--pickle",
        default=PICKLE_PATH,
        type=Path,
        help="Path to master_timetable.pkl.",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        type=Path,
        help="CSV output path.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading master timetable pickle: {args.pickle}")
    master_timetable = load_master_timetable(args.pickle)
    validate_master_timetable(master_timetable)

    print("Loading validated student/course data...")
    students, courses, course_lookup = load_validated_data()

    print("Building student schedules for enrollment counts...")
    _, section_enrollment = build_student_timetables(
        students,
        master_timetable,
        course_lookup,
    )

    print("Writing group diagnostic CSV...")
    rows = build_group_rows(
        master_timetable,
        courses,
        section_enrollment,
    )
    export_view_groups_csv(rows, args.output)

    print(f"Exported {len(rows)} row(s) to: {args.output}")


if __name__ == "__main__":
    main()
