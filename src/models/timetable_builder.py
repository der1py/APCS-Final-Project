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
# NEW: NUMBER OF SECTIONS PER COURSE
# =====================================================

course_sections = {
    "Math": 3,
    "Physics": 2,
    "Music": 1,
    "CS": 1,
    "Art": 1
}

# =====================================================
# NEW: GENERATE SECTION NAMES
# =====================================================

sections = []

course_to_sections = defaultdict(list)

for course, count in course_sections.items():

    for i in range(1, count + 1):

        section_name = f"{course}_{i}"

        sections.append(section_name)

        course_to_sections[course].append(section_name)

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
# NEW:
# x[(section, block)]
# instead of x[(course, block)]
# =====================================================

x = {}

for s in sections:

    for b in blocks:

        x[(s, b)] = model.NewBoolVar(f"{s}_{b}")

# =====================================================
# CONSTRAINT:
# EACH SECTION EXACTLY ONE BLOCK
# =====================================================

for s in sections:

    model.Add(

        sum(x[(s, b)] for b in blocks) == 1

    )

# =====================================================
# NEW:
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

    sec1_list = course_to_sections[c1]
    sec2_list = course_to_sections[c2]

    for s1 in sec1_list:

        for s2 in sec2_list:

            for b in blocks:

                v = model.NewBoolVar(
                    f"same_{s1}_{s2}_{b}"
                )

                same_block[(s1, s2, b)] = v

                # v <= x1
                model.Add(
                    v <= x[(s1, b)]
                )

                # v <= x2
                model.Add(
                    v <= x[(s2, b)]
                )

                # v >= x1 + x2 - 1
                model.Add(
                    v >=
                    x[(s1, b)] +
                    x[(s2, b)] - 1
                )

# =====================================================
# OBJECTIVE:
# MINIMIZE CONFLICTS
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
# OUTPUT
# =====================================================

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:

    print("\nSECTION SCHEDULE:\n")

    for s in sections:

        for b in blocks:

            if solver.Value(x[(s, b)]):

                print(f"{s:12} -> Block {b}")

    print("\nTotal Conflict Cost:",
          solver.ObjectiveValue())

else:

    print("No solution found.")