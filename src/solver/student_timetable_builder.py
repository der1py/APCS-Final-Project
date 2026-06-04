# This module builds the student timetables based on the master timetable.
from collections import defaultdict
from models.course import Course
from models.student import Student
from solver.master_timetable_builder import MasterTimetable
import math

# =====================================================
# SINGLE STUDENT SCHEDULE
# =====================================================


def _get_section_blocks(section):
    occupied = getattr(section, "occupied_blocks", None)
    if occupied:
        return list(occupied)
    return [section.time_slot]


def generate_student_schedule(student: Student, master_timetable: MasterTimetable, section_enrollment, section_capacity=None):

    chosen = {}
    used_blocks = set()

    ordered_courses = sorted(
        student.main_courses,
        key=lambda course_code: 0 if master_timetable.course_lookup.get(course_code, None) and master_timetable.course_lookup[course_code].linear else 1
    )

    for course_code in ordered_courses:

        possible_sections = master_timetable.course_to_sections.get(course_code, [])

        if not possible_sections:
            print(f"Could not place {student.id} into {course_code}")
            continue

        # Most filled first
        # NOTE: least filled first to balance
        possible_sections = sorted(
            possible_sections,
            key=lambda s: section_enrollment[s.id]
        )

        assigned = False

        for sec in possible_sections:

            section_blocks = _get_section_blocks(sec)

            # conflict
            if any(block in used_blocks for block in section_blocks):
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
            chosen[course_code] = (sec.id, section_blocks)

            used_blocks.update(section_blocks)
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
            for sec_id, blocks in schedule.values()
            if sec_id not in cancelled_sections
            for block in (blocks if isinstance(blocks, list) else [blocks])
        }

        for course_code in list(schedule.keys()):

            current_section_id, current_blocks = schedule[course_code]

            if current_section_id not in cancelled_sections:
                continue

            alternatives = (
                master_timetable.course_to_sections[
                    course_code
                ]
            )

            replacement = None
            replacement_blocks = []

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

                section_blocks = _get_section_blocks(sec)
                if any(block in used_blocks for block in section_blocks):
                    continue

                replacement = sec
                replacement_blocks = section_blocks
                break

            if replacement:

                section_enrollment[current_section_id] -= 1

                section_enrollment[replacement.id] += 1

                schedule[course_code] = (
                    replacement.id,
                    replacement_blocks
                )

                used_blocks.update(replacement_blocks)

            else:

                print(
                    f"Could not reassign "
                    f"{student_id} "
                    f"for {course_code}"
                )