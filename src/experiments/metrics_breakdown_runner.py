"""
Run a pickle-only timetable metrics report with score breakdowns.

This script loads the cached master timetable and student timetable artifacts.
It does not rebuild the master timetable and does not run the student CP-SAT.
"""

import math
from collections import Counter, defaultdict

from data.data_loader import (
    load_courses_from_json,
    load_rules,
    load_simultaneous_blocking_rules,
    load_students,
)
from output_scripts.metrics import (
    calculate_0_to_2_unfulfilled_percent,
    calculate_3_to_8_unfulfilled_percent,
    calculate_7_to_8_requested_percent,
    calculate_8_of_8_with_alternates_percent,
    calculate_8_of_8_without_alternates_percent,
    calculate_block_balance_difference,
    calculate_courses_per_block,
    calculate_full_sections,
    calculate_request_completion,
    calculate_room_capacity_violations,
    calculate_room_utilization,
    calculate_under_half_sections,
    format_courses_per_block,
)
from solver.room_config import DEFAULT_ROOM_CAPACITY, get_room_capacity_map
from timetable_cache import (
    MASTER_TIMETABLE_PICKLE,
    STUDENT_TIMETABLE_PICKLE,
    load_master_timetable,
    load_student_timetable_result,
)
from validator import validate_courses, validate_students


BLOCKS = list(range(8))
SEMESTER_1_BLOCKS = {0, 1, 2, 3}
SEMESTER_2_BLOCKS = {4, 5, 6, 7}
DEFAULT_SECTION_CAPACITY = 30


def _load_validated_data():
    students = load_students()
    courses = load_courses_from_json()

    valid_courses, _invalid_courses = validate_courses(courses)
    students = validate_students(students, valid_courses)

    return students, list(valid_courses.values())


def _section_blocks(section, section_to_block):
    occupied = getattr(section, "occupied_blocks", None)

    if occupied:
        return list(occupied)

    block = section_to_block.get(section.id, getattr(section, "time_slot", None))

    if block is None or block == -1:
        return []

    return [block]


def _assigned_blocks(value):
    _section_id, blocks = value

    if isinstance(blocks, list):
        return blocks

    if blocks is None:
        return []

    return [blocks]


def _is_notsim_pair(course_1, course_2, notsim_pairs):
    return (
        course_1 != course_2
        and frozenset((course_1, course_2)) in notsim_pairs
    )


def _build_enrollment_groups(sections):
    section_by_id = {
        section.id: section
        for section in sections
    }
    course_to_sections = defaultdict(list)

    for section in sections:
        course_to_sections[section.course_code].append(section)

    groups = {}
    section_to_group = {}
    group_counter = 0
    blocking_rules = load_simultaneous_blocking_rules()

    for course_1, course_2 in blocking_rules.get("Simultaneous", []):
        if course_1 not in course_to_sections:
            continue

        if course_2 not in course_to_sections:
            continue

        sections_1 = course_to_sections[course_1]
        sections_2 = course_to_sections[course_2]

        for index in range(min(len(sections_1), len(sections_2))):
            section_1 = sections_1[index]
            section_2 = sections_2[index]

            group_1 = section_to_group.get(section_1.id)
            group_2 = section_to_group.get(section_2.id)

            if group_1 is None and group_2 is None:
                group_id = f"group_{group_counter}"
                group_counter += 1
                groups[group_id] = {section_1.id, section_2.id}
                section_to_group[section_1.id] = group_id
                section_to_group[section_2.id] = group_id

            elif group_1 is not None and group_2 is None:
                groups[group_1].add(section_2.id)
                section_to_group[section_2.id] = group_1

            elif group_1 is None and group_2 is not None:
                groups[group_2].add(section_1.id)
                section_to_group[section_1.id] = group_2

            elif group_1 != group_2:
                for section_id in groups[group_2]:
                    groups[group_1].add(section_id)
                    section_to_group[section_id] = group_1

                del groups[group_2]

    for section in sections:
        if section.id in section_to_group:
            continue

        group_id = f"group_{group_counter}"
        group_counter += 1
        groups[group_id] = {section.id}
        section_to_group[section.id] = group_id

    return {
        group_id: [
            section_by_id[section_id]
            for section_id in sorted(section_ids)
        ]
        for group_id, section_ids in groups.items()
    }


