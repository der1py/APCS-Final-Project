from collections import defaultdict
from models.course import Course
from models.student import Student
from solver.master_timetable_builder import MasterTimetable
import math

# =====================================================
# SINGLE STUDENT SCHEDULE
# =====================================================

def generate_student_schedule(student: Student, master_timetable: MasterTimetable, section_enrollment, section_capacity=None):

    chosen = {}
    used_blocks = set()

    for course_code in student.main_courses:

        possible_sections = (master_timetable.course_to_sections[course_code])

        # Most filled first
        possible_sections = sorted(
            possible_sections,
            key=lambda s: section_enrollment[s.id],
            reverse=True
        )

        assigned = False

        for sec in possible_sections:

            block = sec.time_slot

            # conflict
            if block in used_blocks:
                continue

            # capacity check
            if section_capacity:

                if (
                    section_enrollment[sec.id]
                    >= section_capacity.get(
                        sec.id,
                        999999
                    )
                ):
                    continue

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

def generate_all_student_schedules(students, master_timetable, section_capacity):

    all_schedules = {}

    section_enrollment = defaultdict(int)

    for student in students:
        sched = generate_student_schedule(student, master_timetable, section_enrollment, section_capacity)
        all_schedules[student.id] = sched

    return all_schedules, section_enrollment

# =====================================================
# CANCEL UNDERFILLED SECTIONS
# =====================================================

def find_underfilled_sections(
    master_timetable,
    section_enrollment,
    course_lookup
):

    cancelled = []

    for sec in master_timetable.sections:

        course = course_lookup[sec.course_code]

        enrolled = section_enrollment[sec.id]

        minimum = math.ceil(course.enrollment_max * 0.5)

        if enrolled < minimum:

            cancelled.append(sec.id)

    return cancelled

# =====================================================
# REASSIGN CANCELLED SECTIONS
# =====================================================

def reassign_cancelled_sections(

    all_schedules,
    cancelled_sections,
    master_timetable,
    section_enrollment,
    section_capacity

):

    for student_id, schedule in all_schedules.items():

        used_blocks = {
            block
            for sec, block in schedule.values()
            if sec.id not in cancelled_sections
        }

        for course_code in list(schedule.keys()):

            current_sec, current_block = schedule[course_code]

            if current_sec.id not in cancelled_sections:
                continue

            alternatives = (
                master_timetable.course_to_sections[
                    course_code
                ]
            )

            replacement = None

            for sec in alternatives:

                if sec.id in cancelled_sections:
                    continue

                if (
                    section_enrollment[sec.id]
                    >= section_capacity.get(
                        sec.id,
                        999999
                    )
                ):
                    continue

                if sec.time_slot in used_blocks:
                    continue

                replacement = sec
                break

            if replacement:

                section_enrollment[current_sec.id] -= 1

                section_enrollment[replacement.id] += 1

                schedule[course_code] = (
                    replacement,
                    replacement.time_slot
                )

                used_blocks.add(replacement.time_slot)

            else:

                print(
                    f"Could not reassign "
                    f"{student_id} "
                    f"for {course_code}"
                )