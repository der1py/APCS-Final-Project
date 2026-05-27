import sys

from ortools.sat.python import cp_model
from collections import defaultdict
from itertools import combinations
import csv

from models.course import Course
from models.student import Student
from models.section import Section

from data_loader import load_students, load_courses, load_rules

import os
from datetime import datetime

# =====================================================
# log any issues
# =====================================================

LOG_FILE = "invalid_data.log"

def log_issue(msg: str):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

# =====================================================
# INPUT DATA
# =====================================================

students = load_students()

blocks = list(range(8))

courses = load_courses()

# =====================================================
# DATA VALIDATION
# =====================================================

valid_courses = {}
invalid_courses = set()

for c in courses:
    if not hasattr(c, "code") or not hasattr(c, "num_sections"):
        log_issue(f"INVALID COURSE OBJECT: {c}")
        continue

    if c.num_sections <= 0:
        log_issue(f"COURSE HAS ZERO SECTIONS: {c.code}")
        invalid_courses.add(c.code)
        continue

    valid_courses[c.code] = c


# FILTER STUDENTS
valid_students = []

for s in students:

    if not hasattr(s, "main_courses"):
        log_issue(f"INVALID STUDENT OBJECT: {s}")
        continue

    cleaned_courses = []

    for c in s.main_courses:
        if c not in valid_courses:
            log_issue(f"{s.id}: INVALID COURSE REQUEST -> {c}")
            continue
        cleaned_courses.append(c)

    if not cleaned_courses:
        log_issue(f"{s.id}: HAS NO VALID COURSES AFTER CLEANING")
        continue

    s.main_courses = cleaned_courses
    valid_students.append(s)


students = valid_students
courses = list(valid_courses.values())

course_name_map = {course.code: course.name for course in courses}

# =====================================================
# SECTION CAPACITY
# =====================================================

section_capacity = {
    "MATH_1": 2000,
    "MATH_2": 2000,
    "MATH_3": 2000,
    "PHYS_1": 2000,
    "PHYS_2": 2000,
    "MUSIC_1": 3000,
    "CS_1": 2000,
    "ART_1": 2000
}


# =====================================================
# GENERATE SECTIONS
# =====================================================

sections = []
course_to_sections = defaultdict(list)

for course in courses:
    for i in range(1, course.num_sections + 1):

        sec_id = f"{course.code}_{i}"

        sec = Section(
            id=sec_id,
            course_code=course.code,
            time_slot=-1
        )

        sections.append(sec)
        course_to_sections[course.code].append(sec)


# lookup table (IMPORTANT)
section_by_id = {s.id: s for s in sections}


# =====================================================
# CONFLICT WEIGHTS
# =====================================================

conflict = defaultdict(int)

for student in students:
    for c1, c2 in combinations(student.main_courses, 2):
        pair = tuple(sorted((c1, c2)))
        conflict[pair] += 1


# =====================================================
# CP-SAT MODEL
# =====================================================

model = cp_model.CpModel()

x = {}

for s in sections:
    for b in blocks:
        x[(s.id, b)] = model.NewBoolVar(f"{s.id}_{b}")


# =====================================================
# EACH SECTION EXACTLY ONE BLOCK
# =====================================================

for s in sections:
    model.Add(sum(x[(s.id, b)] for b in blocks) == 1)


# =====================================================
# SAME COURSE SECTIONS CANNOT SHARE BLOCK
# =====================================================

# TODO this is literally bullshit, 2 teachers can teach the same class in same block
# for course, sec_list in course_to_sections.items():
#     for b in blocks:
#         model.Add(sum(x[(s.id, b)] for s in sec_list) <= 1)

# =====================================================
# BALANCED SECTIONS PER BLOCK
# =====================================================

num_sections = len(sections)
num_blocks = len(blocks)

base = num_sections // num_blocks
remainder = num_sections % num_blocks

block_counts = {}

for b in blocks:
    block_counts[b] = sum(x[(s.id, b)] for s in sections)

for b in blocks:
    # first 'remainder' blocks get +1
    upper_bound = base + (1 if b < remainder else 0)

    model.Add(block_counts[b] <= upper_bound)
    model.Add(block_counts[b] >= base)

# =====================================================
# CONFLICT VARIABLES
# =====================================================

# TODO fix later

# same_block = {}

# for (c1, c2), weight in conflict.items():

#     for s1 in course_to_sections[c1]:
#         for s2 in course_to_sections[c2]:
#             for b in blocks:

#                 v = model.NewBoolVar(f"same_{s1.id}_{s2.id}_{b}")
#                 same_block[(s1.id, s2.id, b)] = v

#                 model.Add(v <= x[(s1.id, b)])
#                 model.Add(v <= x[(s2.id, b)])
#                 model.Add(v >= x[(s1.id, b)] + x[(s2.id, b)] - 1)

