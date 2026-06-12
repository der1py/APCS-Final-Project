import csv
import json
from collections import defaultdict
from pathlib import Path


NO_ROOM_FOUND = "NO ROOM FOUND"


def _unpack_schedule_value(value):
    section_id, blocks = value
    if isinstance(blocks, int):
        blocks = [blocks]
    return section_id, list(blocks)


# =====================================================
# MASTER TIMETABLE EXPORT (CSV)
# =====================================================

def export_master_csv(section_to_block, blocks,
                      output_path="src/output/master_timetable.csv",
                      master_timetable=None,
                      courses=None,
                      section_enrollment=None):

    blocks = list(blocks)
    master_timetable_display = {b: [] for b in blocks}

    # optional course code -> name map
    course_map = {c.code: c.name for c in courses} if courses is not None else {}

    section_blocks_map = None
    if master_timetable is not None and hasattr(master_timetable, "section_to_blocks"):
        section_blocks_map = master_timetable.section_to_blocks

    for sec_id, block in section_to_block.items():
        section_blocks = [block]
        if section_blocks_map is not None and sec_id in section_blocks_map:
            section_blocks = section_blocks_map[sec_id]

        # use any available block for the course/section metadata lookup
        section_display_block = section_blocks[0] if section_blocks else block

        if section_display_block in master_timetable_display:
            # determine course code for this section id
            course_code = None
            sec_obj = None

            if master_timetable is not None and hasattr(master_timetable, "section_by_id"):
                sec_obj = master_timetable.section_by_id.get(sec_id)
                if sec_obj is not None:
                    course_code = getattr(sec_obj, "course_code", None)

            if sec_obj is not None and getattr(sec_obj, "cancelled", False):
                continue

            # fallback: try parsing from section id (prefix before first underscore)
            if course_code is None and isinstance(sec_id, str) and "_" in sec_id:
                course_code = sec_id.split("_")[0]

            # map to display name if available
            if course_code and course_map.get(course_code):
                display = course_map[course_code]
            else:
                display = sec_id

            if sec_obj is not None and sec_obj.room_id:
                display = f"{display} (Room {sec_obj.room_id})"

            count = 0
            if section_enrollment is not None:
                count = section_enrollment.get(sec_id, 0)

            display = f"{display} ({count} students)"

            for block in section_blocks:
                if block in master_timetable_display:
                    master_timetable_display[block].append(display)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([f"Block {b}" for b in blocks])

        max_rows = max(len(master_timetable_display[b]) for b in blocks)

        for i in range(max_rows):
            row = []

            for b in blocks:
                if i < len(master_timetable_display[b]):
                    row.append(master_timetable_display[b][i])
                else:
                    row.append("")

            writer.writerow(row)


# =====================================================
# ROOM TIMETABLE EXPORT (CSV)
# =====================================================

def export_room_timetable_csv(master_timetable,
                              blocks,
                              output_path="src/output/master_timetable_by_room.csv",
                              courses=None,
                              section_enrollment=None):

    blocks = sorted(list(blocks), key=int)
    room_block_grid = defaultdict(lambda: {b: [] for b in blocks})

    course_map = {c.code: c.name for c in courses} if courses is not None else {}
    section_blocks_map = getattr(master_timetable, "section_to_blocks", {})
    section_by_id = getattr(master_timetable, "section_by_id", {})

    for sec_id, block in master_timetable.section_to_block.items():
        sec_obj = section_by_id.get(sec_id)

        if sec_obj is not None and getattr(sec_obj, "cancelled", False):
            continue

        section_blocks = section_blocks_map.get(sec_id, [block])
        if isinstance(section_blocks, int):
            section_blocks = [section_blocks]

        room = getattr(sec_obj, "room_id", None) if sec_obj is not None else None
        room = NO_ROOM_FOUND if room is None or room == "" else str(room)

        course_code = getattr(sec_obj, "course_code", None) if sec_obj is not None else None
        if course_code is None and isinstance(sec_id, str) and "_" in sec_id:
            course_code = sec_id.split("_")[0]

        display = course_map.get(course_code, sec_id)
        count = section_enrollment.get(sec_id, 0) if section_enrollment is not None else 0
        display = f"{display} ({count} students)"

        for section_block in section_blocks:
            if section_block in blocks:
                room_block_grid[room][section_block].append(display)

    rooms = sorted(
        room
        for room in room_block_grid
        if room != NO_ROOM_FOUND
    )

    if NO_ROOM_FOUND in room_block_grid:
        rooms.append(NO_ROOM_FOUND)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([""] + [f"Block {b}" for b in blocks])

        for room in rooms:
            row = [room]

            for block in blocks:
                row.append("\n".join(room_block_grid[room][block]))

            writer.writerow(row)