def _build_section_capacity(sections, course_lookup):
    capacity = {}

    for section in sections:
        course = course_lookup.get(section.course_code)
        section_capacity = (
            course.enrollment_max
            if course is not None
            else DEFAULT_SECTION_CAPACITY
        )

        if section_capacity <= 0:
            section_capacity = DEFAULT_SECTION_CAPACITY

        capacity[section.id] = section_capacity

    return capacity


def _format_block_counts(counts):
    return ", ".join(
        f"Block {block}: {counts.get(block, 0)}"
        for block in BLOCKS
    )


def _count_placed_main_requests(students, all_schedules):
    placed = 0

    for student in students:
        schedule = all_schedules.get(student.id, {})

        for course in student.main_courses:
            if course in schedule:
                placed += 1

    return placed


def _count_full_requested_timetables(students, all_schedules):
    full = 0

    for student in students:
        schedule = all_schedules.get(student.id, {})
        placed = sum(
            1
            for course in student.main_courses
            if course in schedule
        )

        if placed == len(student.main_courses):
            full += 1

    return full


def _count_student_double_bookings(all_schedules):
    blocking_rules = load_simultaneous_blocking_rules()
    notsim_pairs = {
        frozenset((course_1, course_2))
        for course_1, course_2 in blocking_rules.get("NotSimultaneous", [])
    }
    violations = 0

    for schedule in all_schedules.values():
        courses_by_block = defaultdict(list)

        for course, value in schedule.items():
            for block in _assigned_blocks(value):
                has_conflict = any(
                    not _is_notsim_pair(course, existing, notsim_pairs)
                    for existing in courses_by_block[block]
                )

                if has_conflict:
                    violations += 1
                else:
                    courses_by_block[block].append(course)

    return violations


def _count_over_capacity_sections(sections, section_enrollment, section_capacity):
    over_capacity = 0

    for section in sections:
        enrolled = section_enrollment.get(section.id, 0)
        capacity = section_capacity.get(section.id, DEFAULT_SECTION_CAPACITY)

        if enrolled > capacity:
            over_capacity += 1

    return over_capacity


def _count_invalid_room_assignments(sections, course_lookup):
    invalid = 0

    for section in sections:
        room = getattr(section, "room_id", None)

        if room is None or room == "NO ROOM FOUND":
            invalid += 1
            continue

        course = course_lookup.get(section.course_code)

        if course is None:
            invalid += 1
            continue

        allowed_rooms = set(course.rooms + course.back_up_rooms)

        if allowed_rooms and str(room) not in {str(r) for r in allowed_rooms}:
            invalid += 1

    return invalid


def _count_room_double_bookings(sections, section_to_block):
    room_usage = defaultdict(set)

    for group_id, grouped_sections in _build_enrollment_groups(sections).items():
        room = None
        occupied_blocks = set()

        for section in grouped_sections:
            if room is None and getattr(section, "room_id", None):
                room = str(section.room_id)

            occupied_blocks.update(
                _section_blocks(section, section_to_block)
            )

        if not room:
            room = "NO ROOM FOUND"

        for block in occupied_blocks:
            room_usage[(room, block)].add(group_id)

    return sum(
        max(0, len(group_ids) - 1)
        for group_ids in room_usage.values()
    )


