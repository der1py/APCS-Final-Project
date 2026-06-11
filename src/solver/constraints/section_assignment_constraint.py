"""Section assignment hard constraint for the master timetable model."""

from solver.constraints.base import HardConstraint


class SectionAssignmentConstraint(HardConstraint):
    """Create section-block decision variables and assignment constraints."""

    def apply(self, ctx) -> None:
        model = ctx.model

        x = {}
        ctx.x = x

        for s in ctx.sections:

            # block variables
            for b in ctx.blocks:

                x[(s.id, b)] = model.NewBoolVar(
                    f"block_{s.id}_{b}"
                )

        for s in ctx.sections:

            course = ctx.course_lookup[s.course_code]

            if course.linear:
                # Linear course: exactly one block in Semester 1 AND exactly one in Semester 2
                model.Add(
                    sum(x[(s.id, b)] for b in ctx.semester1_blocks) == 1
                )
                model.Add(
                    sum(x[(s.id, b)] for b in ctx.semester2_blocks) == 1
                )
            else:
                # Non-linear course: exactly one block across all blocks
                model.Add(
                    sum(x[(s.id, b)] for b in ctx.blocks) == 1
                )
