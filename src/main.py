from data.data_loader import load_students
from data.course_loader import load_courses_from_csv

from solver.master_timetable_builder import build_master_timetable
from solver.student_timetable_builder import generate_all_student_schedules

from validator import validate_courses, validate_students

from output_scripts.export import export_all

from output_scripts.metrics import (
    calculate_request_completion,
    calculate_7_to_8_requested_percent,
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
    calculate_blocking_rule_success_percent,
    calculate_full_schedules,
    calculate_half_full_schedules,
    calculate_optimization_score,
)


# =====================================================
# LOAD DATA
# =====================================================

students = load_students()
courses = load_courses_from_csv()


# =====================================================
# VALIDATION
# =====================================================

valid_courses, invalid_courses = validate_courses(courses)

students = validate_students(
    students,
    valid_courses
)

courses = list(valid_courses.values())


# =====================================================
# MASTER TIMETABLE
# =====================================================

master_timetable = build_master_timetable(
    students,
    courses
)

# TODO comment ts
course_lookup = {
    course.code: course
    for course in courses
}

section_capacity = {
    sec.id: course_lookup[sec.course_code].enrollment_max
    for sec in master_timetable.sections
}

# =====================================================
# STUDENT ASSIGNMENTS
# =====================================================

all_schedules, section_enrollment = generate_all_student_schedules(
    students,
    master_timetable,
    section_capacity
)


# =====================================================
# EXPORT FILES
# =====================================================

export_all(
    students=students,
    section_to_block=master_timetable.section_to_block,
    blocks=list(range(8)),
    master_timetable=master_timetable,
    all_schedules=all_schedules,
    courses=courses,
    section_enrollment=section_enrollment
)

print("Export complete.")


# =====================================================
# METRICS
# =====================================================

# Student Metrics
request_completion = calculate_request_completion(students, all_schedules)
# % of students with 8/8 requested courses placed
count_8_of_8 = 0
id_8_of_8_students = []
for s in students:
    sched = all_schedules.get(s.id, {})
    placed = sum(1 for c in s.main_courses if c in sched)
    if len(s.main_courses) == 8 and placed == 8:
        count_8_of_8 += 1
        id_8_of_8_students.append(s.id)

percent_8_of_8 = (count_8_of_8 / len(students)) * 100 if students else 0

# % of students with >=50% of requested courses placed
count_half_or_more = 0
for s in students:
    sched = all_schedules.get(s.id, {})
    placed = sum(1 for c in s.main_courses if c in sched)
    total = len(s.main_courses) if len(s.main_courses) > 0 else 1
    if (placed / total) >= 0.5:
        count_half_or_more += 1

percent_half_or_more = (count_half_or_more / len(students)) * 100 if students else 0
# full_schedules = calculate_full_schedules(students, all_schedules)
# half_full_schedules = calculate_half_full_schedules(students, all_schedules)
seven_to_eight_requested = calculate_7_to_8_requested_percent(students, all_schedules)
eight_of_eight_with_alternates = calculate_8_of_8_with_alternates_percent(students, all_schedules)
students_with_conflicts = calculate_students_with_conflicts(all_schedules)
unassigned_requests = calculate_unassigned_requests(students, all_schedules)

# Enrollment Metrics
section_enrollment_metric = calculate_section_enrollment(section_enrollment)
total_sections = calculate_total_sections(master_timetable.sections)
full_sections = calculate_full_sections(master_timetable.sections, section_enrollment, section_capacity)
under_half_sections = calculate_under_half_sections(master_timetable.sections, section_enrollment, section_capacity)

# Timetable Metrics
room_conflicts = calculate_room_conflicts(master_timetable.sections, master_timetable.section_to_block)
student_conflicts = calculate_student_conflicts(all_schedules)
invalid_room_assignments = calculate_invalid_room_assignments(master_timetable.sections)
block_distribution = calculate_block_distribution(master_timetable.section_to_block)
blocking_rule_success = calculate_blocking_rule_success_percent(master_timetable.course_to_sections, master_timetable.section_to_block)


# Optimization Score
optimization_score = calculate_optimization_score(
    students,
    all_schedules,
    master_timetable.sections,
    section_enrollment,
    section_capacity,
    master_timetable.section_to_block
)

print("--- Student Metrics ---")
print(f"Request Completion: {request_completion:.2f}%")
print(f"Full Schedules: {percent_8_of_8:.2f}%")
print(f"Half-Full Schedules: {percent_half_or_more:.2f}%")
print(f"7-8/8 Requested Courses: {seven_to_eight_requested:.2f}%")
print(f"8/8 Courses (with Alternates): {eight_of_eight_with_alternates:.2f}%")
print(f"Students with Timetable Conflicts: {students_with_conflicts}")
print(f"Unassigned Course Requests: {unassigned_requests}")
print(f"Students with 8/8 requested courses placed: {id_8_of_8_students}")

print("\n--- Enrollment Metrics ---")
print(f"Total Number of Sections: {total_sections}")
print(f"Full Sections: {full_sections}")
print(f"Sections Below 50% Enrollment: {under_half_sections}")
# print(f"Section Enrollment: {section_enrollment_metric}") # This can be very long

print("\n--- Timetable Metrics ---")
print(f"Room Conflicts: {room_conflicts}")
print(f"Student Conflicts: {student_conflicts}")
print(f"Invalid Room Assignments: {invalid_room_assignments}")
print(f"Block Distribution: {block_distribution}")
print(f"Blocking Rule Success: {blocking_rule_success:.2f}%")

print(f"\nOptimization Score: {optimization_score}")