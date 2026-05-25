def calculate_request_completion(students):
    total_requests = 0
    placed_requests = 0

    for student in students:
        total_requests += len(student.requests)

        for course in student.requests:
            if course in student.schedule:
                placed_requests += 1

    return (placed_requests / total_requests) * 100

def calculate_full_schedules(students):
    successful_students = 0

    for student in students:
        placed = 0

        for course in student.requests:
            if course in student.schedule:
                placed += 1

        if placed == 8:
            successful_students += 1

    return (successful_students / len(students)) * 100

def calculate_half_full_schedules(students):
    successful_students = 0

    for student in students:
        placed = 0

        for course in student.requests:
            if course in student.schedule:
                placed += 1

        if placed >= 4:
            successful_students += 1

    return (successful_students / len(students)) * 100

# Optimization score calculations
def calculate_request_score(all_schedules, students):

    score = 0

    for student, requests in students.items():

        scheduled_courses = all_schedules[student]

        for course in requests:

            if course in scheduled_courses:
                score += 10

    return score

def calculate_full_timetable_score(all_schedules, students):

    score = 0

    for student, requests in students.items():

        scheduled_courses = all_schedules[student]

        placed = 0

        for course in requests:

            if course in scheduled_courses:
                placed += 1

        if placed == 8:
            score += 50

    return score

def calculate_student_conflicts(all_schedules):

    penalty = 0

    for student, sched in all_schedules.items():

        used_blocks = set()

        for course, (sec, block) in sched.items():

            if block in used_blocks:

                penalty -= 1000

            else:
                used_blocks.add(block)

    return penalty

def calculate_overfilled_penalty(sections,
                                 section_enrollment,
                                 section_capacity):

    penalty = 0

    for sec in sections:

        if section_enrollment[sec] > section_capacity[sec]:

            penalty -= 1000

    return penalty

def calculate_room_conflicts(sections,
                             section_to_room,
                             section_to_block):

    penalty = 0

    used = {}

    for sec in sections:

        room = section_to_room[sec]
        block = section_to_block[sec]

        key = (room, block)

        if key in used:

            penalty -= 1000

        else:
            used[key] = sec

    return penalty

def calculate_invalid_room_penalty(sections,
                                section_to_room,
                                section_to_course,
                                course_to_valid_rooms):

    penalty = 0

    for sec in sections:

        course = section_to_course[sec]
        room = section_to_room[sec]

        if room not in course_to_valid_rooms[course]:

            penalty -= 500

    return penalty

from collections import Counter

def calculate_balanced_blocks(section_to_block):

    counts = Counter(section_to_block.values())

    values = list(counts.values())

    average = sum(values) / len(values)

    score = 0

    for count in values:

        if abs(count - average) <= 1:
            score += 1

    return score

def calculate_optimization_score(
    all_schedules,
    students,
    sections,
    section_enrollment,
    section_capacity,
    section_to_room,
    section_to_block,
    section_to_course,
    course_to_valid_rooms
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

    # score += calculate_overfilled_penalty(
    #     sections,
    #     section_enrollment,
    #     section_capacity
    # )

    # score += calculate_room_conflicts(
    #     sections,
    #     section_to_room,
    #     section_to_block
    # )

    # score += calculate_invalid_room_penalty(
    #     sections,
    #     section_to_room,
    #     section_to_course,
    #     course_to_valid_rooms
    # )

    score += calculate_balanced_blocks(
        section_to_block
    )

    return score