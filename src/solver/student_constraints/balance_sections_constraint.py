"""Section balance penalties for the student timetable model."""

from solver.student_constraints.base import HardConstraint


class BalanceSectionsConstraint(HardConstraint):
    """Create penalties for uneven enrollment across sections of one course."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for course_code, sections in (
            ctx.master_timetable.course_to_sections.items()
        ):

            if len(sections) <= 1:
                continue

            total_cap = sum(
                ctx.section_capacity[s.id]
                for s in sections
            )

            target = total_cap // len(sections)

            for sec in sections:

                diff = model.NewIntVar(
                    -1000,
                    1000,
                    f"diff_{sec.id}"
                )

                abs_diff = model.NewIntVar(
                    0,
                    1000,
                    f"abs_{sec.id}"
                )

                model.Add(
                    diff ==
                    ctx.enrollment[sec.id] - target
                )

                model.AddAbsEquality(
                    abs_diff,
                    diff
                )

                ctx.balance_penalties.append(
                    abs_diff
                )
