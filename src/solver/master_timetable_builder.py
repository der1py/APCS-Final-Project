# This module builds the master timetable using CP-SAT.
import sys

from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations

from ortools.sat.python import cp_model

from models.section import Section

from data.data_loader import load_simultaneous_blocking_rules

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
    # LOAD SIMULTANEOUS BLOCKING RULES
    # =================================================

    blocking_rules = load_simultaneous_blocking_rules()

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
        s.id: s
        for s in sections
    }

    course_lookup = {
        c.code: c
        for c in courses
    }

    all_rooms = sorted({
        room
        for c in courses
        for room in c.rooms
    })

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
    y = {}

    for s in sections:

        # block variables
        for b in blocks:

            x[(s.id, b)] = model.NewBoolVar(
                f"block_{s.id}_{b}"
            )

        # room variables
        course = course_lookup[
            s.course_code
        ]

        for room in course.rooms:

            y[(s.id, room)] = model.NewBoolVar(
                f"room_{s.id}_{room}"
            )

    # =================================================
    # EACH SECTION EXACTLY ONE BLOCK
    # =================================================

    for s in sections:

        model.Add(
            sum(x[(s.id, b)] for b in blocks) == 1
        )

    # =================================================
    # EACH SECTION EXACTLY ONE ROOM
    # =================================================

    for s in sections:

        course = course_lookup[
            s.course_code
        ]

        model.Add(

            sum(
                y[(s.id, room)]
                for room in course.rooms
            )

            == 1
        )

    # =====================================================
    # SAME COURSE SECTIONS CANNOT SHARE BLOCK
    # =====================================================

    # TODO this is literally bullshit, 2 teachers can teach the same class in same block
    # for course, sec_list in course_to_sections.items():
    #     for b in blocks:
    #         model.Add(sum(x[(s.id, b)] for s in sec_list) <= 1)

    # =================================================
    # ROOM CONSTRAINTS
    # =================================================

    print(
        f"Sections: {len(sections)}"
    )

    print(
        f"Rooms: {len(all_rooms)}"
    )

    print(
        f"Max sections per block <= {len(all_rooms)}"
    )

    for room in all_rooms:

        room_sections = [

            s

            for s in sections

            if room in course_lookup[
                s.course_code
            ].rooms

        ]

        for block in blocks:

            room_block_vars = []

            for s in room_sections:

                v = model.NewBoolVar(
                    f"use_{s.id}_{room}_{block}"
                )

                model.Add(
                    v <= x[(s.id, block)]
                )

                model.Add(
                    v <= y[(s.id, room)]
                )

                model.Add(
                    v >=
                    x[(s.id, block)]
                    +
                    y[(s.id, room)]
                    - 1
                )

                room_block_vars.append(v)

            model.Add(
                sum(room_block_vars)
                <= 1
            )

    # =================================================
    # SOFT BLOCK BALANCE
    # =================================================

    target = len(sections) // len(blocks)

    balance_penalties = []

    for b in blocks:

        count = sum(
            x[(s.id, b)]
            for s in sections
        )

        diff = model.NewIntVar(
            -len(sections),
            len(sections),
            f"balance_diff_{b}"
        )

        deviation = model.NewIntVar(
            0,
            len(sections),
            f"balance_dev_{b}"
        )

        model.Add(
            diff == count - target
        )

        model.AddAbsEquality(
            deviation,
            diff
        )

        balance_penalties.append(
            deviation
        )

    # =================================================
    # SIMULTANEOUS BLOCKING CONSTRAINTS
    # =================================================

    print("\nADDING SIMULTANEOUS BLOCKING RULES...\n")

    for blocking_type, pairs in blocking_rules.items():

        print(f"Blocking Type: {blocking_type}")

        for c1, c2 in pairs:

            if c1 not in course_to_sections:
                print(f"Missing course: {c1}")
                continue

            if c2 not in course_to_sections:
                print(f"Missing course: {c2}")
                continue

            sec_list_1 = course_to_sections[c1]
            sec_list_2 = course_to_sections[c2]

            # =================================================
            # FORCE SAME BLOCK
            # =================================================

            min_len = min(
                len(sec_list_1),
                len(sec_list_2)
            )

            for i in range(min_len):

                s1 = sec_list_1[i]
                s2 = sec_list_2[i]

                for b in blocks:

                    model.Add(
                        x[(s1.id, b)] ==
                        x[(s2.id, b)]
                    )

    # =================================================
    # CONFLICT VARIABLES
    # =================================================

    same_block = {}

    for (c1, c2), weight in conflict.items():

        if c1 not in course_to_sections:
            continue

        if c2 not in course_to_sections:
            continue

        for s1 in course_to_sections[c1]:

            for s2 in course_to_sections[c2]:

                # skip same-course comparisons
                if s1.course_code == s2.course_code:
                    continue

                for b in blocks:

                    v = model.NewBoolVar(
                        f"same_{s1.id}_{s2.id}_{b}"
                    )

                    same_block[(s1.id, s2.id, b)] = v

                    model.Add(
                        v <= x[(s1.id, b)]
                    )

                    model.Add(
                        v <= x[(s2.id, b)]
                    )

                    model.Add(
                        v >=
                        x[(s1.id, b)] +
                        x[(s2.id, b)] - 1
                    )

    # =================================================
    # OBJECTIVE
    # =================================================

    conflict_cost = sum(

        conflict[(c1, c2)]
        *
        same_block[(s1.id, s2.id, b)]

        for (c1, c2) in conflict

        if c1 in course_to_sections
        and c2 in course_to_sections

        for s1 in course_to_sections[c1]
        for s2 in course_to_sections[c2]

        if s1.course_code != s2.course_code

        for b in blocks
    )

    BALANCE_WEIGHT = 100

    model.Minimize(

        conflict_cost

        +

        BALANCE_WEIGHT
        *
        sum(balance_penalties)

    )


    # =================================================
    # SOLVE
    # =================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    # =================================================
    # SECTION TO BLOCK MAP
    # =================================================

    section_to_block = {}

    if status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        print("\nSECTION SCHEDULE:\n")

        for s in sections:

            for b in blocks:

                if solver.Value(x[(s.id, b)]):

                    section_to_block[s.id] = b

                    s.time_slot = b

                    for room in course_lookup[
                        s.course_code
                    ].rooms:

                        if solver.Value(
                            y[(s.id, room)]
                        ):

                            s.room_id = room
                            break

                    print(
                        f"{s.id:15}"
                        f" Block {s.time_slot}"
                        f" Room {s.room_id}"
                    )

        print(
            "\nTotal Conflict Cost:",
            solver.ObjectiveValue()
        )

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