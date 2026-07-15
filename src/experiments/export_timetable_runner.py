"""
Reload a saved master timetable pickle and regenerate the CSV exports.

This skips rebuilding the master timetable, but it still derives student
assignments so the student CSVs and master timetable enrollment counts stay
consistent with the normal export pipeline.
"""

import pickle
from pathlib import Path

from data.data_loader import load_courses_from_json, load_students
from output_scripts.export import (
    export_master_csv,
    export_room_timetable_csv,
    export_student_csv,
    export_student_csv_code,
)
from solver.student_timetable_cpsat import build_student_timetables
from validator import validate_courses, validate_students


SRC_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = SRC_DIR / "output"
PICKLE_PATH = OUTPUT_DIR / "master_timetable.pkl"
BLOCKS = list(range(8))


def load_master_timetable(pickle_path=PICKLE_PATH):
    with Path(pickle_path).open("rb") as file:
        return pickle.load(file)


def validate_master_timetable(master_timetable):
    required_attrs = [
        "sections",
        "section_to_block",
        "course_to_sections",
        "section_by_id",
        "course_lookup",
        "section_to_blocks",
    ]

    missing_attrs = [
        attr
        for attr in required_attrs
        if not hasattr(master_timetable, attr)
    ]
    if missing_attrs:
        raise ValueError(
            "Pickled master timetable is missing: "
            + ", ".join(missing_attrs)
        )

    section_ids = {
        section.id
        for section in master_timetable.sections
    }

    errors = []

    for name in ("section_to_block", "section_to_blocks", "section_by_id"):
        mapping_ids = set(getattr(master_timetable, name))
        missing_ids = section_ids - mapping_ids
        extra_ids = mapping_ids - section_ids

        if missing_ids:
            errors.append(f"{name} missing {len(missing_ids)} section(s)")
        if extra_ids:
            errors.append(f"{name} has {len(extra_ids)} unknown section(s)")

    for section in master_timetable.sections:
        blocks = master_timetable.section_to_blocks.get(section.id)

        if not blocks:
            errors.append(f"{section.id} has no occupied blocks")
            continue

        if master_timetable.section_to_block.get(section.id) != blocks[0]:
            errors.append(f"{section.id} primary block does not match")

        occupied_blocks = list(getattr(section, "occupied_blocks", []))
        if occupied_blocks != list(blocks):
            errors.append(f"{section.id} occupied blocks do not match")

    course_section_count = sum(
        len(sections)
        for sections in master_timetable.course_to_sections.values()
    )
    if course_section_count != len(master_timetable.sections):
        errors.append(
            "course_to_sections contains "
            f"{course_section_count} section reference(s), expected "
            f"{len(master_timetable.sections)}"
        )

    if errors:
        raise ValueError(
            "Pickled master timetable is incomplete:\n- "
            + "\n- ".join(errors[:10])
        )


def load_validated_data():
    students = load_students()
    courses = load_courses_from_json()

    valid_courses, _ = validate_courses(courses)
    students = validate_students(students, valid_courses)
    courses = list(valid_courses.values())

    return students, courses, valid_courses


def main():
    print(f"Loading master timetable pickle: {PICKLE_PATH}")
    master_timetable = load_master_timetable()
    validate_master_timetable(master_timetable)

    students, courses, course_lookup = load_validated_data()

    print("Building student schedules from saved master timetable...")
    all_schedules, section_enrollment = build_student_timetables(
        students,
        master_timetable,
        course_lookup,
    )

    print("Writing CSV exports...")
    export_master_csv(
        master_timetable.section_to_block,
        BLOCKS,
        output_path=OUTPUT_DIR / "master_timetable.csv",
        master_timetable=master_timetable,
        courses=courses,
        section_enrollment=section_enrollment,
    )
    export_room_timetable_csv(
        master_timetable,
        BLOCKS,
        output_path=OUTPUT_DIR / "master_timetable_by_room.csv",
        courses=courses,
        section_enrollment=section_enrollment,
    )
    export_student_csv_code(
        students,
        all_schedules,
        BLOCKS,
        output_path=OUTPUT_DIR / "student_schedules.csv",
        master_timetable=master_timetable,
    )
    export_student_csv(
        students,
        all_schedules,
        courses,
        BLOCKS,
        OUTPUT_DIR / "student_schedules_by_name.csv",
        master_timetable=master_timetable,
    )

    print("CSV exports complete.")


if __name__ == "__main__":
    main()
