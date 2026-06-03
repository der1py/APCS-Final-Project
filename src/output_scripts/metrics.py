from collections import Counter

from data.data_loader import load_simultaneous_blocking_rules

# student metrics 
# =====================================================
# REQUEST COMPLETION %
# =====================================================

def calculate_request_completion(students, all_schedules):

    total_requests = 0
    placed_requests = 0

    for student in students:

        total_requests += len(student.main_courses)

        sched = all_schedules.get(student.id, {})

        for course in student.main_courses:

            if course in sched:
                placed_requests += 1

    return (placed_requests / total_requests) * 100

# =====================================================
# 7–8/8 REQUESTED COURSES
# =====================================================

def calculate_7_to_8_requested_percent(students, all_schedules):
    successful = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        placed = sum(
            1
            for course in student.main_courses
            if course in sched
        )

        if placed >= 7:
            successful += 1

    return (
        successful / len(students)
    ) * 100

# =====================================================
# 8/8 COURSES (REQUESTED OR ALTERNATE)
# =====================================================

def calculate_8_of_8_with_alternates_percent(students, all_schedules):
    successful = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        if len(sched) >= 8:
            successful += 1

    return (
        successful / len(students)
    ) * 100

# =====================================================
# STUDENTS WITH TIMETABLE CONFLICTS
# =====================================================

def calculate_students_with_conflicts(
    all_schedules
):
    conflicts = 0

    for sched in all_schedules.values():

        used_blocks = set()

        for course, (section, block) in sched.items():

            if block in used_blocks:
                conflicts += 1
                break

            used_blocks.add(block)

    return conflicts

# =====================================================
# UNASSIGNED COURSE REQUESTS
# =====================================================

def calculate_unassigned_requests(students,all_schedules):
    unassigned = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        for course in student.main_courses:

            if course not in sched:
                unassigned += 1

    return unassigned

# Enrollment metrics 
# =====================================================
# STUDENTS REGISTERED IN EACH SECTION
# =====================================================

def calculate_section_enrollment(section_enrollment):
    return section_enrollment

# =====================================================
# TOTAL NUMBER OF SECTIONS
# =====================================================

def calculate_total_sections(sections):
    return len(sections)

# =====================================================
# FULL SECTIONS
# =====================================================

def calculate_full_sections(sections, section_enrollment, section_capacity):
    count = 0

    for sec in sections:

        enrolled = section_enrollment.get(
            sec.id,
            0
        )

        capacity = section_capacity.get(
            sec.id,
            0
        )

        if enrolled >= capacity:
            count += 1

    return count

# =====================================================
# SECTIONS BELOW 50% ENROLLMENT
# =====================================================

def calculate_under_half_sections(sections, section_enrollment, section_capacity):
    count = 0

    for sec in sections:

        enrolled = section_enrollment.get(
            sec.id,
            0
        )

        capacity = section_capacity.get(
            sec.id,
            0
        )

        if capacity > 0:

            if enrolled < capacity * 0.5:
                count += 1

    return count

# timetable metrics 
# =====================================================
# ROOM CONFLICTS
# =====================================================

def calculate_room_conflicts(sections, section_to_block):
    room_usage = {}

    conflicts = 0

    for sec in sections:

        key = (
            sec.room_id,
            section_to_block[sec.id]
        )

        room_usage.setdefault(key, 0)
        room_usage[key] += 1

    for count in room_usage.values():

        if count > 1:
            conflicts += count - 1

    return conflicts

# =====================================================
# STUDENT CONFLICTS
# =====================================================

def calculate_student_conflicts(
    all_schedules
):
    conflicts = 0

    for sched in all_schedules.values():

        blocks = []

        for course, (section, block) in sched.items():
            blocks.append(block)

        if len(blocks) != len(set(blocks)):
            conflicts += 1

    return conflicts

# =====================================================
# INVALID ROOM ASSIGNMENTS
# =====================================================

def calculate_invalid_room_assignments(
    sections
):
    invalid = 0

    for sec in sections:

        if sec.room_id is None:
            invalid += 1

    return invalid

# =====================================================
# BLOCK DISTRIBUTION
# =====================================================

def calculate_block_distribution(section_to_block):
    counts = Counter(section_to_block.values())
    return ", ".join([f"Block {block}: {count}" for block, count in sorted(counts.items())])

