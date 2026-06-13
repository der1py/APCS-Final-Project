"""Room utilization soft constraint for the master timetable model."""

from solver.constraints.base import SoftConstraint
from solver.room_config import DEFAULT_ROOM_SPREAD_TARGET


ROOM_SPREAD_WEIGHT = 1


class RoomSpreadPenaltyConstraint(SoftConstraint):
    """Penalize avoidable room/block crowding to use available rooms better."""

    def apply(self, ctx) -> None:
        model = ctx.model
        penalties = []

        for room in ctx.all_rooms:
            target = ctx.room_spread_target.get(
                room,
                DEFAULT_ROOM_SPREAD_TARGET,
            )

            for block in ctx.blocks:
                room_block_vars = [
                    ctx.z[(gid, room, block)]
                    for gid in ctx.group_sections
                    if (gid, room, block) in ctx.z
                ]

                if not room_block_vars:
                    continue

                occupancy = model.NewIntVar(
                    0,
                    len(room_block_vars),
                    f"room_occupancy_{room}_{block}",
                )
                overflow = model.NewIntVar(
                    0,
                    len(room_block_vars),
                    f"room_spread_overflow_{room}_{block}",
                )

                model.Add(occupancy == sum(room_block_vars))
                model.Add(overflow >= occupancy - target)
                penalties.append(overflow)

        if penalties:
            ctx.add_objective_term(
                "room_spread_penalty",
                sum(penalties),
                ROOM_SPREAD_WEIGHT,
            )
