import csv
from solver.master_timetable_builder import MasterTimetable


# =====================================================
# EXPORT MASTER TIMETABLE
# =====================================================

def export_master_timetable(master_timetable: MasterTimetable, courses, filename="master_timetable.csv"):

    blocks = list(range(8))

    course_name_map = {course.code: course.name for course in courses}

    block_data = {b: [] for b in blocks}

    # organize by block
    for sec in master_timetable.sections:
        block = sec.time_slot
        course_code = sec.course_code
        course_name = course_name_map.get(course_code, course_code)

        block_data[block].append(f"{course_name} ({sec.id})")

    # export csv
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        
        writer.writerow([f"Block {b}" for b in blocks])

        max_rows = max(len(block_data[b]) for b in blocks)

        for i in range(max_rows):
            row = []
            for b in blocks:
                if i < len(block_data[b]):
                    row.append(block_data[b][i])
                else:
                    row.append("")
            writer.writerow(row)