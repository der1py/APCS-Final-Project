"""Base interfaces for modular master timetable constraints.

These classes are Phase 1 scaffolding. Existing constraints remain in
``master_timetable_builder.py`` for now, but later phases can move each
constraint into its own module by implementing one of these interfaces.
"""

from abc import ABC, abstractmethod


class BaseConstraint(ABC):
    """Common interface for constraints that mutate a shared SolverContext."""

    @abstractmethod
    def apply(self, ctx):
        """Apply this constraint to the shared CP-SAT model context."""

        raise NotImplementedError


class HardConstraint(BaseConstraint):
    """Base class for hard constraints.

    Implementations should add constraints directly to ``ctx.model`` and return
    nothing. Because all constraints share the same CP-SAT model object, each
    hard constraint can safely mutate the model in place.
    """


class SoftConstraint(BaseConstraint):
    """Base class for soft constraints.

    Implementations should create penalty expressions or variables on
    ``ctx.model`` and call ``ctx.add_objective_term(...)`` with the weighted
    term that should be included in the final objective.
    """
