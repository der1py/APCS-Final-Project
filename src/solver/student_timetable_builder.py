from collections import defaultdict
from models.course import Course
from models.student import Student
from solver.master_timetable_builder import MasterTimetable

# =====================================================
# SINGLE STUDENT SCHEDULE
# =====================================================

def generate_student_schedule(student: Student, master_timetable: MasterTimetable, section_enrollment, section_capacity=None):

    chosen = {}
    used_blocks = set()

    for course_code in student.main_courses:

        possible_sections = (master_timetable.course_to_sections[course_code])

        # Least filled first
        possible_sections = sorted(possible_sections, key=lambda s: section_enrollment[s.id])

        assigned = False

        for sec in possible_sections:

            block = sec.time_slot

            # conflict
            if block in used_blocks:
                continue

            # TODO skip for now
            # if section_enrollment[sec.id] >= section_capacity[sec.id]:
            #     continue
            #
            # Chat's suggestion for capacity: 
            # # capacity
            # if section_capacity:

            #     if (
            #         section_enrollment[sec.id]
            #         >= section_capacity.get(
            #             sec.id,
            #             999999
            #         )
            #     ):
            #         continue

            # assign
            chosen[course_code] = (sec, block)

            used_blocks.add(block)
            section_enrollment[sec.id] += 1

            assigned = True
            break

        if not assigned:
            print(f"Could not place {student.id} into {course_code}")
    return chosen


# =====================================================
# ALL STUDENT SCHEDULES
# =====================================================

def generate_all_student_schedules(students, master_timetable, section_capacity=None):

    all_schedules = {}

    section_enrollment = defaultdict(int)

    for student in students:
        sched = generate_student_schedule(student, master_timetable, section_enrollment, section_capacity)
        all_schedules[student.id] = sched

    return all_schedules, section_enrollment