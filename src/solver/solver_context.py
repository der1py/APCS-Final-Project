"""Shared CP-SAT solver context for the master timetable builder.

Phase 1 keeps the existing constraint logic inside
``master_timetable_builder.py``. This module provides the shared state object
that future modular hard and soft constraint files will receive so they can
mutate the same CP-SAT model without redesigning solver behavior.
"""

from dataclasses import dataclass, field
from typing import Any, List, Union


@dataclass
class ObjectiveTerm:
    """A weighted objective component contributed by a soft constraint."""

    name: str
    expression: Any
    weight: Union[int, float]


@dataclass
class SolverContext:
    """Shared state passed to future master-timetable constraint modules.

    Hard constraints should add constraints directly to ``model``. Soft
    constraints should create any needed penalty variables or expressions and
    register them with ``add_objective_term`` so the builder can combine all
    terms into one objective.
    """

    model: Any
    students: list
    courses: list
    blocks: list
    semester1_blocks: list
    semester2_blocks: list
    sections: list
    course_to_sections: dict
    section_by_id: dict
    course_lookup: dict
    group_sections: dict
    section_to_group: dict
    all_rooms: list
    room_capacity: dict
    enable_room_fallback: bool
    blocking_rules: dict
    sequence_rules: list
    sequence_demand: dict
    conflict: dict
    x: dict = field(default_factory=dict)
    x_group: dict = field(default_factory=dict)
    z: dict = field(default_factory=dict)
    same_block: dict = field(default_factory=dict)
    group_allowed_rooms: dict = field(default_factory=dict)
    group_primary_rooms: dict = field(default_factory=dict)
    roomless_groups: set = field(default_factory=set)
    objective_terms: List[ObjectiveTerm] = field(default_factory=list)

    def add_objective_term(self, name, expression, weight):
        """Register a weighted objective term for a future soft constraint."""

        self.objective_terms.append(
            ObjectiveTerm(
                name=name,
                expression=expression,
                weight=weight,
            )
        )

    def build_objective(self):
        """Combine all registered objective terms into one CP-SAT expression."""

        return sum(
            term.weight * term.expression
            for term in self.objective_terms
        )
