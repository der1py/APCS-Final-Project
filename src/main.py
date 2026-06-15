import time

from data.data_loader import load_courses_from_json, load_students
from output_scripts.export import export_all
from output_scripts.metrics_report import print_metrics_report
from solver.master_timetable_builder import build_master_timetable
from solver.student_timetable_cpsat import build_student_timetables
from timetable_cache import save_student_timetable_result
from validator import validate_courses, validate_students


# =====================================================
# LOAD DATA
# =====================================================

students = load_students()
courses = load_courses_from_json()


# =====================================================
# VALIDATION
# =====================================================

valid_courses, invalid_courses = validate_courses(courses)

students = validate_students(
    students,
    valid_courses,
)

courses = list(valid_courses.values())


# =====================================================
# MASTER TIMETABLE
# =====================================================

start_time = time.perf_counter()
master_timetable = build_master_timetable(
    students,
    courses,
)

course_lookup = {
    course.code: course
    for course in courses
}


# =====================================================
# STUDENT ASSIGNMENTS
# =====================================================

all_schedules, section_enrollment = build_student_timetables(
    students,
    master_timetable,
    course_lookup,
)

save_student_timetable_result(
    all_schedules,
    section_enrollment,
)

runtime_seconds = time.perf_counter() - start_time


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
    section_enrollment=section_enrollment,
)

print("Export complete.")


# =====================================================
# METRICS
# =====================================================

print_metrics_report(
    students=students,
    courses=courses,
    master_timetable=master_timetable,
    all_schedules=all_schedules,
    section_enrollment=section_enrollment,
    runtime_seconds=runtime_seconds,
)
