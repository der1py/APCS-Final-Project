"""Room capacity and utilization tuning defaults for master timetable solving."""

DEFAULT_ROOM_CAPACITY = 3
DEFAULT_ROOM_SPREAD_TARGET = 1


ROOM_CAPACITY = {
    "114": 1,
    "119": 2,
    "203": 1,
    "Gym": 200,
    "206": 400,
    "108": 20,
    "109": 20,
}


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
