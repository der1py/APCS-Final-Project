"""Room assignment hard constraint for the master timetable model."""

from analysis.data_analysis import analyze_room_assignment_risk
from solver.constraints.base import HardConstraint


class RoomAssignmentConstraint(HardConstraint):
    """Create room assignment variables and room-capacity constraints."""

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

        # Show analysis (unchanged)
        analyze_room_assignment_risk(ctx.group_sections, group_allowed_rooms, group_primary_rooms)

        # Create compact group-room-block variables z[(gid,room,block)].
        # z is true iff the group is scheduled in `block` AND occupies `room`.
        # Link with: sum_rooms z[(gid,room,b)] == x_group[(gid,b)]
        z = {}
        ctx.z = z

        for gid, s_list in ctx.group_sections.items():
            rooms_for_group = group_allowed_rooms.get(gid, [])

            # If there are no allowed rooms:
            if len(rooms_for_group) == 0:
                if ctx.enable_room_fallback:
                    # Allow the group to be scheduled without a room assignment.
                    # Do not create z variables or room constraints for this group.
                    continue
                else:
                    # Enforce that the group cannot be scheduled (makes model
                    # infeasible if the sections must be scheduled).
                    for b in ctx.blocks:
                        model.Add(ctx.x_group[(gid, b)] == 0)
                    continue

            # Create z variables for groups with available rooms
            for room in rooms_for_group:
                for b in ctx.blocks:
                    z[(gid, room, b)] = model.NewBoolVar(f"z_{gid}_{room}_{b}")

            # if group is assigned to block b, exactly one of the group's allowed
            # rooms must be chosen for that block
            for b in ctx.blocks:
                room_vars = [z[(gid, room, b)] for room in rooms_for_group if (gid, room, b) in z]
                if room_vars:
                    model.Add(sum(room_vars) == ctx.x_group[(gid, b)])

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
                        <= ctx.room_capacity.get(room, 3)
                    )