def _count_blocking_rule_violations(course_to_sections, section_to_block):
    blocking_rules = load_simultaneous_blocking_rules()
    violations = 0

    for blocking_type, pairs in blocking_rules.items():
        for course_1, course_2 in pairs:
            if course_1 not in course_to_sections:
                continue

            if course_2 not in course_to_sections:
                continue

            sections_1 = course_to_sections[course_1]
            sections_2 = course_to_sections[course_2]

            if blocking_type in {"Simultaneous", "NotSimultaneous"}:
                for index in range(min(len(sections_1), len(sections_2))):
                    blocks_1 = set(
                        _section_blocks(sections_1[index], section_to_block)
                    )
                    blocks_2 = set(
                        _section_blocks(sections_2[index], section_to_block)
                    )

                    if blocks_1 != blocks_2:
                        violations += 1

            elif blocking_type == "Consecutive":
                first_in_semester_1 = any(
                    block in SEMESTER_1_BLOCKS
                    for section in sections_1
                    for block in _section_blocks(section, section_to_block)
                )
                second_in_semester_2 = any(
                    block in SEMESTER_2_BLOCKS
                    for section in sections_2
                    for block in _section_blocks(section, section_to_block)
                )

                if not (first_in_semester_1 and second_in_semester_2):
                    violations += 1

    return violations


def _count_sequencing_rule_violations(
    students,
    course_to_sections,
    section_to_block,
    course_lookup,
):
    rules = load_rules()
    sequence_demand = defaultdict(int)
    violations = 0

    for student in students:
        requested = set(student.main_courses)

        for prerequisite, advanced in rules.sequence_pairs:
            if prerequisite in requested and advanced in requested:
                sequence_demand[(prerequisite, advanced)] += 1

    for prerequisite, advanced in rules.sequence_pairs:
        demand = sequence_demand.get((prerequisite, advanced), 0)

        if demand == 0:
            continue

        if prerequisite not in course_to_sections:
            continue

        if advanced not in course_to_sections:
            continue

        prerequisite_course = course_lookup.get(prerequisite)
        capacity = (
            prerequisite_course.enrollment_max
            if prerequisite_course is not None
            else DEFAULT_SECTION_CAPACITY
        )

        if capacity <= 0:
            capacity = DEFAULT_SECTION_CAPACITY

        required_sections = math.ceil(demand / capacity)
        prerequisite_semester_1 = sum(
            any(
                block in SEMESTER_1_BLOCKS
                for block in _section_blocks(section, section_to_block)
            )
            for section in course_to_sections[prerequisite]
        )
        advanced_semester_2 = sum(
            any(
                block in SEMESTER_2_BLOCKS
                for block in _section_blocks(section, section_to_block)
            )
            for section in course_to_sections[advanced]
        )

        if (
            prerequisite_semester_1 < required_sections
            or advanced_semester_2 < required_sections
        ):
            violations += 1

    return violations


def _count_student_sequencing_violations(students, all_schedules):
    rules = load_rules()
    violations = 0

    for student in students:
        schedule = all_schedules.get(student.id, {})

        for prerequisite, subsequent in rules.sequence_pairs:
            if prerequisite not in schedule:
                continue

            if subsequent not in schedule:
                continue

            prerequisite_in_semester_1 = any(
                block in SEMESTER_1_BLOCKS
                for block in _assigned_blocks(schedule[prerequisite])
            )
            subsequent_in_semester_2 = any(
                block in SEMESTER_2_BLOCKS
                for block in _assigned_blocks(schedule[subsequent])
            )

            if not (
                prerequisite_in_semester_1
                and subsequent_in_semester_2
            ):
                violations += 1

    return violations


def _count_linear_course_violations(sections, section_to_block, course_lookup):
    violations = 0

    for section in sections:
        course = course_lookup.get(section.course_code)

        if course is None or not course.linear:
            continue

        occupied_blocks = _section_blocks(section, section_to_block)
        semester_1_count = sum(
            1
            for block in occupied_blocks
            if block in SEMESTER_1_BLOCKS
        )
        semester_2_count = sum(
            1
            for block in occupied_blocks
            if block in SEMESTER_2_BLOCKS
        )

        if semester_1_count != 1 or semester_2_count != 1:
            violations += 1

    return violations


def _count_balanced_blocks(section_to_block):
    counts = Counter(section_to_block.values())
    values = list(counts.values())

    if not values:
        return 0

    average = sum(values) / len(values)

    return sum(
        1
        for count in values
        if abs(count - average) <= 1
    )


