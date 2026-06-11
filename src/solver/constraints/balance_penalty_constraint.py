"""Balance penalty soft constraint for the master timetable model.

This is an early modular constraint migration. The logic is copied from
``master_timetable_builder.py`` so current solver behavior stays canonical
while future phases continue moving constraints out of the builder.
"""

from solver.constraints.base import SoftConstraint


BALANCE_WEIGHT = 100


class BalancePenaltyConstraint(SoftConstraint):
    """Penalize block loads that deviate from the target section count."""

    def apply(self, ctx) -> None:
        model = ctx.model
        target = len(ctx.sections) // len(ctx.blocks)

        balance_penalties = []

        for b in ctx.blocks:

            count = sum(
                ctx.x[(s.id, b)]
                for s in ctx.sections
            )

            diff = model.NewIntVar(
                -len(ctx.sections),
                len(ctx.sections),
                f"balance_diff_{b}"
            )

            deviation = model.NewIntVar(
                0,
                len(ctx.sections),
                f"balance_dev_{b}"
            )

            model.Add(
                diff == count - target
            )

            model.AddAbsEquality(
                deviation,
                diff
            )

            balance_penalties.append(
                deviation
            )

        ctx.add_objective_term(
            "balance_penalty",
            sum(balance_penalties),
            BALANCE_WEIGHT
        )
