"""Section enrollment constraints for the student timetable model."""

from solver.student_constraints.base import HardConstraint


class SectionEnrollmentConstraint(HardConstraint):
    """Count assigned students in each section and cap enrollment."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for sec in ctx.master_timetable.sections:

            cap = ctx.section_capacity[sec.id]

            e = model.NewIntVar(
                0,
                cap,
                f"enrollment_{sec.id}"
            )

            ctx.enrollment[sec.id] = e

            vars_for_section = []

            for student in ctx.students:

                if (
                    sec.course_code
                    not in ctx.student_course_options[student.id]["all"]
                ):
                    continue

                vars_for_section.append(
                    ctx.x[
                        (
                            student.id,
                            sec.course_code,
                            sec.id
                        )
                    ]
                )

            model.Add(
                e == sum(vars_for_section)
            )
