"""Debugging-only soft room assignment constraint.

This constraint exists solely to diagnose room-assignment infeasibility. It
mirrors the production room assignment structure, but lets the solver choose a
massively-penalized ``roomless`` variable when no valid room assignment can be
made.
"""

from pathlib import Path

from analysis.data_analysis import analyze_room_assignment_risk
from solver.constraints.base import SoftConstraint
from solver.room_config import DEFAULT_ROOM_CAPACITY


ROOMLESS_DEBUG_WEIGHT = 99999999
ROOMLESS_DEBUG_REPORT_PATH = "src/output/logging/roomless_debug.txt"


class RoomAssignmentDebugSoftConstraint(SoftConstraint):
    """Create room assignment variables with a penalized roomless escape hatch."""

    @staticmethod
    def get_roomless_assignments(ctx, solver):
        """Return roomless group/block selections after a debug solve."""

        return [
            {
                "group_id": gid,
                "block": block,
                "section_ids": ctx.roomless_debug_group_sections.get(gid, []),
            }
            for (gid, block), roomless_var in getattr(ctx, "roomless_debug", {}).items()
            if solver.Value(roomless_var)
        ]

    @staticmethod
    def write_roomless_report(
        ctx,
        solver,
        output_path=ROOMLESS_DEBUG_REPORT_PATH,
    ):
        """Write selected roomless group/block assignments after solving."""

        assignments = RoomAssignmentDebugSoftConstraint.get_roomless_assignments(
            ctx,
            solver,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "Roomless Debug Assignments",
            f"Count: {len(assignments)}",
            f"Unique groups: {len({item['group_id'] for item in assignments})}",
            "",
        ]

        if not assignments:
            lines.append(
                "No roomless group-block assignments were selected."
            )
        else:
            for item in assignments:
                section_ids = ", ".join(item["section_ids"])
                lines.append(
                    f"group_id={item['group_id']} "
                    f"block={item['block']} "
                    f"sections={section_ids}"
                )

        path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

        return assignments

    def apply(self, ctx) -> None:
        model = ctx.model

        # build group->allowed rooms (intersection of allowed rooms)
        # include back_up_rooms so backup rooms are valid options
        group_allowed_rooms = {}
        group_primary_rooms = {}  # subset of allowed rooms that are primary
        ctx.group_allowed_rooms = group_allowed_rooms
        ctx.group_primary_rooms = group_primary_rooms

        for gid, s_list in ctx.group_sections.items():

            # compute allowed rooms as intersection of (primary + backup) rooms
            allowed = set(ctx.course_lookup[s_list[0].course_code].rooms) | set(ctx.course_lookup[s_list[0].course_code].back_up_rooms)
            primary = set(ctx.course_lookup[s_list[0].course_code].rooms)

            for s in s_list[1:]:
                c = ctx.course_lookup[s.course_code]
                allowed &= (set(c.rooms) | set(c.back_up_rooms))
                primary &= set(c.rooms)

            group_allowed_rooms[gid] = sorted(allowed)
            group_primary_rooms[gid] = primary

        # =================================================
        # CLASSIFY GROUPS BY ROOM AVAILABILITY
        # =================================================
        roomless_groups = {
            gid
            for gid, rooms in group_allowed_rooms.items()
            if len(rooms) == 0
        }

        normal_groups = set(group_allowed_rooms.keys()) - roomless_groups
        ctx.roomless_groups = roomless_groups
        ctx.room_assignment_debug_normal_groups = normal_groups

        # Show analysis (unchanged)
        analyze_room_assignment_risk(ctx.group_sections, group_allowed_rooms, group_primary_rooms)

        # Create compact group-room-block variables z[(gid,room,block)].
        # z is true iff the group is scheduled in `block` AND occupies `room`.
        # Link with: sum_rooms z[(gid,room,b)] + roomless[(gid,b)] == x_group[(gid,b)]
        z = {}
        roomless = {}
        ctx.z = z

        # Diagnostic reporting helpers:
        # after solving, inspect solver.Value(ctx.roomless_debug[(gid, b)]) to
        # report the exact groups/sections that could not obtain a valid room.
        ctx.roomless_debug = roomless
        ctx.roomless_debug_group_sections = {
            gid: [s.id for s in s_list]
            for gid, s_list in ctx.group_sections.items()
        }

        for gid, s_list in ctx.group_sections.items():
            rooms_for_group = group_allowed_rooms.get(gid, [])

            for b in ctx.blocks:
                roomless[(gid, b)] = model.NewBoolVar(f"roomless_debug_{gid}_{b}")

            # Create z variables for groups with available rooms
            for room in rooms_for_group:
                for b in ctx.blocks:
                    z[(gid, room, b)] = model.NewBoolVar(f"z_{gid}_{room}_{b}")

            # if group is assigned to block b, exactly one of the group's allowed
            # rooms or the roomless debug variable must be chosen for that block
            for b in ctx.blocks:
                room_vars = [z[(gid, room, b)] for room in rooms_for_group if (gid, room, b) in z]
                model.Add(sum(room_vars) + roomless[(gid, b)] == ctx.x_group[(gid, b)])

        # ensure each room respects its configured capacity per block
        for room in ctx.all_rooms:
            for block in ctx.blocks:
                room_block_vars = []
                for gid in ctx.group_sections:
                    if (gid, room, block) in z:
                        room_block_vars.append(z[(gid, room, block)])
                if room_block_vars:
                    model.Add(
                        sum(room_block_vars)
                        <= ctx.room_capacity.get(room, DEFAULT_ROOM_CAPACITY)
                    )

        roomless_debug_penalty = sum(
            roomless[(gid, b)]
            for gid in ctx.group_sections
            for b in ctx.blocks
        )

        ctx.add_objective_term(
            "roomless_debug_penalty",
            roomless_debug_penalty,
            ROOMLESS_DEBUG_WEIGHT
        )
