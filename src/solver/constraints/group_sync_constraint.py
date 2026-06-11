"""Group synchronization hard constraint for the master timetable model."""

from solver.constraints.base import HardConstraint


class GroupSyncConstraint(HardConstraint):
    """Mirror section-block variables at the simultaneous-group level."""

    def apply(self, ctx) -> None:
        model = ctx.model

        # group-level block variables (mirror of x for group)
        x_group = {}
        ctx.x_group = x_group

        for gid, s_list in ctx.group_sections.items():

            # ensure group block var equals the first section's block var
            s0 = s_list[0]

            for b in ctx.blocks:
                xg = model.NewBoolVar(f"x_group_{gid}_{b}")
                x_group[(gid, b)] = xg
                model.Add(xg == ctx.x[(s0.id, b)])

            # enforce section-level synchronization: link every member to the
            # group's block var so all sections share the same block (O(n)).
            for s in s_list:
                for b in ctx.blocks:
                    model.Add(ctx.x[(s.id, b)] == x_group[(gid, b)])
