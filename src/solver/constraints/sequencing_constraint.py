"""Course sequencing hard constraint for the master timetable model."""

import math

from solver.constraints.base import HardConstraint


class SequencingConstraint(HardConstraint):
    """Require enough prerequisite sections in semester 1 and advanced in 2."""

    def apply(self, ctx) -> None:
        model = ctx.model

        print("\nADDING COURSE SEQUENCING RULES...\n")

        for prereq, advanced in ctx.sequence_rules:

            demand = ctx.sequence_demand.get(
                (prereq, advanced),
                0
            )

            if demand == 0:
                continue

            if prereq not in ctx.course_to_sections:
                continue

            if advanced not in ctx.course_to_sections:
                continue

            prereq_sections = ctx.course_to_sections[prereq]
            advanced_sections = ctx.course_to_sections[advanced]

            # estimate sections needed

            prereq_course = ctx.course_lookup[prereq]

            DEFAULT_SECTION_SIZE = 30

            capacity = prereq_course.enrollment_max

            if capacity <= 0:
                capacity = DEFAULT_SECTION_SIZE

            required_sections = math.ceil(
                demand / capacity
            )

            print(
                f"{prereq} -> {advanced}"
                f" demand={demand}"
                f" sections_needed={required_sections}"
            )

            # ==========================================
            # prerequisite sections in semester 1
            # ==========================================

            prereq_sem1_vars = []

            for sec in prereq_sections:

                v = model.NewBoolVar(
                    f"sem1_{sec.id}"
                )

                model.Add(
                    v ==
                    sum(
                        ctx.x[(sec.id, b)]
                        for b in ctx.semester1_blocks
                    )
                )

                prereq_sem1_vars.append(v)

            model.Add(
                sum(prereq_sem1_vars)
                >= required_sections
            )

            # ==========================================
            # advanced sections in semester 2
            # ==========================================

            advanced_sem2_vars = []

            for sec in advanced_sections:

                v = model.NewBoolVar(
                    f"sem2_{sec.id}"
                )

                model.Add(
                    v ==
                    sum(
                        ctx.x[(sec.id, b)]
                        for b in ctx.semester2_blocks
                    )
                )

                advanced_sem2_vars.append(v)

            model.Add(
                sum(advanced_sem2_vars)
                >= required_sections
            )
