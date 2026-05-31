from data.data_loader import load_students
from data.course_loader import load_courses_from_csv

from solver.master_timetable_builder import build_master_timetable
from solver.student_timetable_builder import generate_all_student_schedules

from validator import validate_courses, validate_students

from output.output_scripts.metrics import calculate_request_completion
from output.output_scripts.export import export_all


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