def _build_score_breakdown(
    students,
    all_schedules,
    sections,
    section_enrollment,
    section_capacity,
    section_to_block,
):
    placed_requests = _count_placed_main_requests(students, all_schedules)
    full_timetables = _count_full_requested_timetables(
        students,
        all_schedules,
    )
    student_conflicts = _count_student_double_bookings(all_schedules)
    overfilled_sections = _count_over_capacity_sections(
        sections,
        section_enrollment,
        section_capacity,
    )
    balanced_blocks = _count_balanced_blocks(section_to_block)

    components = [
        {
            "label": "Requested Courses Placed",
            "count": placed_requests,
            "points_each": 10,
            "points": placed_requests * 10,
        },
        {
            "label": "Full Requested Timetables",
            "count": full_timetables,
            "points_each": 50,
            "points": full_timetables * 50,
        },
        {
            "label": "Student Conflict Penalties",
            "count": student_conflicts,
            "points_each": -1000,
            "points": student_conflicts * -1000,
        },
        {
            "label": "Overfilled Section Penalties",
            "count": overfilled_sections,
            "points_each": -1000,
            "points": overfilled_sections * -1000,
        },
        {
            "label": "Balanced Block Bonus",
            "count": balanced_blocks,
            "points_each": 1,
            "points": balanced_blocks,
        },
    ]

    return components, sum(component["points"] for component in components)


def _print_score_breakdown(components, total_score):
    print("\n--- Optimization Score Breakdown ---")

    for component in components:
        points = component["points"]

        print(
            f"{component['label']}: "
            f"{component['count']} x {component['points_each']} = {points}"
        )

        if component["points_each"] < 0:
            print(f"  Points Lost: {-points}")

    print(f"Final Optimization Score: {total_score}")


