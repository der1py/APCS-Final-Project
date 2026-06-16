"""
Run corrected boosted timetable metrics from saved pickle artifacts.

Boost rule:
- Every main request still counts as one course request.
- A main request for any course marked NotSimultaneous adds one extra boosted
  slot for reporting metrics.
- The extra slot is attached to the request itself, so an 8-request student who
  misses a NotSimultaneous main course can still count as boosted 8/8.

This script writes the same output filenames as boosted_metrics_runner.py:
src/output/boosted_metrics_summary.json
src/output/boosted_metrics.csv
"""

import csv
import json
from pathlib import Path

from data.data_loader import (
    BLOCKING_DATA_PATH,
    load_courses_from_json,
    load_students,
)
from output_scripts.metrics import calculate_students_with_conflicts
from timetable_cache import (
    MASTER_TIMETABLE_PICKLE,
    OUTPUT_DIR,
    STUDENT_TIMETABLE_PICKLE,
    load_master_timetable,
    load_student_timetable_result,
)
from validator import validate_courses, validate_students


def _load_validated_data():
    students = load_students()
    courses = load_courses_from_json()

    valid_courses, _ = validate_courses(courses)
    students = validate_students(students, valid_courses)

    return students, list(valid_courses.values())


def _load_not_simultaneous_data(blocking_rules_path):
    pairs = set()
    courses = set()
    path = Path(blocking_rules_path)

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            course_1 = (row.get("Course_1") or "").strip()
            course_2 = (row.get("Course_2") or "").strip()
            blocking_type = (row.get("Blocking_Type") or "").strip()

            if blocking_type != "NotSimultaneous":
                continue

            if not course_1 or not course_2 or course_1 == course_2:
                continue

            pairs.add(frozenset((course_1, course_2)))
            courses.add(course_1)
            courses.add(course_2)

    return pairs, courses


def _notsim_bonus(course_ids, notsim_courses):
    return sum(1 for course in course_ids if course in notsim_courses)


def _boosted_requested_count(main_courses, notsim_courses):
    return len(main_courses) + _notsim_bonus(main_courses, notsim_courses)


def _boosted_placed_main_count(main_courses, schedule, notsim_courses):
    placed_main_count = sum(1 for course in main_courses if course in schedule)
    return placed_main_count + _notsim_bonus(main_courses, notsim_courses)


def _boosted_scheduled_count(student, schedule, notsim_courses):
    return len(schedule) + _notsim_bonus(student.main_courses, notsim_courses)


