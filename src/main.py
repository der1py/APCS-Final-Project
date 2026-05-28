from data.data_loader import load_students, load_courses

from solver.master_timetable_builder import build_master_timetable

from solver.student_timetable_builderr import generate_all_student_schedules

from validator import validate_courses, validate_students

from output.metrics import calculate_request_completion

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