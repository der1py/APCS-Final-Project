"""Full schedule soft-goal variables for the student timetable model."""

from solver.student_constraints.base import HardConstraint


class FullScheduleConstraint(HardConstraint):
    """Create variables that indicate whether each student has 8 courses."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for student in ctx.students:
            assigned_count = sum(
                ctx.assigned_all_by_student[student.id]
            )

            full_schedule = model.NewBoolVar(
                f"full_schedule_{student.id}"
            )

            model.Add(
                assigned_count >= 8
            ).OnlyEnforceIf(full_schedule)

            model.Add(
                assigned_count <= 7
            ).OnlyEnforceIf(full_schedule.Not())

            ctx.full_schedule_vars.append(full_schedule)
