from ortools.sat.python import cp_model
from collections import defaultdict
from itertools import combinations

from models.course import Course
from models.student import Student
from models.section import Section
from models.rules import Rules

# =====================================================
# INPUT DATA
# =====================================================

students = [
    Student(
        id=1,
        main_courses=["Math", "Physics", "Music"],
        alt_courses=[]
    ),
    Student(
        id=2,
        main_courses=["Math", "CS"],
        alt_courses=[]
    ),
    Student(
        id=3,
        main_courses=["Physics", "Art"],
        alt_courses=[]
    ),
    Student(
        id=4,
        main_courses=["Math", "Physics"],
        alt_courses=[]
    ),
    Student(
        id=5,
        main_courses=["CS", "Music"],
        alt_courses=[]
    )
]

blocks = list(range(8))

# =====================================================
# COURSE SECTIONS
# =====================================================

courses = [
    Course(code="MATH", name="Math", num_sections=3),
    Course(code="PHYS", name="Physics", num_sections=2),
    Course(code="MUSIC", name="Music", num_sections=1),
    Course(code="CS", name="CS", num_sections=1),
    Course(code="ART", name="Art", num_sections=1)
]

# =====================================================
# NEW:
# SECTION CAPACITY (ignore for milstone 1)
# =====================================================

section_capacity = {
    "Math_1": 2000,
    "Math_2": 2000,
    "Math_3": 2000,

    "Physics_1": 2000,
    "Physics_2": 2000,

    "Music_1": 3000,

    "CS_1": 2000,

    "Art_1": 2000
}

# =====================================================
# GENERATE SECTIONS
# =====================================================

sections = []
course_to_sections = defaultdict(list)

for course in courses:

    for i in range(1, course.num_sections + 1):

        sec_id = f"{course.code}_{i}"

        section = Section(
            id=sec_id,
            course_code=course.code,
            time_slot=-1  # CP-SAT will fill this later
        )

        sections.append(section)
        course_to_sections[course.code].append(section)

# =====================================================
# BUILD CONFLICT WEIGHTS
# =====================================================

conflict = defaultdict(int)

for student in students:
    course_list = student.main_courses

    for c1, c2 in combinations(course_list, 2):

        pair = tuple(sorted((c1, c2)))

        conflict[pair] += 1

# =====================================================
# CP-SAT MODEL
# =====================================================

model = cp_model.CpModel()

# =====================================================
# VARIABLES
# x[(section, block)]
# =====================================================

x = {}

for s in sections:

    for b in blocks:

        x[(s, b)] = model.NewBoolVar(f"{s}_{b}")

# =====================================================
# EACH SECTION EXACTLY ONE BLOCK
# =====================================================

for s in sections:

    model.Add(

        sum(x[(s, b)] for b in blocks) == 1

    )

# =====================================================
# SAME COURSE SECTIONS CANNOT SHARE BLOCK
# =====================================================

for course, sec_list in course_to_sections.items():

    for b in blocks:

        model.Add(

            sum(x[(s, b)] for s in sec_list) <= 1

        )

# =====================================================
# CONFLICT VARIABLES
# =====================================================

same_block = {}

for (c1, c2), weight in conflict.items():

    for s1 in course_to_sections[c1]:

        for s2 in course_to_sections[c2]:

            for b in blocks:

                v = model.NewBoolVar(
                    f"same_{s1}_{s2}_{b}"
                )

                same_block[(s1, s2, b)] = v

                model.Add(
                    v <= x[(s1, b)]
                )

                model.Add(
                    v <= x[(s2, b)]
                )

                model.Add(
                    v >=
                    x[(s1, b)] +
                    x[(s2, b)] - 1
                )

# =====================================================
# OBJECTIVE
# =====================================================

model.Minimize(

    sum(

        conflict[(c1, c2)] *

        same_block[(s1, s2, b)]

        for (c1, c2) in conflict

        for s1 in course_to_sections[c1]

        for s2 in course_to_sections[c2]

        for b in blocks

    )

)

# =====================================================
# SOLVE
# =====================================================

solver = cp_model.CpSolver()

status = solver.Solve(model)

# =====================================================
# STORE SECTION SCHEDULE
# =====================================================

section_to_block = {}

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:

    print("\nSECTION SCHEDULE:\n")

    for s in sections:

        for b in blocks:

            if solver.Value(x[(s, b)]):

                section_to_block[s] = b

                print(f"{s:12} -> Block {b}")

    print("\nTotal Conflict Cost:",
          solver.ObjectiveValue())

else:

    print("No solution found.")
    
# =====================================================
# EXPORT MASTER TIMETABLE TO CSV
# =====================================================

import csv

# build master timetable: block -> sections
master_timetable = {b: [] for b in blocks}

for sec, block in section_to_block.items():
    master_timetable[block].append(sec)

# write CSV
with open("master_timetable.csv", "w", newline="") as f:
    writer = csv.writer(f)

    # header row
    writer.writerow([f"Block {b}" for b in blocks])

    # max height across columns
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
# NEW:
# SECTION ENROLLMENT TRACKER
# =====================================================

section_enrollment = defaultdict(int)

# =====================================================
# NEW:
# GENERATE STUDENT TIMETABLE
# =====================================================

def generate_student_schedule(student_name):

    requested_courses = next (
        student.main_courses
        for student in students
        if student.id == student_name
    )

    chosen = {}

    used_blocks = set()

    for course in requested_courses:

        assigned = False

        possible_sections = course_to_sections[course.code]

        # sort by current enrollment
        possible_sections.sort(
            key=lambda s: section_enrollment[s]
        )

        for sec in possible_sections:

            block = section_to_block[sec]

            # avoid block conflict
            if block in used_blocks:
                continue

            # capacity check
            if (
                section_enrollment[sec]
                >=
                section_capacity[sec]
            ):
                continue

            # assign student
            chosen[course] = (
                sec,
                block
            )

            used_blocks.add(block)

            section_enrollment[sec] += 1

            assigned = True

            break

        if not assigned:

            print(
                f"\nCould not place "
                f"{student_name} into {course}"
            )

            # continue scheduling other courses
            continue

    return chosen

# =====================================================
# NEW:
# GENERATE ALL STUDENT TIMETABLES
# =====================================================

all_schedules = {}

for student in students:

    sched = generate_student_schedule(student.id)

    all_schedules[student.id] = sched

# =====================================================
# PRINT TIMETABLES
# =====================================================

print("\n========================")
print("STUDENT TIMETABLES")
print("========================\n")

for student, sched in all_schedules.items():

    print(f"{student}:")

    if len(sched) == 0:

        print("  No courses assigned\n")

        continue

    for course, (sec, block) in sched.items():

        print(
            f"  {course:10}"
            f"{sec:12}"
            f"Block {block}"
        )

    print()

# =====================================================
# PRINT FINAL ENROLLMENTS
# =====================================================

print("========================")
print("SECTION ENROLLMENTS")
print("========================\n")

for sec in sections:

    print(
        f"{sec:12}"
        f"{section_enrollment[sec]}"
        f"/"
        f"{section_capacity[sec]}"
    )