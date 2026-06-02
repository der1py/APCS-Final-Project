# This module builds the master timetable using CP-SAT.
import sys
import os

from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations
import math

from ortools.sat.python import cp_model

from models.section import Section

from data.data_loader import load_simultaneous_blocking_rules
import csv

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

    DEFAULT_BLOCKS = 8

    blocking_rules = load_simultaneous_blocking_rules()

    # -------------------------------------------------
    # Cancel low-enrollment sections before building the
    # timetable sections. Use a stricter threshold so extra
    # sections are removed earlier.
    # -------------------------------------------------

    LOW_ENROLLMENT_THRESHOLD = 0.5

    course_lookup = {
        c.code: c
        for c in courses
    }

    requests_per_course = defaultdict(int)
    for student in students:
        for ccode in student.main_courses:
            if ccode in course_lookup:
                requests_per_course[ccode] += 1

    adjusted = []
    for c in courses:
        max_per_section = getattr(c, 'enrollment_max', None)
        if max_per_section is None or max_per_section <= 0:
            continue

        requested = requests_per_course.get(c.code, 0)
        total_max = max_per_section * c.num_sections

        if total_max > 0 and requested < LOW_ENROLLMENT_THRESHOLD * total_max:
            # compute the largest number of sections such that
            # requested >= threshold * (enrollment_max * new_num_sections)
            new_ns = int(math.floor(requested / (LOW_ENROLLMENT_THRESHOLD * max_per_section)))
            if requested > 0:
                new_ns = max(1, new_ns)
            if new_ns < c.num_sections:
                adjusted.append((c.code, c.num_sections, new_ns, requested, max_per_section))
                c.num_sections = new_ns

    if adjusted:
        print("Adjusted low-enrollment courses (code, old_ns, new_ns, requested, per_section_max):")
        for rec in adjusted:
            print(rec)

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

    # collect rooms declared on courses
    course_rooms = {
        room
        for c in courses
        for room in c.rooms
    }

    # also read staff room list to include any rooms not referenced by courses
    staff_rooms = set()
    try:
        staff_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'cleaned data', 'Staff list with rooms.csv')
        staff_csv = os.path.normpath(staff_csv)
        with open(staff_csv, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = row.get('Num')
                if num:
                    staff_rooms.add(num.strip())
    except Exception:
        # if staff file missing or unreadable, ignore and proceed with course rooms
        staff_rooms = set()

    all_rooms = sorted(course_rooms | staff_rooms)

    # Build simultaneous groups: sections grouped into atomic room-units.
    # Each section will belong to exactly one group; groups created from
    # simultaneous blocking rules, then remaining sections become singleton
    # groups so the room-constraint logic can be applied uniformly.

    sim_groups = {}           # group_id -> set(section_id)
    section_to_group = {}     # section_id -> group_id
    group_counter = 0

    for blocking_type, pairs in blocking_rules.items():

        if blocking_type != "Simultaneous":
            continue

        for c1, c2 in pairs:

            # only consider pairs where both courses exist
            if c1 not in course_to_sections:
                continue

            if c2 not in course_to_sections:
                continue

            course1 = course_lookup.get(c1)
            course2 = course_lookup.get(c2)
            if course1 is None or course2 is None:
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

    blocks = list(range(DEFAULT_BLOCKS))

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

    # diagnostics for group-room capacity constraints
    zero_room_groups = [gid for gid, rooms in group_allowed_rooms.items() if not rooms]
    room_count_list = [len(rooms) for rooms in group_allowed_rooms.values()]
    singleton_room_groups = defaultdict(int)
    for gid, rooms in group_allowed_rooms.items():
        if len(rooms) == 1:
            singleton_room_groups[rooms[0]] += 1

    print("\nGROUP-ROOM CAPACITY DIAGNOSTICS:")
    print(f"  Zero common-room groups: {len(zero_room_groups)}")
    print(f"  Groups with 1 allowed room: {sum(1 for count in room_count_list if count == 1)}")
    print(f"  Groups with <=2 allowed rooms: {sum(1 for count in room_count_list if count <= 2)}")
    print(f"  Groups with <=3 allowed rooms: {sum(1 for count in room_count_list if count <= 3)}")
    print(f"  Min allowed rooms per group: {min(room_count_list) if room_count_list else 0}")
    print(f"  Median allowed rooms per group: {sorted(room_count_list)[len(room_count_list)//2] if room_count_list else 0}")
    print(f"  Rooms with >8 singleton-only group assignments: {sum(1 for count in singleton_room_groups.values() if count > DEFAULT_BLOCKS)}")
    if singleton_room_groups:
        top_singleton_rooms = sorted(singleton_room_groups.items(), key=lambda item: item[1], reverse=True)[:10]
        print("  Top singleton-only rooms:")
        for room, count in top_singleton_rooms:
            print(f"    {room}: {count}")

    # identify staff rooms that were not referenced by any course
    missing_staff_rooms = sorted(list(staff_rooms - course_rooms))
    if missing_staff_rooms:
        print("Missing staff rooms (not in course rooms):", missing_staff_rooms)

    # If a group has no common allowed rooms, offer all available rooms as fallback.
    # This ensures feasibility; solver will minimize cost of using non-preferred rooms.
    for gid in list(group_allowed_rooms.keys()):
        if not group_allowed_rooms[gid]:
            # zero-room groups: allow ANY room in all_rooms (with penalty in objective)
            group_allowed_rooms[gid] = all_rooms

    # =================================================
    # C3.5 - ROOM ASSIGNMENT PER SECTION (create y after group_allowed_rooms)
    # =================================================

    y = {}

    for s in sections:

        course = course_lookup[s.course_code]
        gid = section_to_group.get(s.id)

        # base allowed rooms from course, plus any group-level allowed rooms
        # (this ensures that when we added missing staff rooms as group
        # fallbacks, those rooms are also available at section-level)
        allowed_rooms = set(course.rooms) | set(group_allowed_rooms.get(gid, []))

        for room in sorted(allowed_rooms):
            y[(s.id, room)] = model.NewBoolVar(
                f"room_{s.id}_{room}"
            )

        model.Add(
            sum(
                y[(s.id, room)]
                for room in sorted(allowed_rooms)
            ) == 1
        )

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

        # if the group has a common room intersection, force every section in
        # the group to use the group's chosen room.
        if rooms_for_group:
            for s in s_list:
                # enforce y for each room the group may occupy
                for room in rooms_for_group:
                    # y exists because we created per-section allowed rooms
                    model.Add(
                        y[(s.id, room)] ==
                        sum(z[(gid, room, b)] for b in blocks)
                    )

                # any section-level rooms not in the group's allowed set must be 0
                for room in course_lookup[s.course_code].rooms:
                    if room not in rooms_for_group:
                        model.Add(y[(s.id, room)] == 0)

    # ensure each room is used by at most one group or one section per block
    # for overloaded rooms (singleton-only count > blocks), allow multiple groups but penalize in objective
    room_block_overload = {}  # (room, block) -> IntVar for group count
    
    for room in all_rooms:
        for block in blocks:
            room_block_vars = []

            # group-level occupancy for groups with a common room
            for gid in group_sections:
                if (gid, room, block) in z:
                    room_block_vars.append(z[(gid, room, block)])

            # section-level occupancy for groups without a common room
            for gid, s_list in group_sections.items():
                if not group_allowed_rooms[gid]:
                    for s in s_list:
                        if room in course_lookup[s.course_code].rooms:
                            v = model.NewBoolVar(
                                f"use_{s.id}_{room}_{block}"
                            )
                            model.Add(v <= x[(s.id, block)])
                            model.Add(v <= y[(s.id, room)])
                            model.Add(
                                v >=
                                x[(s.id, block)] +
                                y[(s.id, room)] - 1
                            )
                            room_block_vars.append(v)

            if room_block_vars:

                count_var = model.NewIntVar(
                    0,
                    len(group_sections),
                    f"count_{room}_{block}"
                )

                model.Add(
                    count_var ==
                    sum(room_block_vars)
                )
                model.Add(count_var <= 2)  # hard constraint: no more than 2 groups/sections per room-block

                overload = model.NewIntVar(
                    0,
                    len(group_sections),
                    f"overload_{room}_{block}"
                )

                model.Add(
                    overload >= count_var - 1
                )

                model.Add(
                    overload >= 0
                )

                room_block_overload[(room, block)] = overload

    # =================================================
    # C4 - SIMULTANEOUS BLOCKING RULES
    # =================================================

    print("\nADDING SIMULTANEOUS BLOCKING RULES...\n")

    for blocking_type, pairs in blocking_rules.items():

        if blocking_type != "Simultaneous":
            continue

        print(f"Blocking Type: {blocking_type}")

        for c1, c2 in pairs:

            if c1 not in course_to_sections:
                print(f"Missing course: {c1}")
                continue

            if c2 not in course_to_sections:
                print(f"Missing course: {c2}")
                continue

            course1 = course_lookup.get(c1)
            course2 = course_lookup.get(c2)
            if course1 is None or course2 is None:
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
    ROOM_OVERLOAD_WEIGHT = 5000  # reduced to prioritize feasibility over perfect separation

    # compute overload penalty: for each overloaded room-block, penalize based on group count > 1
    room_overload_cost = (
        ROOM_OVERLOAD_WEIGHT
        *
        sum(room_block_overload.values())
    )

    model.Minimize(

        conflict_cost

        +

        BALANCE_WEIGHT
        *
        sum(balance_penalties)

        +

        room_overload_cost

    )

    # =================================================
    # SOLVE
    # =================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    print('SOLVER STATUS:', solver.StatusName(status))

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