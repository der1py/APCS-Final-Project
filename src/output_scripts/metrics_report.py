from output_scripts.metrics import (
    calculate_request_completion,
    calculate_7_to_8_requested_percent,
    calculate_8_of_8_without_alternates_percent,
    calculate_8_of_8_with_alternates_percent,
    calculate_students_with_conflicts,
    calculate_unassigned_requests,
    calculate_section_enrollment,
    calculate_total_sections,
    calculate_full_sections,
    calculate_under_half_sections,
    calculate_room_conflicts,
    calculate_student_conflicts,
    calculate_invalid_room_assignments,
    calculate_block_distribution,
    calculate_blocking_rule_violation_percent,
    calculate_sequencing_rule_violation_percent,
    calculate_student_sequencing_violation_percent,
    calculate_optimization_score,
    calculate_0_to_2_unfulfilled_percent,
    calculate_3_to_8_unfulfilled_percent,
    calculate_courses_per_block,
    format_courses_per_block,
    calculate_block_balance_difference,
    calculate_room_capacity_violations,
    calculate_room_utilization,
)
from solver.room_config import get_room_capacity_map


def print_metrics_report(
    students,
    courses,
    master_timetable,
    all_schedules,
    section_enrollment,
    runtime_seconds=None,
):
    course_lookup = {
        course.code: course
        for course in courses
    }

    section_capacity = {
        sec.id: course_lookup[sec.course_code].enrollment_max
        for sec in master_timetable.sections
    }

    request_completion = calculate_request_completion(students, all_schedules)

    id_8_of_8_students = []
    for student in students:
        sched = all_schedules.get(student.id, {})
        placed = sum(1 for course in student.main_courses if course in sched)
        if len(student.main_courses) == 8 and placed == 8:
            id_8_of_8_students.append(student.id)

    eight_of_eight_without_alternates = (
        calculate_8_of_8_without_alternates_percent(
            students,
            all_schedules,
        )
    )

    count_half_or_more = 0
    for student in students:
        sched = all_schedules.get(student.id, {})
        placed = sum(1 for course in student.main_courses if course in sched)
        total = len(student.main_courses) if student.main_courses else 1
        if (placed / total) >= 0.5:
            count_half_or_more += 1

    percent_half_or_more = (
        (count_half_or_more / len(students)) * 100
        if students
        else 0
    )

    seven_to_eight_requested = calculate_7_to_8_requested_percent(
        students,
        all_schedules,
    )
    eight_of_eight_with_alternates = calculate_8_of_8_with_alternates_percent(
        students,
        all_schedules,
    )
    students_with_conflicts = calculate_students_with_conflicts(all_schedules)
    unassigned_requests = calculate_unassigned_requests(students, all_schedules)
    unfulfilled_0_to_2 = calculate_0_to_2_unfulfilled_percent(
        students,
        all_schedules,
    )
    unfulfilled_3_to_8 = calculate_3_to_8_unfulfilled_percent(
        students,
        all_schedules,
    )

    section_enrollment_metric = calculate_section_enrollment(section_enrollment)
    total_sections = calculate_total_sections(master_timetable.sections)
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

    room_conflicts = calculate_room_conflicts(
        master_timetable.sections,
        master_timetable.section_to_block,
    )
    student_conflicts = calculate_student_conflicts(all_schedules)
    invalid_room_assignments = calculate_invalid_room_assignments(
        master_timetable.sections,
    )
    room_capacity_violations = calculate_room_capacity_violations(
        master_timetable.sections,
        master_timetable.section_to_block,
        get_room_capacity_map(),
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
    block_distribution = calculate_block_distribution(
        master_timetable.section_to_block,
    )
    block_courses = calculate_courses_per_block(
        master_timetable.sections,
        master_timetable.section_to_block,
    )
    block_balance_difference = calculate_block_balance_difference(block_courses)
    blocking_rule_violation = calculate_blocking_rule_violation_percent(
        master_timetable.course_to_sections,
        master_timetable.section_to_block,
    )
    sequencing_rule_violation = calculate_sequencing_rule_violation_percent(
        students,
        master_timetable.course_to_sections,
        master_timetable.section_to_block,
    )
    student_sequencing_violation = (
        calculate_student_sequencing_violation_percent(
            students,
            all_schedules,
        )
    )

    optimization_score = calculate_optimization_score(
        students,
        all_schedules,
        master_timetable.sections,
        section_enrollment,
        section_capacity,
        master_timetable.section_to_block,
    )

    print("--- Student Metrics ---")
    print(
        "Request Completion: "
        f"{request_completion:.2f}% "
        f"{'PASS' if request_completion > 70 else 'FAIL'}"
    )
    print(
        "8/8 Courses (without Alternates): "
        f"{eight_of_eight_without_alternates:.2f}% "
        f"{'PASS' if eight_of_eight_without_alternates > 30 else 'FAIL'}"
    )
    print(f"Half-Full Schedules: {percent_half_or_more:.2f}%")
    print(f"7-8/8 Requested Courses: {seven_to_eight_requested:.2f}%")
    print(
        "8/8 Courses (with Alternates): "
        f"{eight_of_eight_with_alternates:.2f}% "
        f"{'PASS' if eight_of_eight_with_alternates > 50 else 'FAIL'}"
    )
    print(
        "0-2 Unfulfilled Courses: "
        f"{unfulfilled_0_to_2:.2f}% "
        f"{'PASS' if unfulfilled_0_to_2 > 50 else 'FAIL'}"
    )
    print(
        "3-8 Unfulfilled Courses: "
        f"{unfulfilled_3_to_8:.2f}% "
        f"{'PASS' if unfulfilled_3_to_8 < 15 else 'FAIL'}"
    )
    print(f"Students with Timetable Conflicts: {students_with_conflicts}")
    print(f"Unassigned Course Requests: {unassigned_requests}")
    print(f"Students with 8/8 requested courses placed: {id_8_of_8_students}")

    print("\n--- Enrollment Metrics ---")
    print(f"Total Number of Sections: {total_sections}")
    print(f"Full Enrollment Groups: {full_sections}")
    print(f"Active Enrollment Groups Below 50%: {under_half_sections}")
    # print(f"Section Enrollment: {section_enrollment_metric}")
    _ = section_enrollment_metric

    print("\n--- Timetable Metrics ---")
    print(f"Room Conflicts: {room_conflicts}")
    print(f"Room Capacity Violations: {room_capacity_violations}")
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
    print(
        "Low-Use Rooms (<=2 blocks): "
        + ", ".join(
            f"{room}:{used}"
            for room, used in room_utilization["low_used_rooms"][:12]
        )
    )
    print(
        "Busiest Rooms: "
        + ", ".join(
            f"{room}:{used_blocks} blocks/{group_occupancies} groups"
            for room, used_blocks, group_occupancies, _shared
            in room_utilization["busiest_rooms"][:8]
        )
    )
    print(f"Student Conflicts: {student_conflicts}")
    print(f"Invalid Room Assignments: {invalid_room_assignments}")
    print(f"Section per block: {block_distribution}")
    print(f"Course per block:  {format_courses_per_block(block_courses)}")
    print(
        "Largest-Smallest Course Difference: "
        f"{block_balance_difference} "
        f"{'PASS' if block_balance_difference <= 4 else 'FAIL'}"
    )
    print(f"Blocking Rule Violation: {blocking_rule_violation:.2f}%")
    print(f"Sequencing Rule Violation: {sequencing_rule_violation:.2f}%")
    print(
        "Student Sequencing Rule Violation: "
        f"{student_sequencing_violation:.2f}%"
    )
    if runtime_seconds is not None:
        print(f"Full Timetable Runtime: {runtime_seconds:.3f} seconds")
    else:
        print("Full Timetable Runtime: loaded from cache")
    print(f"\nOptimization Score: {optimization_score}")
