# This module builds the master timetable using CP-SAT.
import sys
import os

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

    # =================================================
    # SETUP
    # =================================================

    blocks = list(range(8))

    blocking_rules = load_simultaneous_blocking_rules()

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

    # Build simultaneous groups: sections grouped into atomic room-units.
    # Each section will belong to exactly one group; groups created from
    # simultaneous blocking rules, then remaining sections become singleton
    # groups so the room-constraint logic can be applied uniformly.

    sim_groups = {}           # group_id -> set(section_id)
    section_to_group = {}     # section_id -> group_id
    group_counter = 0

    for blocking_type, pairs in blocking_rules.items():

        for c1, c2 in pairs:

            if c1 not in course_to_sections:
                continue

            if c2 not in course_to_sections:
                continue

            sec_list_1 = course_to_sections[c1]
            sec_list_2 = course_to_sections[c2]

            min_len = min(
                len(sec_list_1),
                len(sec_list_2)
            )

            for i in range(min_len):

                s1 = sec_list_1[i]
                s2 = sec_list_2[i]

                g1 = section_to_group.get(s1.id)
                g2 = section_to_group.get(s2.id)

                if g1 is None and g2 is None:
                    gid = f"sim_{group_counter}"
                    group_counter += 1
                    sim_groups[gid] = {s1.id, s2.id}
                    section_to_group[s1.id] = gid
                    section_to_group[s2.id] = gid

                elif g1 is not None and g2 is None:
                    sim_groups[g1].add(s2.id)
                    section_to_group[s2.id] = g1

                elif g1 is None and g2 is not None:
                    sim_groups[g2].add(s1.id)
                    section_to_group[s1.id] = g2

                elif g1 != g2:
                    # merge groups g2 into g1
                    for sid in sim_groups[g2]:
                        sim_groups[g1].add(sid)
                        section_to_group[sid] = g1
                    del sim_groups[g2]

    # any leftover sections become their own singleton groups
    for s in sections:
        if s.id not in section_to_group:
            gid = f"sim_{group_counter}"
            group_counter += 1
            sim_groups[gid] = {s.id}
            section_to_group[s.id] = gid

    # convert to mapping of group -> list of Section objects
    group_sections = {
        gid: [section_by_id[sid] for sid in sids]
        for gid, sids in sim_groups.items()
    }

    # Build conflict matrix
    conflict = defaultdict(int)

    for student in students:

        for c1, c2 in combinations(
            student.main_courses,
            2
        ):

            pair = tuple(sorted((c1, c2)))

            conflict[pair] += 1

    print(
        f"Sections: {len(sections)}"
    )

    print(
        f"Rooms: {len(all_rooms)}"
    )

    print(
        f"Groups: {len(group_sections)}"
    )

    print(
        f"Max sections per block <= {len(all_rooms)}"
    )

    # =================================================
    # MODEL CREATION
    # =================================================

    model = cp_model.CpModel()

    # =================================================
    # C1 - SECTION ASSIGNMENT
    # =================================================

    x = {}

    for s in sections:

        # block variables
        for b in blocks:

            x[(s.id, b)] = model.NewBoolVar(
                f"block_{s.id}_{b}"
            )

    for s in sections:

        model.Add(
            sum(x[(s.id, b)] for b in blocks) == 1
        )

    # =================================================
    # C2 - GROUP SYNCHRONIZATION
    # =================================================

    # group-level block variables (mirror of x for group)
    x_group = {}

    for gid, s_list in group_sections.items():

        # ensure group block var equals the first section's block var
        s0 = s_list[0]

        for b in blocks:
            xg = model.NewBoolVar(f"x_group_{gid}_{b}")
            x_group[(gid, b)] = xg
            model.Add(xg == x[(s0.id, b)])

        # enforce section-level synchronization: link every member to the
        # group's block var so all sections share the same block (O(n)).
        for s in s_list:
            for b in blocks:
                model.Add(x[(s.id, b)] == x_group[(gid, b)])

    # =================================================
    # C3 - ROOM CONSTRAINTS
    # =================================================

    # build group->allowed rooms (intersection of allowed rooms)
    group_allowed_rooms = {}

    for gid, s_list in group_sections.items():

        # compute allowed rooms as intersection of member course rooms
        allowed = set(course_lookup[s_list[0].course_code].rooms)

        for s in s_list[1:]:
            allowed &= set(course_lookup[s.course_code].rooms)

        group_allowed_rooms[gid] = sorted(allowed)

    # Create compact group-room-block variables z[(gid,room,block)].
    # z is true iff the group is scheduled in `block` AND occupies `room`.
    # Link with: sum_rooms z[(gid,room,b)] == x_group[(gid,b)]
    z = {}

    for gid, s_list in group_sections.items():

        rooms_for_group = group_allowed_rooms.get(gid, [])

        for room in rooms_for_group:
            for b in blocks:
                z[(gid, room, b)] = model.NewBoolVar(f"z_{gid}_{room}_{b}")

        # if group is assigned to block b, exactly one of the group's allowed
        # rooms must be chosen for that block
        for b in blocks:
            room_vars = [z[(gid, room, b)] for room in rooms_for_group if (gid, room, b) in z]
            if room_vars:
                model.Add(sum(room_vars) == x_group[(gid, b)])

    # ensure each room is used by at most one group per block
    for room in all_rooms:
        for block in blocks:
            room_block_vars = []
            for gid in group_sections:
                if (gid, room, block) in z:
                    room_block_vars.append(z[(gid, room, block)])
            if room_block_vars:
                model.Add(sum(room_block_vars) <= 1)

    # =================================================
    # C4 - SIMULTANEOUS BLOCKING RULES
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

            # force same block for matched sections
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
    # C5 - CONFLICT CONSTRAINTS
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
    # C6 - BALANCE CONSTRAINTS
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
    # O1 - OBJECTIVE FUNCTION
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
    # RESULTS
    # =================================================

    section_to_block = {}

    if status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        print("\nSECTION SCHEDULE:\n")

        # derive group-room assignments from z and assign to each section
        group_room_for_block = {}

        for gid in group_sections:
            for b in blocks:
                for room in group_allowed_rooms.get(gid, []):
                    if (gid, room, b) in z and solver.Value(z[(gid, room, b)]):
                        group_room_for_block[(gid, b)] = room
                        break

        for s in sections:
            for b in blocks:
                if solver.Value(x[(s.id, b)]):
                    section_to_block[s.id] = b
                    s.time_slot = b
                    gid = section_to_group.get(s.id)
                    assigned = group_room_for_block.get((gid, b))
                    if assigned is None:
                        # fallback: pick first allowed room for the group
                        allowed = group_allowed_rooms.get(gid, [])
                        s.room_id = allowed[0] if allowed else None
                    else:
                        s.room_id = assigned

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

    return MasterTimetable(
        sections=sections,
        section_to_block=section_to_block,
        course_to_sections=course_to_sections,
        section_by_id=section_by_id
    )