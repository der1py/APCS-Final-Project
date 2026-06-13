"""Special room sharing rule for the linear concert band room."""

from solver.constraints.base import HardConstraint


BAND_ROOM_ID = "119"
BAND_ROOM_SHARED_CAPACITY = 2


class BandRoomSharingConstraint(HardConstraint):
    """Allow room 119 sharing only between linear concert band groups."""

    def apply(self, ctx) -> None:
        model = ctx.model

        if BAND_ROOM_ID not in ctx.all_rooms:
            return

        band_groups = {
            gid
            for gid, sections in ctx.group_sections.items()
            if self._is_linear_concert_band_group(ctx, sections)
        }

        for block in ctx.blocks:
            room_vars = [
                ctx.z[(gid, BAND_ROOM_ID, block)]
                for gid in ctx.group_sections
                if (gid, BAND_ROOM_ID, block) in ctx.z
            ]

            non_band_room_vars = [
                ctx.z[(gid, BAND_ROOM_ID, block)]
                for gid in ctx.group_sections
                if (
                    (gid, BAND_ROOM_ID, block) in ctx.z
                    and gid not in band_groups
                )
            ]

            if not room_vars:
                continue

            model.Add(sum(room_vars) <= BAND_ROOM_SHARED_CAPACITY)

            if non_band_room_vars:
                # If a non-band group uses the band room, it cannot share it.
                model.Add(sum(room_vars) + sum(non_band_room_vars) <= 2)

    def _is_linear_concert_band_group(self, ctx, sections) -> bool:
        for section in sections:
            course = ctx.course_lookup[section.course_code]
            name = course.name.upper()

            if not course.linear:
                return False

            if "CONCERT BAND" not in name:
                return False

        return True