# =====================================================
# STUDENT SCHEDULES EXPORT (CSV)
# =====================================================

def export_student_csv_code(students, all_schedules, blocks,
                           output_path="src/output/student_schedules.csv",
                           master_timetable=None):

    blocks = list(blocks)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["Student"] + [f"Block {b}" for b in blocks])

        for student in students:
            schedule = all_schedules.get(student.id, {})

            row = [student.id] + ["unassigned" for _ in blocks]

            for course, value in schedule.items():
                section_id, assigned_blocks = _unpack_schedule_value(value)

                display = course
                if master_timetable is not None and section_id is not None:
                    sec_obj = master_timetable.section_by_id.get(section_id)
                    if sec_obj is not None and sec_obj.room_id:
                        display = f"{display} (Room {sec_obj.room_id})"

                for block in assigned_blocks:
                    if block in blocks:
                        block_index = blocks.index(block)
                        row[block_index + 1] = display

            writer.writerow(row)


def export_student_csv(students, all_schedules, courses, blocks, output_path, master_timetable=None):
    """
    Export student schedules with course NAMES instead of codes.

    Parameters:
    - students: iterable of student objects (must have .id)
    - all_schedules: dict mapping student_id -> {course_code: (section_id, blocks)}
    - courses: list of course objects with .code and .name
    - blocks: iterable of blocks
    - output_path: path to write CSV
    - master_timetable: optional MasterTimetable for section metadata
    """

    blocks = list(blocks)

    # build code -> name map
    course_map = {c.code: c.name for c in courses}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["Student"] + [f"Block {b}" for b in blocks])

        for student in students:
            schedule = all_schedules.get(student.id, {})

            row = [student.id] + ["unassigned" for _ in blocks]

            for course_code, value in schedule.items():
                section_id, assigned_blocks = _unpack_schedule_value(value)

                display = course_map.get(course_code, course_code)
                if master_timetable is not None and section_id is not None:
                    sec_obj = master_timetable.section_by_id.get(section_id)
                    if sec_obj is not None and sec_obj.room_id:
                        display = f"{display} (Room {sec_obj.room_id})"

                for block in assigned_blocks:
                    if block in blocks:
                        block_index = blocks.index(block)
                        row[block_index + 1] = display

            writer.writerow(row)


# =====================================================
# MASTER TIMETABLE EXPORT (JSON)
# =====================================================

def export_master_json(master_timetable,
                       output_path="src/output/json/master_timetable.json"):

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    data = {
        "section_to_block": master_timetable.section_to_block
    }

    if hasattr(master_timetable, "section_to_blocks"):
        data["section_to_blocks"] = master_timetable.section_to_blocks

    if hasattr(master_timetable, "sections"):
        data["cancelled_sections"] = [
            sec.id
            for sec in master_timetable.sections
            if getattr(sec, "cancelled", False)
        ]

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


# =====================================================
# STUDENT SCHEDULES EXPORT (JSON)
# =====================================================

def export_student_json(all_schedules,
                        output_path="src/output/json/student_schedules.json"):

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    clean_schedules = {}

    for student_id, schedule in all_schedules.items():
        clean_schedules[student_id] = {}

        for course, value in schedule.items():
            section_id, blocks = _unpack_schedule_value(value)
            clean_schedules[student_id][course] = {
                "section": section_id,
                "blocks": blocks if blocks else ["unassigned"]
            }

    with open(output_path, "w") as f:
        json.dump(clean_schedules, f, indent=2)


# =====================================================
# MASTER EXPORT WRAPPER
# =====================================================

def export_all(students,
               section_to_block,
               blocks,
               master_timetable,
               all_schedules,
               courses=None,
               section_enrollment=None):

    blocks = list(blocks)

    export_master_csv(
        section_to_block,
        blocks,
        master_timetable=master_timetable,
        courses=courses,
        section_enrollment=section_enrollment,
    )
    export_room_timetable_csv(
        master_timetable,
        blocks,
        courses=courses,
        section_enrollment=section_enrollment,
    )
    # legacy exporter (codes)
    export_student_csv_code(students, all_schedules, blocks, master_timetable=master_timetable)

    # name-based exporter (requires courses list)
    if courses is not None:
        export_student_csv(students, all_schedules, courses, blocks, "src/output/student_schedules_by_name.csv", master_timetable=master_timetable)

    export_master_json(master_timetable)
    export_student_json(all_schedules)

    print("Files exported successfully.")
