from collections import Counter


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
# FULL TIMETABLE %
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
# HALF FULL TIMETABLE %
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

def calculate_overfilled_penalty(
    sections,
    section_enrollment,
    section_capacity
):

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

def calculate_optimization_score(
    students,
    all_schedules,
    sections,
    section_enrollment,
    section_capacity,
    section_to_block
):

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
