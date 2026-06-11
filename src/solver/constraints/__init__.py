"""Constraint interfaces for future master timetable modules."""

from solver.constraints.backup_room_penalty_constraint import BackupRoomPenaltyConstraint
from solver.constraints.base import BaseConstraint, HardConstraint, SoftConstraint
from solver.constraints.balance_penalty_constraint import BalancePenaltyConstraint
from solver.constraints.conflict_penalty_constraint import ConflictPenaltyConstraint
from solver.constraints.group_sync_constraint import GroupSyncConstraint
from solver.constraints.room_assignment_constraint import RoomAssignmentConstraint
from solver.constraints.sequencing_constraint import SequencingConstraint
from solver.constraints.section_assignment_constraint import SectionAssignmentConstraint
from solver.constraints.simultaneous_blocking_constraint import SimultaneousBlockingConstraint

__all__ = [
    "BackupRoomPenaltyConstraint",
    "BaseConstraint",
    "BalancePenaltyConstraint",
    "ConflictPenaltyConstraint",
    "GroupSyncConstraint",
    "HardConstraint",
    "RoomAssignmentConstraint",
    "SequencingConstraint",
    "SectionAssignmentConstraint",
    "SoftConstraint",
    "SimultaneousBlockingConstraint",
]
