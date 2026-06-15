"""Room capacity and utilization tuning defaults for master timetable solving."""

DEFAULT_ROOM_CAPACITY = 1 # default number of groups per room
DEFAULT_ROOM_SPREAD_TARGET = 1

# Override room capacities for specific rooms as needed
ROOM_CAPACITY = {
    "114": 1,
    "119": 2,
    "203": 1,
    "Gym": 6,
    # "206": 400,
    "108": 20,
    "109": 20,
}

# tries to to force at least this many groups into the listed rooms
# thanks yufei and david's codex for the soft constraint
# TODO relic from the old days, do we even need ts anymore?
ROOM_SPREAD_TARGET = {
    "108": 6,
    "109": 6,
    "119": 2,
    "206": 4,
    "Gym": 4,
}


def get_room_capacity_map():
    """Return hard per-block room capacities."""

    return dict(ROOM_CAPACITY)


def get_room_spread_target_map():
    """Return soft desired per-block room occupancies."""

    return dict(ROOM_SPREAD_TARGET)
