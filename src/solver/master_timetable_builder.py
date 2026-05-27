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

    section_by_id = {
        s.id: s for s in sections
    }

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

    # =================================================
    # BALANCED BLOCKS
    # =================================================

    num_sections = len(sections)

    num_blocks = len(blocks)

    base = num_sections // num_blocks

    remainder = num_sections % num_blocks

    block_counts = {}

    for b in blocks:

        block_counts[b] = sum(
            x[(s.id, b)] for s in sections
        )

    for b in blocks:

        upper = base + (
            1 if b < remainder else 0
        )

        model.Add(block_counts[b] <= upper)

        model.Add(block_counts[b] >= base)

    # =================================================
    # SOLVE
    # =================================================

    solver = cp_model.CpSolver()

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        raise Exception(
            "No feasible master timetable found."
        )

    # =================================================
    # EXTRACT SOLUTION
    # =================================================

    section_to_block = {}

    for s in sections:

        for b in blocks:

            if solver.Value(x[(s.id, b)]):

                section_to_block[s.id] = b

                # IMPORTANT
                s.time_slot = b

    # =================================================
    # RETURN OBJECT
    # =================================================

    return MasterTimetable(
        sections=sections,
        section_to_block=section_to_block,
        course_to_sections=course_to_sections,
        section_by_id=section_by_id
    )