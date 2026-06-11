"""Course blocking hard constraint for the master timetable model.

This module preserves the current rule-based blocking logic from
``master_timetable_builder.py``. The filename follows the requested migration
target; the existing builder logic handles all loaded blocking rule types.
"""

from solver.constraints.base import HardConstraint


class SimultaneousBlockingConstraint(HardConstraint):
    """Apply blocking rules directly to the shared CP-SAT model."""

    def apply(self, ctx) -> None:
        model = ctx.model

        print("\nADDING COURSE BLOCKING RULES...\n")

        for blocking_type, pairs in ctx.blocking_rules.items():

            print(f"Blocking Type: {blocking_type}")

            for c1, c2 in pairs:

                if c1 not in ctx.course_to_sections:
                    print(f"Missing course: {c1}")
                    continue

                if c2 not in ctx.course_to_sections:
                    print(f"Missing course: {c2}")
                    continue

                sec_list_1 = ctx.course_to_sections[c1]
                sec_list_2 = ctx.course_to_sections[c2]

                if blocking_type == "Simultaneous":
                    min_len = min(
                        len(sec_list_1),
                        len(sec_list_2)
                    )

                    for i in range(min_len):

                        s1 = sec_list_1[i]
                        s2 = sec_list_2[i]

                        for b in ctx.blocks:

                            model.Add(
                                ctx.x[(s1.id, b)] ==
                                ctx.x[(s2.id, b)]
                            )

                elif blocking_type == "NotSimultaneous":
                    min_len = min(
                        len(sec_list_1),
                        len(sec_list_2)
                    )

                    for i in range(min_len):

                        s1 = sec_list_1[i]
                        s2 = sec_list_2[i]

                        for b in ctx.blocks:

                            model.Add(
                                ctx.x[(s1.id, b)] ==
                                ctx.x[(s2.id, b)]
                            )

                elif blocking_type == "Consecutive":
                    model.Add(
                        sum(
                            ctx.x[(s.id, b)]
                            for s in sec_list_1
                            for b in ctx.semester1_blocks
                        ) >= 1
                    )

                    model.Add(
                        sum(
                            ctx.x[(s.id, b)]
                            for s in sec_list_2
                            for b in ctx.semester2_blocks
                        ) >= 1
                    )