# model.Minimize(
#     sum(
#         conflict[(c1, c2)] *
#         same_block[(s1.id, s2.id, b)]

#         for (c1, c2) in conflict
#         for s1 in course_to_sections[c1]
#         for s2 in course_to_sections[c2]
#         for b in blocks
#     )
# )


# =====================================================
# SOLVE
# =====================================================

solver = cp_model.CpSolver()
status = solver.Solve(model)


# =====================================================
# SECTION TO BLOCK MAP
# =====================================================

section_to_block = {}

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):

    print("\nSECTION SCHEDULE:\n")

    for s in sections:
        for b in blocks:
            if solver.Value(x[(s.id, b)]):

                section_to_block[s.id] = b
                print(f"{s.id:12} -> Block {b}")

    print("\nTotal Conflict Cost:", solver.ObjectiveValue())

else:
    print("No solution found.")
    sys.exit() # <-- THIS STOPS THE SCRIPT FROM CRASHING LATER


# =====================================================
# EXPORT MASTER TIMETABLE
# =====================================================

master_timetable = {b: [] for b in blocks}

for sec_id, block in section_to_block.items():
    course_code = section_by_id[sec_id].course_code
    course_name = course_name_map.get(course_code, course_code)
    master_timetable[block].append(course_name)

with open("master_timetable.csv", "w", newline="") as f:
    writer = csv.writer(f)

    writer.writerow([f"Block {b}" for b in blocks])

    max_rows = max(len(master_timetable[b]) for b in blocks)

    for i in range(max_rows):
        row = []
        for b in blocks:
            if i < len(master_timetable[b]):
                row.append(master_timetable[b][i])
            else:
                row.append("")
        writer.writerow(row)


# =====================================================
# SECTION ENROLLMENT
# =====================================================

section_enrollment = defaultdict(int)

# sys.exit(); # TODO skip student tt for now. maybe do in separte file?


def generate_student_schedule(student_id):

    student = next(s for s in students if s.id == student_id)

    chosen = {}
    used_blocks = set()

    for course_code in student.main_courses:

        possible_sections = course_to_sections[course_code]

        possible_sections.sort(
            key=lambda s: section_enrollment[s.id]
        )

        assigned = False

        for sec in possible_sections:

            block = section_to_block[sec.id]

            if block in used_blocks:
                continue
            
            # TODO skip for now
            # if section_enrollment[sec.id] >= section_capacity[sec.id]:
            #     continue

            chosen[course_code] = (sec, block)

            used_blocks.add(block)
            section_enrollment[sec.id] += 1

            assigned = True
            break

        if not assigned:
            print(f"Could not place {student_id} into {course_code}")

    return chosen


# =====================================================
# ALL STUDENT SCHEDULES
# =====================================================

all_schedules = {}

for student in students:
    all_schedules[student.id] = generate_student_schedule(student.id)


# =====================================================
# EXPORT STUDENT SCHEDULES
# =====================================================

with open("student_schedules.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Student"] + [f"Block {b}" for b in blocks])

    for student in students:
        schedule = all_schedules.get(student.id, {})
        row = [student.id] + ["unassigned" for _ in blocks]

        for course, (_, block) in schedule.items():
            if 0 <= block < len(blocks):
                row[block + 1] = course_name_map.get(course, course)

        writer.writerow(row)


# =====================================================
# PRINT STUDENTS
# =====================================================

print("\n========================")
print("STUDENT TIMETABLES")
print("========================\n")

for sid, sched in all_schedules.items():

    print(f"{sid}:")

    if not sched:
        print("  No courses assigned\n")
        continue

    for course, (sec, block) in sched.items():
        print(f"  {course:10}{sec.id:12}Block {block}")

    print()


# =====================================================
# PRINT ENROLLMENTS
# =====================================================

print("========================")
print("SECTION ENROLLMENTS")
print("========================\n")

for sec in sections:
    print(
        f"{sec.id:12}"
        f"{section_enrollment[sec.id]}"
        f"/"
        # f"{section_capacity[sec.id]}"
        f"unlimited"
    )

from metrics import calculate_optimization_score, calculate_request_completion, calculate_full_schedules, calculate_half_full_schedules

optimization_score = calculate_optimization_score(
    students,
    all_schedules,
    sections,
    section_enrollment,
    section_capacity,
    section_to_block
)

print("\n========================")
print("METRICS")
print("========================")

print(
    "Request Completion:",
    round(calculate_request_completion(
        students,
        all_schedules
    ), 2),
    "%"
)

print(
    "Full Timetables:",
    round(calculate_full_schedules(
        students,
        all_schedules
    ), 2),
    "%"
)

print(
    "Half Full Timetables:",
    round(calculate_half_full_schedules(
        students,
        all_schedules
    ), 2),
    "%"
)

print("Optimization Score:", optimization_score)
