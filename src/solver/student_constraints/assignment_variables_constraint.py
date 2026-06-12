"""Assignment decision variables for the student timetable model."""

from solver.student_constraints.base import HardConstraint


class AssignmentVariablesConstraint(HardConstraint):
    """Create student-course-section assignment variables."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for student in ctx.students:

            for course_code in (
                ctx.student_course_options[student.id]["all"]
            ):

                sections = (
                    ctx.master_timetable.course_to_sections
                    .get(course_code, [])
                )

                for sec in sections:

                    ctx.x[
                        (
                            student.id,
                            course_code,
                            sec.id
                        )
                    ] = model.NewBoolVar(
                        f"x_{student.id}_{sec.id}"
                    )
