"""Shared context for modular student timetable CP-SAT constraints."""

from collections import defaultdict
from dataclasses import dataclass, field

from solver.constraints.base import HardConstraint


@dataclass
class StudentSolverContext:
    """State shared by student timetable constraint modules."""

    model: object
    students: list
    master_timetable: object
    course_lookup: dict
    semester1_blocks: set
    semester2_blocks: set
    blocking_rules: dict
    sequence_rules: list
    notsim_pairs: set
    student_course_options: dict
    section_capacity: dict
    group_sections: dict
    section_to_group: dict
    x: dict = field(default_factory=dict)
    assigned_course_vars: list = field(default_factory=list)
    assigned_alternate_vars: list = field(default_factory=list)
    assigned_by_course: dict = field(default_factory=dict)
    assigned_main_by_student: dict = field(
        default_factory=lambda: defaultdict(list)
    )
    assigned_alternate_by_student: dict = field(
        default_factory=lambda: defaultdict(list)
    )
    assigned_all_by_student: dict = field(
        default_factory=lambda: defaultdict(list)
    )
    full_schedule_vars: list = field(default_factory=list)
    enrollment: dict = field(default_factory=dict)
    active: dict = field(default_factory=dict)
    active_groups: dict = field(default_factory=dict)
    group_enrollment: dict = field(default_factory=dict)
    under_half_penalties: list = field(default_factory=list)
    balance_penalties: list = field(default_factory=list)

    def section_occupied(self, sec):
        occupied = getattr(sec, "occupied_blocks", None)

        if not occupied:
            occupied = [sec.time_slot]

        return occupied

    def section_in_semester(self, sec, semester_blocks):
        return any(
            b in semester_blocks
            for b in self.section_occupied(sec)
        )

    def is_notsim_pair(self, c1, c2):
        return (
            c1 != c2
            and frozenset((c1, c2)) in self.notsim_pairs
        )


__all__ = [
    "HardConstraint",
    "StudentSolverContext",
]
