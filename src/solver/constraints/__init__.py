"""Constraint interfaces for future master timetable modules."""

from solver.constraints.backup_room_penalty_constraint import BackupRoomPenaltyConstraint
from solver.constraints.base import BaseConstraint, HardConstraint, SoftConstraint
from solver.constraints.balance_penalty_constraint import BalancePenaltyConstraint

__all__ = [
    "BackupRoomPenaltyConstraint",
    "BaseConstraint",
    "BalancePenaltyConstraint",
    "HardConstraint",
    "SoftConstraint",
]
