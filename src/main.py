from data.data_loader import load_students, load_courses
<<<<<<< HEAD
from solver.master_timetable_builder import build_master_timetable
from solver.student_timetable_builder import generate_all_student_schedules
from output.output_scripts.metrics import calculate_request_completion
from output.output_scripts.export import export_all
=======

from solver.master_timetable_builder import build_master_timetable

from solver.student_timetable_builderr import generate_all_student_schedules

from validator import validate_courses, validate_students

from output.metrics import calculate_request_completion
>>>>>>> c5c4dd9daab7fb8fbc5850cc30e827b9dd1e57e7

students = load_students()

courses = load_courses()

# =====================================================
# VALIDATION
# =====================================================

valid_courses, invalid_courses = (
    validate_courses(courses)
)

students = validate_students(
    students,
    valid_courses
)

courses = list(valid_courses.values())

course_name_map = {
    course.code: course.name
    for course in courses
}

# =====================================================
# MASTER TIMETABLE
# =====================================================

master_timetable = build_master_timetable(
    students,
    courses
)

# =====================================================
# STUDENT ASSIGNMENTS
# =====================================================

all_schedules, section_enrollment = (
    generate_all_student_schedules(
        students,
        master_timetable
    )
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

export_all(
    students=students,
    section_to_block=master_timetable.section_to_block,
    blocks=(range(8)),
    master_timetable=master_timetable,
    all_schedules=all_schedules
)