# =====================================================
# BLOCKING RULE VIOLATION %
# =====================================================

def calculate_blocking_rule_violation_percent(
    course_to_sections,
    section_to_block
):
    blocking_rules = load_simultaneous_blocking_rules()

    total_rules = 0
    violations = 0

    for blocking_type, pairs in blocking_rules.items():

        for c1, c2 in pairs:

            if c1 not in course_to_sections:
                continue

            if c2 not in course_to_sections:
                continue

            sec_list_1 = course_to_sections[c1]
            sec_list_2 = course_to_sections[c2]

            min_len = min(
                len(sec_list_1),
                len(sec_list_2)
            )

            for i in range(min_len):

                total_rules += 1

                s1 = sec_list_1[i]
                s2 = sec_list_2[i]

                if (
                    section_to_block[s1.id]
                    !=
                    section_to_block[s2.id]
                ):
                    violations += 1

    if total_rules == 0:
        return 0

    return (violations / total_rules) * 100

# =====================================================
# SEQUENCING RULE VIOLATION %
# =====================================================

def calculate_sequencing_rule_violation_percent(
    course_to_sections,
    section_to_block
):
    """
    Placeholder metric.

    Sequencing constraints have not yet been implemented
    in the timetable generator, so this metric currently
    returns 0%.

    Future implementation should count the percentage
    of sequencing constraints that are violated.
    """

    return 0.0

# =====================================================
# FULL TIMETABLE % -- done in main
# =====================================================

def calculate_full_schedules(students, all_schedules):

    successful_students = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        placed = 0

        for course in student.main_courses:

            if course in sched:
                placed += 1

        if placed == len(student.main_courses):
            successful_students += 1

    return (successful_students / len(students)) * 100


# =====================================================
# HALF FULL TIMETABLE % -- done in main
# =====================================================

def calculate_half_full_schedules(students, all_schedules):

    successful_students = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        placed = 0

        for course in student.main_courses:

            if course in sched:
                placed += 1

        if placed >= 4:
            successful_students += 1

    return (successful_students / len(students)) * 100


# helper methods for optimization score 
# =====================================================
# REQUEST SCORE
# +10 per placed course
# =====================================================

def calculate_request_score(all_schedules, students):

    score = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        for course in student.main_courses:

            if course in sched:
                score += 10

    return score


# =====================================================
# FULL TIMETABLE SCORE
# +50 if student gets complete timetable
# =====================================================

def calculate_full_timetable_score(all_schedules, students):

    score = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        placed = 0

        for course in student.main_courses:

            if course in sched:
                placed += 1

        if placed == len(student.main_courses):
            score += 50

    return score


# =====================================================
# STUDENT CONFLICT PENALTY
# -1000 for duplicate block
# =====================================================

def calculate_student_conflicts(all_schedules):

    penalty = 0

    for student_id, sched in all_schedules.items():

        used_blocks = set()

        for course, (sec, block) in sched.items():

            if block in used_blocks:
                penalty -= 1000
            else:
                used_blocks.add(block)

    return penalty


# =====================================================
# OVERFILLED SECTION PENALTY
# =====================================================

def calculate_overfilled_penalty(sections, section_enrollment, section_capacity):

    penalty = 0

    for sec in sections:

        sec_id = sec.id

        if sec_id not in section_capacity:
            continue

        if section_enrollment[sec_id] > section_capacity[sec_id]:
            penalty -= 1000

    return penalty


# =====================================================
# BALANCED BLOCKS SCORE
# +1 for each balanced block
# =====================================================

def calculate_balanced_blocks(section_to_block):

    counts = Counter(section_to_block.values())

    values = list(counts.values())

    average = sum(values) / len(values)

    score = 0

    for count in values:

        if abs(count - average) <= 1:
            score += 1

    return score


# =====================================================
# TOTAL OPTIMIZATION SCORE
# =====================================================

def calculate_optimization_score(students, all_schedules, sections, section_enrollment, section_capacity, section_to_block):

    score = 0

    score += calculate_request_score(
        all_schedules,
        students
    )

    score += calculate_full_timetable_score(
        all_schedules,
        students
    )

    score += calculate_student_conflicts(
        all_schedules
    )

    score += calculate_overfilled_penalty(
        sections,
        section_enrollment,
        section_capacity
    )

    score += calculate_balanced_blocks(
        section_to_block
    )

    return score