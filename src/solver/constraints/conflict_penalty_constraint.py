"""Conflict penalty soft constraint for the master timetable model."""

from solver.constraints.base import SoftConstraint


class ConflictPenaltyConstraint(SoftConstraint):
    """Create same-block indicators and add the unweighted conflict cost."""

    def apply(self, ctx) -> None:
        model = ctx.model
        same_block = {}
        ctx.same_block = same_block

        for (c1, c2), weight in ctx.conflict.items():

            if c1 not in ctx.course_to_sections:
                continue

            if c2 not in ctx.course_to_sections:
                continue

            for s1 in ctx.course_to_sections[c1]:

                for s2 in ctx.course_to_sections[c2]:

                    # skip same-course comparisons
                    if s1.course_code == s2.course_code:
                        continue

                    for b in ctx.blocks:

                        v = model.NewBoolVar(
                            f"same_{s1.id}_{s2.id}_{b}"
                        )

                        same_block[(s1.id, s2.id, b)] = v

                        model.Add(
                            v <= ctx.x[(s1.id, b)]
                        )

                        model.Add(
                            v <= ctx.x[(s2.id, b)]
                        )

                        model.Add(
                            v >=
                            ctx.x[(s1.id, b)] +
                            ctx.x[(s2.id, b)] - 1
                        )

        conflict_cost = sum(

            ctx.conflict[(c1, c2)]
            *
            same_block[(s1.id, s2.id, b)]

            for (c1, c2) in ctx.conflict

            if c1 in ctx.course_to_sections
            and c2 in ctx.course_to_sections

            for s1 in ctx.course_to_sections[c1]
            for s2 in ctx.course_to_sections[c2]

            if s1.course_code != s2.course_code

            for b in ctx.blocks
        )

        ctx.add_objective_term(
            "conflict_cost",
            conflict_cost,
            1
        )
