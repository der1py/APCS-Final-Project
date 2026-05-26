from ortools.sat.python import cp_model
from collections import defaultdict
from itertools import combinations

# =====================================================
# INPUT DATA
# =====================================================

students = {
    "S1": ["Math", "Physics", "Music"],
    "S2": ["Math", "CS"],
    "S3": ["Physics", "Art"],
    "S4": ["Math", "Physics"],
    "S5": ["CS", "Music"]
}

blocks = ["A", "B", "C", "D"]

# =====================================================
# COURSE SECTIONS
# =====================================================

course_sections = {
    "Math": 3,
    "Physics": 2,
    "Music": 1,
    "CS": 1,
    "Art": 1
}

# =====================================================
# NEW:
# SECTION CAPACITY
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

for course, count in course_sections.items():

    for i in range(1, count + 1):

        sec = f"{course}_{i}"

        sections.append(sec)

        course_to_sections[course].append(sec)

# =====================================================
# BUILD CONFLICT WEIGHTS
# =====================================================

conflict = defaultdict(int)

for course_list in students.values():

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

        x[(s.id, b)] = model.NewBoolVar(f"{s.id}_{b}")

# =====================================================
# EACH SECTION EXACTLY ONE BLOCK
# =====================================================

for s in sections:

    model.Add(

        sum(x[(s.id, b)] for b in blocks) == 1

    )

# =====================================================
# SAME COURSE SECTIONS CANNOT SHARE BLOCK
# =====================================================

for course, sec_list in course_to_sections.items():

    for b in blocks:

        model.Add(

            sum(x[(s.id, b)] for s in sec_list) <= 1

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
                    f"same_{s1.id}_{s2.id}_{b}"
                )

                same_block[(s1.id, s2.id, b)] = v

                model.Add(
                    v <= x[(s1.id, b)]
                )

                model.Add(
                    v <= x[(s2.id   , b)]
                )

                model.Add(
                    v >=
                    x[(s1.id, b)] +
                    x[(s2.id, b)] - 1
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

            if solver.Value(x[(s.id, b)]):

                section_to_block[s] = b

                print(f"{s:12} -> Block {b}")

    print("\nTotal Conflict Cost:",
          solver.ObjectiveValue())

else:

    print("No solution found.")

# =====================================================
# NEW:
# SECTION ENROLLMENT TRACKER
# =====================================================

section_enrollment = defaultdict(int)

# =====================================================
# NEW:
# GENERATE STUDENT TIMETABLE
# =====================================================
unplaced_courses = {}
def generate_student_schedule(student_name):

    requested_courses = students[student_name]

    chosen = {}

    used_blocks = set()

    # initialize student list
    unplaced_courses[student_name] = []

    for course in requested_courses:

        assigned = False

        possible_sections = course_to_sections[course]

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
            unplaced_courses[student_name].append(course)
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

    sched = generate_student_schedule(student)

    all_schedules[student] = sched

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