from collections import defaultdict


def assign_rooms(
    master_timetable,
    course_lookup
):
    """
    Assign a room to every section.

    Rules:
    - Section must use one of the rooms allowed by its course
    - Two sections in the same block cannot use the same room
    """

    room_usage = defaultdict(set)

    unassigned = []

    for sec in master_timetable.sections:

        block = sec.time_slot

        course = course_lookup[
            sec.course_code
        ]

        assigned = False

        for room in course.rooms:

            if room not in room_usage[block]:

                sec.room_id = room

                room_usage[block].add(room)

                assigned = True

                break

        if not assigned:

            sec.room_id = None

            unassigned.append(sec.id)

    print("\nROOM ASSIGNMENTS\n")

    for sec in master_timetable.sections:

        print(
            f"{sec.id:20}"
            f"Block {sec.time_slot:<3}"
            f"Room {sec.room_id}"
        )

    if unassigned:

        print("\nUNASSIGNED ROOMS:")

        for sec_id in unassigned:
            print(sec_id)

    return unassigned