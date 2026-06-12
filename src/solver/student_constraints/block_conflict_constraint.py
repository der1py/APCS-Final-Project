"""Block conflict constraints for student section assignments."""

from itertools import combinations

from solver.student_constraints.base import HardConstraint


class BlockConflictConstraint(HardConstraint):
    """Prevent a student from taking two conflicting sections in one block."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for student in ctx.students:

            for block in range(8):

                block_vars = []

                for course_code in (
                    ctx.student_course_options[student.id]["all"]
                ):

                    for sec in (
                        ctx.master_timetable.course_to_sections
                        .get(course_code, [])
                    ):

                        if block in ctx.section_occupied(sec):

                            block_vars.append(
                                (
                                    course_code,
                                    ctx.x[
                                        (
                                            student.id,
                                            course_code,
                                            sec.id
                                        )
                                    ]
                                )
                            )

                for (c1, v1), (c2, v2) in combinations(block_vars, 2):

                    if ctx.is_notsim_pair(c1, c2):
                        continue

                    model.Add(
                        v1 + v2 <= 1
                    )
