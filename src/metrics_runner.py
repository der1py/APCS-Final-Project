"""
Run timetable metrics from saved pickle artifacts.

This runner does not rebuild the master timetable and does not run the student
assignment CP-SAT. It expects src/main.py to have generated both pickle files.
"""

from data.data_loader import load_courses_from_json, load_students
from output_scripts.metrics_report import print_metrics_report
from timetable_cache import (
    MASTER_TIMETABLE_PICKLE,
    STUDENT_TIMETABLE_PICKLE,
    load_master_timetable,
    load_student_timetable_result,
)
from validator import validate_courses, validate_students


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


def load_validated_data():
    students = load_students()
    courses = load_courses_from_json()

    valid_courses, _ = validate_courses(courses)
    students = validate_students(students, valid_courses)
    courses = list(valid_courses.values())

    return students, courses


def main():
    print(f"Loading master timetable pickle: {MASTER_TIMETABLE_PICKLE}")
    master_timetable = load_master_timetable()
    validate_master_timetable(master_timetable)

    print(f"Loading student timetable pickle: {STUDENT_TIMETABLE_PICKLE}")
    student_timetable = load_student_timetable_result()

    students, courses = load_validated_data()

    print_metrics_report(
        students=students,
        courses=courses,
        master_timetable=master_timetable,
        all_schedules=student_timetable.all_schedules,
        section_enrollment=student_timetable.section_enrollment,
    )


if __name__ == "__main__":
    main()
