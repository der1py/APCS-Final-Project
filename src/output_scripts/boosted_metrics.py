import csv
import json
from pathlib import Path

from data.data_loader import load_courses_from_json, load_students
from output_scripts.metrics import calculate_students_with_conflicts
from timetable_cache import load_master_timetable, load_student_timetable_result
from validator import validate_courses, validate_students


def _load_validated_data():
    students = load_students()
    courses = load_courses_from_json()

    valid_courses, _ = validate_courses(courses)
    students = validate_students(students, valid_courses)

    return students, list(valid_courses.values())


def _load_not_simultaneous_pairs(blocking_rules_path):
    pairs = set()
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

    return pairs


def _weighted_course_count(course_ids, notsim_pairs):
    course_set = set(course_ids)
    accounted = set()
    total = 0

    sorted_pairs = sorted(
        notsim_pairs,
        key=lambda pair: tuple(sorted(pair)),
    )

    for pair in sorted_pairs:
        pair_courses = set(pair)
        present = pair_courses & course_set
        unaccounted_present = present - accounted

        if not unaccounted_present:
            continue

        if present == unaccounted_present:
            total += 2
            accounted.update(pair_courses)

    total += len(course_set - accounted)

    return total


def _calculate_boosted_student_metrics(students, all_schedules, notsim_pairs):
    total_requested = 0
    total_placed = 0
    seven_to_eight_count = 0
    eight_of_eight_count = 0
    half_full_count = 0
    unfulfilled_0_to_2_count = 0
    unfulfilled_3_to_8_count = 0
    normal_total_requested = 0
    normal_total_placed = 0

    for student in students:
        requested_courses = list(student.main_courses)
        schedule = all_schedules.get(student.id, {})
        placed_requested_courses = [
            course
            for course in requested_courses
            if course in schedule
        ]

        boosted_requested = _weighted_course_count(
            requested_courses,
            notsim_pairs,
        )
        boosted_placed = _weighted_course_count(
            placed_requested_courses,
            notsim_pairs,
        )
        boosted_unfulfilled = max(0, boosted_requested - boosted_placed)

        total_requested += boosted_requested
        total_placed += boosted_placed
        normal_total_requested += len(requested_courses)
        normal_total_placed += len(placed_requested_courses)

        if boosted_placed >= 7:
            seven_to_eight_count += 1

        if boosted_requested == 8 and boosted_placed == 8:
            eight_of_eight_count += 1

        if boosted_requested > 0 and (boosted_placed / boosted_requested) >= 0.5:
            half_full_count += 1

        if boosted_unfulfilled <= 2:
            unfulfilled_0_to_2_count += 1

        if 3 <= boosted_unfulfilled <= 8:
            unfulfilled_3_to_8_count += 1

    student_count = len(students)
    request_completion = (
        (total_placed / total_requested) * 100
        if total_requested
        else 0.0
    )

    return {
        "student_count": student_count,
        "boosted_total_requested": total_requested,
        "boosted_placed_requested": total_placed,
        "boosted_unassigned_requests": total_requested - total_placed,
        "boosted_request_completion_percent": request_completion,
        "boosted_7_to_8_requested_percent": (
            (seven_to_eight_count / student_count) * 100
            if student_count
            else 0.0
        ),
        "boosted_8_of_8_without_alternates_percent": (
            (eight_of_eight_count / student_count) * 100
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
            writer.writerow([metric, value, "boosted reporting hotfix"])

        writer.writerow([
            "not_simultaneous_pair_count",
            summary["not_simultaneous_pair_count"],
            "deduped unordered pairs",
        ])

    return {
        "json": json_path,
        "csv": csv_path,
    }


def run_boosted_metrics(
    master_pickle_path,
    student_pickle_path,
    blocking_rules_path,
    output_dir,
):
    master_timetable = load_master_timetable(master_pickle_path)
    student_timetable = load_student_timetable_result(student_pickle_path)
    students, _courses = _load_validated_data()

    notsim_pairs = _load_not_simultaneous_pairs(blocking_rules_path)

    metrics = _calculate_boosted_student_metrics(
        students,
        student_timetable.all_schedules,
        notsim_pairs,
    )
    metrics["normal_students_with_timetable_conflicts"] = (
        calculate_students_with_conflicts(student_timetable.all_schedules)
    )

    summary = {
        "source_files": {
            "master_pickle_path": str(Path(master_pickle_path)),
            "student_pickle_path": str(Path(student_pickle_path)),
            "blocking_rules_path": str(Path(blocking_rules_path)),
        },
        "not_simultaneous_pair_count": len(notsim_pairs),
        "master_section_count": len(getattr(master_timetable, "sections", [])),
        "metrics": metrics,
    }

    output_path = Path(output_dir)
    summary["output_files"] = {
        "json": str(output_path / "boosted_metrics_summary.json"),
        "csv": str(output_path / "boosted_metrics.csv"),
    }

    _write_boosted_outputs(summary, output_dir)

    return summary
