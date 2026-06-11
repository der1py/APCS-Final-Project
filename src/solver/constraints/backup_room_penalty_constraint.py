"""Backup-room preference soft constraint for the master timetable model.

This module preserves the existing backup-room objective logic while moving it
behind the shared SolverContext interface.
"""

from solver.constraints.base import SoftConstraint


ROOM_PENALTY_WEIGHT = 50
BACKUP_ROOM_COST = 1  # per-assignment penalty for a backup room


class BackupRoomPenaltyConstraint(SoftConstraint):
    """Penalize assigning a group to a backup room instead of a primary room."""

    def apply(self, ctx) -> None:
        backup_room_penalty = sum(
            BACKUP_ROOM_COST * ctx.z[(gid, room, b)]
            for gid in ctx.group_sections
            for room in ctx.group_allowed_rooms.get(gid, [])
            for b in ctx.blocks
            if (gid, room, b) in ctx.z
            and room not in ctx.group_primary_rooms.get(gid, set())
        )

        ctx.add_objective_term(
            "backup_room_penalty",
            backup_room_penalty,
            ROOM_PENALTY_WEIGHT
        )