def main():
    print(f"Loading master timetable pickle: {MASTER_TIMETABLE_PICKLE}")
    master_timetable = load_master_timetable()

    print(f"Loading student timetable pickle: {STUDENT_TIMETABLE_PICKLE}")
    student_timetable = load_student_timetable_result()

    students, courses = _load_validated_data()
    course_lookup = {
        course.code: course
        for course in courses
    }
    all_schedules = student_timetable.all_schedules
    section_enrollment = student_timetable.section_enrollment
    section_capacity = _build_section_capacity(
        master_timetable.sections,
        course_lookup,
    )

    request_completion = calculate_request_completion(students, all_schedules)
    eight_of_eight_without_alternates = (
        calculate_8_of_8_without_alternates_percent(
            students,
            all_schedules,
        )
    )
    seven_to_eight_requested = calculate_7_to_8_requested_percent(
        students,
        all_schedules,
    )
    eight_of_eight_with_alternates = (
        calculate_8_of_8_with_alternates_percent(
            students,
            all_schedules,
        )
    )
    unfulfilled_0_to_2 = calculate_0_to_2_unfulfilled_percent(
        students,
        all_schedules,
    )
    unfulfilled_3_to_8 = calculate_3_to_8_unfulfilled_percent(
        students,
        all_schedules,
    )

    count_half_or_more = 0

    for student in students:
        schedule = all_schedules.get(student.id, {})
        placed = sum(
            1
            for course in student.main_courses
            if course in schedule
        )
        total = len(student.main_courses) if student.main_courses else 1

        if (placed / total) >= 0.5:
            count_half_or_more += 1

    percent_half_or_more = (
        (count_half_or_more / len(students)) * 100
        if students
        else 0.0
    )

    total_sections = len(master_timetable.sections)
    full_sections = calculate_full_sections(
        master_timetable.sections,
        section_enrollment,
        section_capacity,
    )
    under_half_sections = calculate_under_half_sections(
        master_timetable.sections,
        section_enrollment,
        section_capacity,
    )

    section_block_counts = Counter(master_timetable.section_to_block.values())
    courses_per_block = calculate_courses_per_block(
        master_timetable.sections,
        master_timetable.section_to_block,
    )
    block_balance_difference = calculate_block_balance_difference(
        courses_per_block,
    )

    all_rooms = sorted({
        room
        for course in courses
        for room in (course.rooms + course.back_up_rooms)
    })
    room_utilization = calculate_room_utilization(
        master_timetable.sections,
        master_timetable.section_to_block,
        all_rooms,
        get_room_capacity_map(),
    )
    room_capacity_violations = calculate_room_capacity_violations(
        master_timetable.sections,
        master_timetable.section_to_block,
        get_room_capacity_map(),
        DEFAULT_ROOM_CAPACITY,
    )

    student_double_bookings = _count_student_double_bookings(all_schedules)
    room_double_bookings = _count_room_double_bookings(
        master_timetable.sections,
        master_timetable.section_to_block,
    )
    over_capacity_sections = _count_over_capacity_sections(
        master_timetable.sections,
        section_enrollment,
        section_capacity,
    )
    invalid_room_assignments = _count_invalid_room_assignments(
        master_timetable.sections,
        course_lookup,
    )
    blocking_rule_violations = _count_blocking_rule_violations(
        master_timetable.course_to_sections,
        master_timetable.section_to_block,
    )
    sequencing_rule_violations = _count_sequencing_rule_violations(
        students,
        master_timetable.course_to_sections,
        master_timetable.section_to_block,
        course_lookup,
    )
    student_sequencing_violations = _count_student_sequencing_violations(
        students,
        all_schedules,
    )
    linear_course_violations = _count_linear_course_violations(
        master_timetable.sections,
        master_timetable.section_to_block,
        course_lookup,
    )

    score_components, final_score = _build_score_breakdown(
        students,
        all_schedules,
        master_timetable.sections,
        section_enrollment,
        section_capacity,
        master_timetable.section_to_block,
    )

    print("\n--- Student Metrics ---")
    print(f"Request Completion: {request_completion:.2f}%")
    print(
        "8/8 Courses (without Alternates): "
        f"{eight_of_eight_without_alternates:.2f}%"
    )
    print(f"Half-Full Schedules: {percent_half_or_more:.2f}%")
    print(f"7-8/8 Requested Courses: {seven_to_eight_requested:.2f}%")
    print(
        "8/8 Courses (with Alternates): "
        f"{eight_of_eight_with_alternates:.2f}%"
    )
    print(f"0-2 Unfulfilled Courses: {unfulfilled_0_to_2:.2f}%")
    print(f"3-8 Unfulfilled Courses: {unfulfilled_3_to_8:.2f}%")

    print("\n--- Enrollment Metrics ---")
    print(f"Total Number of Sections: {total_sections}")
    print(f"Full Enrollment Groups: {full_sections}")
    print(f"Active Enrollment Groups Below 50%: {under_half_sections}")

    print("\n--- Timetable Balance Metrics ---")
    print(f"Sections per Block: {_format_block_counts(section_block_counts)}")
    print(f"Courses per Block:  {format_courses_per_block(courses_per_block)}")
    print(
        "Largest-Smallest Course Difference: "
        f"{block_balance_difference} "
        f"{'PASS' if block_balance_difference <= 4 else 'FAIL'}"
    )

    print("\n--- Room Metrics ---")
    print(
        "Room Block Utilization: "
        f"{room_utilization['used_room_blocks']}/"
        f"{room_utilization['total_room_blocks']} "
        f"({room_utilization['utilization_percent']:.1f}%)"
    )
    print(
        "Room Group Occupancies: "
        f"{room_utilization['total_group_occupancies']} "
        f"(shared excess {room_utilization['shared_group_occupancies']})"
    )
    print(f"Room Capacity Violations: {room_capacity_violations}")

    print("\n--- Hard Constraint Verification ---")
    print(f"Student Double-Bookings: {student_double_bookings}")
    print(f"Room Double-Bookings: {room_double_bookings}")
    print(f"Over-Capacity Sections: {over_capacity_sections}")
    print(f"Invalid Room Assignments: {invalid_room_assignments}")
    print(f"Blocking Rule Violations: {blocking_rule_violations}")
    print(f"Sequencing Rule Violations: {sequencing_rule_violations}")
    print(
        "Student Sequencing Rule Violations: "
        f"{student_sequencing_violations}"
    )
    print(f"Linear Course Violations: {linear_course_violations}")

    _print_score_breakdown(score_components, final_score)


if __name__ == "__main__":
    main()
