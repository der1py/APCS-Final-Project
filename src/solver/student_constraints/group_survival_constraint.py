"""Enrollment group survival constraints for the student timetable model."""

import math

from solver.student_constraints.base import HardConstraint


class GroupSurvivalConstraint(HardConstraint):
    """Track active enrollment groups and under-half penalties."""

    def apply(self, ctx) -> None:
        model = ctx.model

        for gid, grouped_sections in ctx.group_sections.items():

            group_capacity = max(
                ctx.section_capacity[sec.id]
                for sec in grouped_sections
            )

            minimum = math.ceil(max(1, group_capacity) * 0.5)

            group_enrollment_var = model.NewIntVar(
                0,
                group_capacity,
                f"enrollment_{gid}"
            )

            ctx.group_enrollment[gid] = group_enrollment_var

            model.Add(
                group_enrollment_var
                ==
                sum(
                    ctx.enrollment[sec.id]
                    for sec in grouped_sections
                )
            )

            active = model.NewBoolVar(
                f"active_{gid}"
            )

            ctx.active_groups[gid] = active

            model.Add(
                group_enrollment_var >= 1
            ).OnlyEnforceIf(active)

            model.Add(
                group_enrollment_var == 0
            ).OnlyEnforceIf(active.Not())

            under_half_penalty = model.NewIntVar(
                0,
                minimum,
                f"under_half_penalty_{gid}"
            )

            model.Add(
                under_half_penalty
                >=
                minimum
                -
                group_enrollment_var
            ).OnlyEnforceIf(active)

            model.Add(
                under_half_penalty == 0
            ).OnlyEnforceIf(active.Not())

            ctx.under_half_penalties.append(
                under_half_penalty
            )

            for sec in grouped_sections:
                ctx.active[sec.id] = active
