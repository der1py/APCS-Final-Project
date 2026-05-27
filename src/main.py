from data_loader import load_students, load_courses

from master_timetable_builder import build_master_timetable

from student_scheduler import generate_all_student_schedules


from metrics import calculate_request_completion

students = load_students()

courses = load_courses()

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