def _calculate_real_boosted_student_metrics(
    students,
    all_schedules,
    notsim_courses,
):
    total_requested = 0
    total_placed = 0
    seven_to_eight_count = 0
    eight_of_eight_without_alternates_count = 0
    eight_of_eight_with_alternates_count = 0
    half_full_count = 0
    unfulfilled_0_to_2_count = 0
    unfulfilled_3_to_8_count = 0
    normal_total_requested = 0
    normal_total_placed = 0
    normal_unassigned_requests = 0

    for student in students:
        main_courses = list(student.main_courses)
        schedule = all_schedules.get(student.id, {})

        boosted_requested = _boosted_requested_count(
            main_courses,
            notsim_courses,
        )
        boosted_placed = _boosted_placed_main_count(
            main_courses,
            schedule,
            notsim_courses,
        )
        boosted_scheduled = _boosted_scheduled_count(
            student,
            schedule,
            notsim_courses,
        )
        boosted_unfulfilled = max(0, 8 - boosted_scheduled)

        normal_placed = sum(1 for course in main_courses if course in schedule)

        total_requested += boosted_requested
        total_placed += boosted_placed
        normal_total_requested += len(main_courses)
        normal_total_placed += normal_placed
        normal_unassigned_requests += len(main_courses) - normal_placed

        if boosted_placed >= 7:
            seven_to_eight_count += 1

        if boosted_placed >= 8:
            eight_of_eight_without_alternates_count += 1

        if boosted_scheduled >= 8:
            eight_of_eight_with_alternates_count += 1

        if boosted_requested > 0 and (boosted_placed / boosted_requested) >= 0.5:
            half_full_count += 1

        if boosted_unfulfilled <= 2:
            unfulfilled_0_to_2_count += 1

        if 3 <= boosted_unfulfilled <= 8:
            unfulfilled_3_to_8_count += 1

    student_count = len(students)
    boosted_unassigned = total_requested - total_placed
    request_completion = (
        (total_placed / total_requested) * 100
        if total_requested
        else 0.0
    )

    return {
        "student_count": student_count,
        "boosted_total_requested": total_requested,
        "boosted_placed_requested": total_placed,
        "boosted_unassigned_requests": boosted_unassigned,
        "boosted_request_completion_percent": request_completion,
        "boosted_7_to_8_requested_percent": (
            (seven_to_eight_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "boosted_8_of_8_without_alternates_percent": (
            (eight_of_eight_without_alternates_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "boosted_8_of_8_with_alternates_percent": (
            (eight_of_eight_with_alternates_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "boosted_half_full_schedules_percent": (
            (half_full_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "boosted_0_to_2_unfulfilled_percent": (
            (unfulfilled_0_to_2_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "boosted_3_to_8_unfulfilled_percent": (
            (unfulfilled_3_to_8_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "normal_total_requested": normal_total_requested,
        "normal_placed_requested": normal_total_placed,
        "normal_unassigned_requests": normal_unassigned_requests,
    }


def _write_boosted_outputs(summary, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / "boosted_metrics_summary.json"
    csv_path = output_path / "boosted_metrics.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value", "notes"])

        for metric, value in summary["metrics"].items():
            writer.writerow([
                metric,
                value,
                "real boosted metrics; NotSimultaneous main requests add one slot",
            ])

        writer.writerow([
            "not_simultaneous_pair_count",
            summary["not_simultaneous_pair_count"],
            "deduped unordered pairs",
        ])
        writer.writerow([
            "not_simultaneous_course_count",
            summary["not_simultaneous_course_count"],
            "unique courses appearing in NotSimultaneous pairs",
        ])

    return {
        "json": json_path,
        "csv": csv_path,
    }


def run_boosted_metrics_real(
    master_pickle_path=MASTER_TIMETABLE_PICKLE,
    student_pickle_path=STUDENT_TIMETABLE_PICKLE,
    blocking_rules_path=BLOCKING_DATA_PATH,
    output_dir=OUTPUT_DIR,
):
    master_timetable = load_master_timetable(master_pickle_path)
    student_timetable = load_student_timetable_result(student_pickle_path)
    students, _courses = _load_validated_data()
    notsim_pairs, notsim_courses = _load_not_simultaneous_data(
        blocking_rules_path,
    )

    metrics = _calculate_real_boosted_student_metrics(
        students,
        student_timetable.all_schedules,
        notsim_courses,
    )
    metrics["normal_students_with_timetable_conflicts"] = (
        calculate_students_with_conflicts(student_timetable.all_schedules)
    )

    output_path = Path(output_dir)
    summary = {
        "source_files": {
            "master_pickle_path": str(Path(master_pickle_path)),
            "student_pickle_path": str(Path(student_pickle_path)),
            "blocking_rules_path": str(Path(blocking_rules_path)),
        },
        "boost_rule": (
            "Each NotSimultaneous main request adds one extra reporting slot, "
            "even when that specific course was not assigned."
        ),
        "not_simultaneous_pair_count": len(notsim_pairs),
        "not_simultaneous_course_count": len(notsim_courses),
        "master_section_count": len(getattr(master_timetable, "sections", [])),
        "metrics": metrics,
        "output_files": {
            "json": str(output_path / "boosted_metrics_summary.json"),
            "csv": str(output_path / "boosted_metrics.csv"),
        },
    }

    _write_boosted_outputs(summary, output_dir)

    return summary


def main():
    summary = run_boosted_metrics_real()

    print("Real boosted metrics written:")
    for path in summary["output_files"].values():
        print(path)


if __name__ == "__main__":
    main()
