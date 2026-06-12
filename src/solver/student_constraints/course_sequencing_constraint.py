"""Course sequencing constraints for student section assignments."""

from solver.student_constraints.base import HardConstraint


class CourseSequencingConstraint(HardConstraint):
    """Keep prerequisite assignments in semester 1 and subsequent in semester 2."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for student in ctx.students:

            requested = set(
                ctx.student_course_options[student.id]["all"]
            )

            for prereq, subsequent in ctx.sequence_rules:

                if prereq not in requested:
                    continue

                if subsequent not in requested:
                    continue

                prereq_assigned = ctx.assigned_by_course.get(
                    (
                        student.id,
                        prereq
                    )
                )

                subsequent_assigned = ctx.assigned_by_course.get(
                    (
                        student.id,
                        subsequent
                    )
                )

                if prereq_assigned is None:
                    continue

                if subsequent_assigned is None:
                    continue

                for sec in (
                    ctx.master_timetable.course_to_sections
                    .get(prereq, [])
                ):

                    if not ctx.section_in_semester(
                        sec,
                        ctx.semester1_blocks
                    ):

                        model.Add(
                            ctx.x[
                                (
                                    student.id,
                                    prereq,
                                    sec.id
                                )
                            ] == 0
                        ).OnlyEnforceIf(subsequent_assigned)

                for sec in (
                    ctx.master_timetable.course_to_sections
                    .get(subsequent, [])
                ):

                    if not ctx.section_in_semester(
                        sec,
                        ctx.semester2_blocks
                    ):

                        model.Add(
                            ctx.x[
                                (
                                    student.id,
                                    subsequent,
                                    sec.id
                                )
                            ] == 0
                        ).OnlyEnforceIf(prereq_assigned)
