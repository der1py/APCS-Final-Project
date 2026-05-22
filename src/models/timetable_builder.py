from ortools.sat.python import cp_model
from collections import defaultdict
from itertools import combinations

# -------------------------
# Input Data
# -------------------------

students = {
    "S1": ["Math", "Physics", "Music"],
    "S2": ["Math", "CS", "Art", "Physics"],
    "S3": ["Physics", "Art"],
    "S4": ["Math", "Physics"],
    "S5": ["CS", "Music"]
}

blocks = ["A", "B", "C", "D"]

# -------------------------
# Build course list
# -------------------------

courses = set()

for course_list in students.values():
    for c in course_list:
        courses.add(c)

courses = list(courses)

# -------------------------
# Build conflict weights
# -------------------------

# conflict[(c1,c2)] = number of shared students

conflict = defaultdict(int)

for course_list in students.values():

    for c1, c2 in combinations(course_list, 2):

        pair = tuple(sorted((c1, c2)))

        conflict[pair] += 1

# -------------------------
# CP-SAT Model
# -------------------------

model = cp_model.CpModel()

# x[(course, block)] = 1 if course assigned to block

x = {}

for c in courses:
    for b in blocks:
        x[(c, b)] = model.NewBoolVar(f"{c}_{b}")

# -------------------------
# Constraint:
# each course exactly one block
# -------------------------

for c in courses:

    model.Add(
        sum(x[(c, b)] for b in blocks) == 1
    )

# -------------------------
# Conflict variables
# -------------------------

same_block = {}

for (c1, c2), weight in conflict.items():

    for b in blocks:

        v = model.NewBoolVar(f"same_{c1}_{c2}_{b}")

        same_block[(c1, c2, b)] = v

        # v = 1 iff both courses in same block

        model.AddBoolAnd([
            x[(c1, b)],
            x[(c2, b)]
        ]).OnlyEnforceIf(v)

        model.AddImplication(v, x[(c1, b)])
        model.AddImplication(v, x[(c2, b)])

        model.AddBoolOr([
            x[(c1, b)].Not(),
            x[(c2, b)].Not(),
            v
        ])

# -------------------------
# Objective:
# minimize student conflicts
# -------------------------

model.Minimize(

    sum(
        weight * same_block[(c1, c2, b)]

        for (c1, c2), weight in conflict.items()

        for b in blocks
    )

)

# -------------------------
# Solve
# -------------------------

solver = cp_model.CpSolver()

status = solver.Solve(model)

# -------------------------
# Output
# -------------------------

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:

    print("\nCourse Schedule:\n")

    for c in courses:

        for b in blocks:

            if solver.Value(x[(c, b)]):

                print(f"{c:10} -> Block {b}")

    print("\nTotal Conflict Cost:",
          solver.ObjectiveValue())

else:
    print("No solution found.")

def score_difficulty(enrollment, slot):
    return enrollment / slot