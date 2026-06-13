# This module builds the master timetable using CP-SAT.
import sys
import pickle

from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations

from ortools.sat.python import cp_model

from models.section import Section

from data.data_loader import (
    load_simultaneous_blocking_rules,
    load_rules,
)

from solver.constraints import (
    BackupRoomPenaltyConstraint,
    BandRoomSharingConstraint,
    BalancePenaltyConstraint,
    ConflictPenaltyConstraint,
    GroupSyncConstraint,
    RoomAssignmentConstraint,
    RoomSpreadPenaltyConstraint,
    SequencingConstraint,
    SectionAssignmentConstraint,
    SimultaneousBlockingConstraint,
)
from solver.room_config import (
    get_room_capacity_map,
    get_room_spread_target_map,
)
from solver.solver_context import SolverContext

# Toggle: when True, groups with zero allowed rooms may be scheduled without
# requiring a room assignment. When False, roomless behavior is not permitted
# (model will behave as before).
ENABLE_ROOM_FALLBACK = True

# =====================================================
# MASTER TIMETABLE OBJECT
# =====================================================

@dataclass
class MasterTimetable:

    sections: list

    section_to_block: dict

    course_to_sections: dict

    section_by_id: dict

    course_lookup: dict

    section_to_blocks: dict


# NOTE: Room-assignment analysis moved to src/analysis/data_analysis.py


# =====================================================
# BUILD MASTER TIMETABLE
# =====================================================


def build_master_timetable(students, courses):

    # =================================================
    # SETUP
    # =================================================

    blocks = list(range(8))
    semester1_blocks = [0, 1, 2, 3]
    semester2_blocks = [4, 5, 6, 7]

    blocking_rules = load_simultaneous_blocking_rules()

    # =================================================
    # LOAD SEQUENCING RULES
    # =================================================

    rules = load_rules()

    sequence_rules = list(rules.sequence_pairs)

    sections = []

    course_to_sections = defaultdict(list)

    for course in courses:
        
        # filter out courses outside of timetable
        if course.outside_tt:
            continue

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
        for room in (c.rooms + c.back_up_rooms)
    })

    room_capacity = get_room_capacity_map()
    room_spread_target = get_room_spread_target_map()

    # Build simultaneous groups: sections grouped into atomic room-units.
    # Each section will belong to exactly one group; groups created from
    # simultaneous blocking rules, then remaining sections become singleton
    # groups so the room-constraint logic can be applied uniformly.

    sim_groups = {}           # group_id -> set(section_id)
    section_to_group = {}     # section_id -> group_id
    group_counter = 0

    for c1, c2 in blocking_rules.get("Simultaneous", []):

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
    # SEQUENCING DEMAND
    # =================================================

    sequence_demand = defaultdict(int)

    for student in students:

        requested = set(student.main_courses)

        for prereq, advanced in sequence_rules:

            if (
                prereq in requested
                and advanced in requested
            ):

                sequence_demand[
                    (prereq, advanced)
                ] += 1

    # =================================================
    # MODEL CREATION
    # =================================================

    model = cp_model.CpModel()

    # Phase 1 modular constraint infrastructure.
    # Existing constraints remain in this builder for now; later phases can
    # move them into separate HardConstraint/SoftConstraint classes that all
    # receive this shared context and mutate the same CP-SAT model.
    ctx = SolverContext(
        model=model,
        students=students,
        courses=courses,
        blocks=blocks,
        semester1_blocks=semester1_blocks,
        semester2_blocks=semester2_blocks,
        sections=sections,
        course_to_sections=course_to_sections,
        section_by_id=section_by_id,
        course_lookup=course_lookup,
        group_sections=group_sections,
        section_to_group=section_to_group,
        all_rooms=all_rooms,
        room_capacity=room_capacity,
        room_spread_target=room_spread_target,
        enable_room_fallback=ENABLE_ROOM_FALLBACK,
        blocking_rules=blocking_rules,
        sequence_rules=sequence_rules,
        sequence_demand=sequence_demand,
        conflict=conflict,
    )

    # =================================================
    # MODULAR CONSTRAINTS
    # =================================================

    constraints = [
        SectionAssignmentConstraint(),
        GroupSyncConstraint(),
        RoomAssignmentConstraint(),
        BandRoomSharingConstraint(),
        SimultaneousBlockingConstraint(),
        ConflictPenaltyConstraint(),
        SequencingConstraint(),
        BalancePenaltyConstraint(),
        RoomSpreadPenaltyConstraint(),
        BackupRoomPenaltyConstraint(),
    ]

    for constraint in constraints:
        constraint.apply(ctx)

    x = ctx.x
    z = ctx.z
    group_allowed_rooms = ctx.group_allowed_rooms
    roomless_groups = ctx.roomless_groups

    # =================================================
    # O1 - OBJECTIVE FUNCTION
    # =================================================

    model.Minimize(ctx.build_objective())

    # =================================================
    # SOLVE
    # =================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 120
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
            occupied = [
                b
                for b in blocks
                if solver.Value(x[(s.id, b)])
            ]
            s.occupied_blocks = occupied
            s.time_slot = occupied[0] if occupied else -1

            if occupied:
                section_to_block[s.id] = occupied[0]

            gid = section_to_group.get(s.id)
            assigned = None
            for b in occupied:
                room = group_room_for_block.get((gid, b))
                if room is not None:
                    assigned = room
                    break

            if assigned is None:
                # No assigned room from z. If the group is roomless and
                # fallback is enabled, label explicitly. Otherwise pick
                # the first allowed room (existing behavior).
                allowed = group_allowed_rooms.get(gid, [])
                if (
                    ENABLE_ROOM_FALLBACK
                    and gid in roomless_groups
                ):
                    s.room_id = "NO ROOM FOUND"
                else:
                    s.room_id = allowed[0] if allowed else None
            else:
                s.room_id = assigned

            print(
                f"{s.id:15}"
                f" Block {s.time_slot}"
                f" Room {s.room_id}"
                f" Blocks {occupied}"
            )

        print(
            "\nTotal Conflict Cost:",
            solver.ObjectiveValue()
        )

    else:

        print("No solution found.")
        sys.exit() # <-- THIS STOPS THE SCRIPT FROM CRASHING LATER

    section_to_blocks = {
        s.id: s.occupied_blocks
        for s in sections
    }

    result = MasterTimetable(
        sections=sections,
        section_to_block=section_to_block,
        course_to_sections=course_to_sections,
        section_by_id=section_by_id,
        course_lookup=course_lookup,
        section_to_blocks=section_to_blocks
    )

    with open("src/output/master_timetable.pkl", "wb") as f:
        pickle.dump(result, f)

    return result
