import csv
import json
from pathlib import Path


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

    for sec_id, block in section_to_block.items():
        if block in master_timetable_display:
            # determine course code for this section id
            course_code = None

            if master_timetable is not None and hasattr(master_timetable, "section_by_id"):
                sec_obj = master_timetable.section_by_id.get(sec_id)
                if sec_obj is not None:
                    course_code = getattr(sec_obj, "course_code", None)

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
    # legacy exporter (codes)
    export_student_csv_code(students, all_schedules, blocks, master_timetable=master_timetable)

    # name-based exporter (requires courses list)
    if courses is not None:
        export_student_csv(students, all_schedules, courses, blocks, "src/output/student_schedules_by_name.csv", master_timetable=master_timetable)

    export_master_json(master_timetable)
    export_student_json(all_schedules)

    print("Files exported successfully.")