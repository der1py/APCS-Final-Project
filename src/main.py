from data.data_loader import load_students, load_courses

from solver.master_timetable_builder import build_master_timetable
from solver.room_assigner import assign_rooms
from solver.student_timetable_builder import generate_all_student_schedules

from validator import validate_courses, validate_students

from output.output_scripts.metrics import calculate_request_completion
from output.output_scripts.export import export_all

from output.output_scripts.metrics import (
    calculate_request_completion,
    calculate_optimization_score,
)


# =====================================================
# LOAD DATA
# =====================================================

students = load_students()
courses = load_courses()


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

# assign rooms to scheduled sections before student placement/export
course_lookup = {
    course.code: course
    for course in courses
}

assign_rooms(master_timetable, course_lookup)

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
# METRICS
# =====================================================

print(
    calculate_request_completion(
        students,
        all_schedules
    )
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
    courses=courses
)

print("Export complete.")

# METRICS, CLEAN UP LATER

# Additional requested metrics
req_completion = calculate_request_completion(students, all_schedules)

# % of students with 8/8 requested courses placed
count_8_of_8 = 0
for s in students:
    sched = all_schedules.get(s.id, {})
    placed = sum(1 for c in s.main_courses if c in sched)
    if len(s.main_courses) == 8 and placed == 8:
        count_8_of_8 += 1

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

# Optimization score (pass empty capacity dict)
opt_score = calculate_optimization_score(
    students,
    all_schedules,
    master_timetable.sections,
    section_enrollment,
    {},
    master_timetable.section_to_block
)

print(f"Request completion: {req_completion:.2f}%")
print(f"Students with 8/8 placed: {percent_8_of_8:.2f}%")
print(f"Students with >=50% placed: {percent_half_or_more:.2f}%")
print(f"Optimization score: {opt_score}")