"""
Test harness for student timetable builder.

Loads a pre-generated master timetable JSON (from CP-SAT) and runs ONLY
the student assignment phase to isolate bugs in the student timetable builder.
"""

import json
import random
from pathlib import Path
from collections import defaultdict

from models.section import Section
from models.student import Student
from models.course import Course
from solver.master_timetable_builder import MasterTimetable
from solver.student_timetable_builder import generate_all_student_schedules
from data.data_loader import load_students
from data.course_loader import load_courses_from_csv
from validator import validate_courses, validate_students


# =====================================================
# LOAD MASTER TIMETABLE FROM JSON
# =====================================================

def load_master_timetable_json(json_path):
    """
    Load the master timetable JSON and reconstruct the MasterTimetable object.
    
    Returns: MasterTimetable object with sections, mappings, etc.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    section_to_block = data['section_to_block']
    
    # Parse section IDs to reconstruct Section objects
    sections = []
    course_to_sections = defaultdict(list)
    section_by_id = {}
    
    for section_id, block in section_to_block.items():
        # Parse section_id: format is "{course_code}_{section_num}"
        # e.g., "ACAL-12---_1" -> course_code="ACAL-12---", num=1
        parts = section_id.rsplit('_', 1)
        if len(parts) != 2:
            print(f"WARNING: Could not parse section_id: {section_id}")
            continue
        
        course_code = parts[0]
        try:
            section_num = int(parts[1])
        except ValueError:
            print(f"WARNING: Could not parse section number in: {section_id}")
            continue
        
        # Create Section object
        sec = Section(
            id=section_id,
            course_code=course_code,
            time_slot=block,
            room_id=None  # Not stored in JSON, will remain None
        )
        
        sections.append(sec)
        course_to_sections[course_code].append(sec)
        section_by_id[section_id] = sec
    
    # Convert defaultdicts to regular dicts
    course_to_sections = dict(course_to_sections)
    
    return MasterTimetable(
        sections=sections,
        section_to_block=section_to_block,
        course_to_sections=course_to_sections,
        section_by_id=section_by_id
    )


# =====================================================
# MAIN TEST
# =====================================================

def main():
    print("="*70)
    print("STUDENT TIMETABLE BUILDER TEST")
    print("="*70)
    
    # Load master timetable from JSON
    json_path = Path(__file__).resolve().parent / "output" / "json" / "master_timetable.json"
    print(f"\nLoading master timetable from: {json_path}")
    
    master_timetable = load_master_timetable_json(json_path)
    
    # =====================================================
    # LOAD AND VALIDATE DATA
    # =====================================================
    
    print("\nLoading students and courses...")
    students = load_students()
    courses = load_courses_from_csv()
    
    print(f"Students loaded: {len(students)}")
    print(f"Courses loaded: {len(courses)}")
    
    # Validate
    valid_courses, invalid_courses = validate_courses(courses)
    print(f"Valid courses: {len(valid_courses)}, Invalid: {len(invalid_courses)}")
    
    students = validate_students(students, valid_courses)
    print(f"Valid students (after cleaning): {len(students)}")
    
    courses = list(valid_courses.values())
    
    # =====================================================
    # DEBUG: MASTER TIMETABLE STATS
    # =====================================================
    
    print(f"\n--- Master Timetable Statistics ---")
    print(f"Total sections in master timetable: {len(master_timetable.sections)}")
    
    sections_per_course = defaultdict(int)
    for sec in master_timetable.sections:
        sections_per_course[sec.course_code] += 1
    
    print(f"Courses with sections: {len(sections_per_course)}")
    print(f"Average sections per course: {len(master_timetable.sections) / len(sections_per_course):.1f}")
    
    # Check for invalid sections
    invalid_sections = 0
    for sec in master_timetable.sections:
        if sec.time_slot < 0 or sec.time_slot > 7:
            invalid_sections += 1
            print(f"  INVALID BLOCK: {sec.id} -> {sec.time_slot}")
    
    print(f"Sections with invalid/missing block: {invalid_sections}")
    print(f"Sections with missing room: {sum(1 for s in master_timetable.sections if s.room_id is None)}")
    
    # =====================================================
    # CREATE SECTION CAPACITY
    # =====================================================
    
    course_lookup = {c.code: c for c in courses}
    
    print(f"\n--- Course enrollment_max Values ---")
    sample_courses = list(course_lookup.values())[:5]
    for c in sample_courses:
        print(f"  {c.code}: enrollment_max={c.enrollment_max}, num_sections={c.num_sections}")
    
    section_capacity = {
        sec.id: course_lookup[sec.course_code].enrollment_max
        for sec in master_timetable.sections
        if sec.course_code in course_lookup
    }
    
    print(f"Section capacity dict size: {len(section_capacity)}")
    if section_capacity:
        sample_caps = list(section_capacity.values())[:10]
        print(f"Sample section capacities: {sample_caps}")
    
    # =====================================================
    # STUDENT COURSE REQUESTS
    # =====================================================
    
    total_requests = sum(len(s.main_courses) for s in students)
    print(f"\n--- Student Requests ---")
    print(f"Total students: {len(students)}")
    print(f"Total main course requests: {total_requests}")
    print(f"Average requests per student: {total_requests / len(students):.1f}")
    
    # =====================================================
    # RUN STUDENT TIMETABLE BUILDER
    # =====================================================
    
    print(f"\n--- Running Student Timetable Builder ---")
    all_schedules, section_enrollment = generate_all_student_schedules(
        students,
        master_timetable,
        section_capacity
    )
    
    # =====================================================
    # RESULTS
    # =====================================================
    
    print(f"\n--- Student Assignment Results ---")
    
    total_assigned = sum(len(sched) for sched in all_schedules.values())
    print(f"Total courses assigned: {total_assigned}/{total_requests}")
    print(f"Assignment rate: {100 * total_assigned / total_requests:.1f}%")
    
    unassigned_students = sum(1 for s in students if len(all_schedules[s.id]) == 0)
    print(f"Completely unassigned students: {unassigned_students}/{len(students)}")
    
    assignment_distribution = defaultdict(int)
    for student in students:
        num_assigned = len(all_schedules[student.id])
        assignment_distribution[num_assigned] += 1
    
    print(f"\nAssignment distribution:")
    for num_assigned in sorted(assignment_distribution.keys()):
        count = assignment_distribution[num_assigned]
        print(f"  {num_assigned} courses: {count} students")
    
    # =====================================================
    # SAMPLE 5 RANDOM STUDENTS
    # =====================================================
    
    print(f"\n--- Sample of 5 Random Students ---")
    random_students = random.sample(students, min(5, len(students)))
    for student in random_students:
        schedule = all_schedules.get(student.id, {})
        num_assigned = len(schedule)
        print(f"Student {student.id}: {num_assigned}/{len(student.main_courses)} courses assigned")
        for course_code, (sec, block) in sorted(schedule.items()):
            print(f"  {course_code} -> Block {block}")
        if not schedule:
            print(f"  (no courses assigned)")
    
    # =====================================================
    # METRICS
    # =====================================================
    
    from output.output_scripts.metrics import calculate_request_completion, calculate_optimization_score
    
    req_completion = calculate_request_completion(students, all_schedules)
    
    # % of students with 8/8 requested courses placed
    count_8_of_8 = 0
    for s in students:
        sched = all_schedules.get(s.id, {})
        placed = sum(1 for c in s.main_courses if c in sched)
        if len(s.main_courses) == 8 and placed == 8:
            count_8_of_8 += 1
    
    percent_8_of_8 = (count_8_of_8 / len(students)) * 100 if students else 0
    
    # % of students with >=50% of requested courses placed
    count_half_or_more = 0
    for s in students:
        sched = all_schedules.get(s.id, {})
        placed = sum(1 for c in s.main_courses if c in sched)
        total = len(s.main_courses) if len(s.main_courses) > 0 else 1
        if (placed / total) >= 0.5:
            count_half_or_more += 1
    
    percent_half_or_more = (count_half_or_more / len(students)) * 100 if students else 0
    
    # Optimization score
    opt_score = calculate_optimization_score(
        students,
        all_schedules,
        master_timetable.sections,
        section_enrollment,
        {},
        master_timetable.section_to_block
    )
    
    print(f"\nRequest completion: {req_completion:.2f}%")
    print(f"Students with 8/8 placed: {percent_8_of_8:.2f}%")
    print(f"Students with >=50% placed: {percent_half_or_more:.2f}%")
    print(f"Optimization score: {opt_score}")
    
    # =====================================================
    # EXPORT RESULTS TO CSV
    # =====================================================
    
    import csv
    blocks = list(range(8))
    output_path = Path(__file__).resolve().parent / "output" / "student_schedules.csv"
    
    course_map = {c.code: c.name for c in courses}
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Student"] + [f"Block {b}" for b in blocks])
        
        for student in students:
            schedule = all_schedules.get(student.id, {})
            row = [student.id] + ["unassigned" for _ in blocks]
            
            for course_code, value in schedule.items():
                section, block = value
                display = course_map.get(course_code, course_code)
                if section is not None and section.room_id:
                    display = f"{display} (Room {section.room_id})"
                
                if block in blocks:
                    block_index = blocks.index(block)
                    row[block_index + 1] = display
            
            writer.writerow(row)
    
    print(f"\nExported student schedules to: {output_path}")


if __name__ == "__main__":
    main()