"""Course assignment constraints for the student timetable model."""

from solver.student_constraints.base import HardConstraint


class CourseAssignmentConstraint(HardConstraint):
    """Track whether requested main and alternate courses are assigned."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for student in ctx.students:

            for course_code in (
                ctx.student_course_options[student.id]["all"]
            ):

                vars_for_course = []

                for sec in (
                    ctx.master_timetable.course_to_sections
                    .get(course_code, [])
                ):

                    vars_for_course.append(
                        ctx.x[
                            (
                                student.id,
                                course_code,
                                sec.id
                            )
                        ]
                    )

                if not vars_for_course:
                    continue

                assigned = model.NewBoolVar(
                    f"assigned_{student.id}_{course_code}"
                )

                model.Add(
                    sum(vars_for_course) == assigned
                )

                ctx.assigned_by_course[
                    (
                        student.id,
                        course_code
                    )
                ] = assigned

                ctx.assigned_all_by_student[student.id].append(
                    assigned
                )

                if (
                    course_code
                    in ctx.student_course_options[student.id]["main"]
                ):
                    ctx.assigned_course_vars.append(
                        assigned
                    )
                    ctx.assigned_main_by_student[student.id].append(
                        assigned
                    )

                else:
                    ctx.assigned_alternate_vars.append(
                        assigned
                    )
                    ctx.assigned_alternate_by_student[student.id].append(
                        assigned
                    )

        for student in ctx.students:
            main_count = len(
                ctx.student_course_options[student.id]["main"]
            )

            model.Add(
                sum(ctx.assigned_alternate_by_student[student.id])
                <=
                main_count
                -
                sum(ctx.assigned_main_by_student[student.id])
            )
