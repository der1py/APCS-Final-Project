import csv
import json
from pathlib import Path


# =====================================================
# MASTER TIMETABLE EXPORT (CSV)
# =====================================================

def export_master_csv(section_to_block, blocks,
                      output_path="src/output/master_timetable.csv"):

    blocks = list(blocks)
    master_timetable = {b: [] for b in blocks}

    for sec_id, block in section_to_block.items():
        if block in master_timetable:
            master_timetable[block].append(sec_id)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([f"Block {b}" for b in blocks])

        max_rows = max(len(master_timetable[b]) for b in blocks)

        for i in range(max_rows):
            row = []

            for b in blocks:
                if i < len(master_timetable[b]):
                    row.append(master_timetable[b][i])
                else:
                    row.append("")

            writer.writerow(row)


# =====================================================
# STUDENT SCHEDULES EXPORT (CSV)
# =====================================================

def export_student_csv(students, all_schedules, blocks,
                       output_path="src/output/student_schedules.csv"):

    blocks = list(blocks)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["Student"] + [f"Block {b}" for b in blocks])

        for student in students:
            schedule = all_schedules.get(student.id, {})

            row = [student.id] + ["unassigned" for _ in blocks]

            for course, value in schedule.items():
                section, block = value

                if block in blocks:
                    block_index = blocks.index(block)
                    row[block_index + 1] = course

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
            section, block = value

            if block == -1:
                clean_block = "unassigned"
            else:
                clean_block = block

            if section is None:
                clean_section = None
            else:
                clean_section = section.id

            clean_schedules[student_id][course] = {
                "section": clean_section,
                "block": clean_block
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
               all_schedules):

    blocks = list(blocks)

    export_master_csv(section_to_block, blocks)
    export_student_csv(students, all_schedules, blocks)

    export_master_json(master_timetable)
    export_student_json(all_schedules)

    print("Files exported successfully.")