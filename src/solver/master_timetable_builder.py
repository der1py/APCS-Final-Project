import sys

from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations

from ortools.sat.python import cp_model

from models.section import Section



# =====================================================
# MASTER TIMETABLE OBJECT
# =====================================================

@dataclass
class MasterTimetable:

    sections: list

    section_to_block: dict

    course_to_sections: dict

    section_by_id: dict


# =====================================================
# BUILD MASTER TIMETABLE
# =====================================================

def build_master_timetable(students, courses):

    blocks = list(range(8))

    # =================================================
    # GENERATE SECTIONS
    # =================================================

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

    section_by_id = {s.id: s for s in sections}

    # =================================================
    # CONFLICT MATRIX
    # =================================================

    conflict = defaultdict(int)

    for student in students:

        for c1, c2 in combinations(
            student.main_courses,
            2
        ):

            pair = tuple(sorted((c1, c2)))

            conflict[pair] += 1

    # =================================================
    # CP-SAT MODEL
    # =================================================

    model = cp_model.CpModel()

    x = {}

    for s in sections:
        for b in blocks:

            x[(s.id, b)] = model.NewBoolVar(
                f"{s.id}_{b}"
            )

    # =================================================
    # EACH SECTION EXACTLY ONE BLOCK
    # =================================================

    for s in sections:

        model.Add(
            sum(x[(s.id, b)] for b in blocks) == 1
        )

    # =====================================================
    # SAME COURSE SECTIONS CANNOT SHARE BLOCK
    # =====================================================

    # TODO this is literally bullshit, 2 teachers can teach the same class in same block
    # for course, sec_list in course_to_sections.items():
    #     for b in blocks:
    #         model.Add(sum(x[(s.id, b)] for s in sec_list) <= 1)

    # =================================================
    # BALANCED BLOCKS
    # =================================================

    num_sections = len(sections)
    num_blocks = len(blocks)

    base = num_sections // num_blocks
    remainder = num_sections % num_blocks

    block_counts = {}

    for b in blocks:

        block_counts[b] = sum(x[(s.id, b)] for s in sections)

    for b in blocks:
        # first 'remainder' blocks get +1
        upper = base + (1 if b < remainder else 0)

        model.Add(block_counts[b] <= upper)
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

    # =================================================
    # SOLVE
    # =================================================

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
                    s.timeslot = b 

        print("\nTotal Conflict Cost:", solver.ObjectiveValue())

    else:
        print("No solution found.")
        sys.exit() # <-- THIS STOPS THE SCRIPT FROM CRASHING LATER


    # =================================================
    # RETURN OBJECT
    # =================================================

    return MasterTimetable(
        sections=sections,
        section_to_block=section_to_block,
        course_to_sections=course_to_sections,
        section_by_id=section_by_id
    )