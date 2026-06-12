from collections import Counter, defaultdict

from data.data_loader import load_rules, load_simultaneous_blocking_rules
from models import rules


def _get_assigned_blocks(value):
    _, blocks = value
    if isinstance(blocks, list):
        return blocks
    if blocks is None:
        return []
    return [blocks]


def _get_notsim_pairs():
    blocking_rules = load_simultaneous_blocking_rules()
    return {
        frozenset((c1, c2))
        for c1, c2 in blocking_rules.get("NotSimultaneous", [])
    }


def _is_notsim_pair(c1, c2, notsim_pairs):
    return c1 != c2 and frozenset((c1, c2)) in notsim_pairs


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
# 8/8 COURSES (WITHOUT ALTERNATES)
# =====================================================

def calculate_8_of_8_without_alternates_percent(students, all_schedules):
    if not students:
        return 0.0

    successful = 0

    for student in students:

        if len(student.main_courses) != 8:
            continue

        sched = all_schedules.get(student.id, {})

        placed = sum(
            1
            for course in student.main_courses
            if course in sched
        )

        if placed == 8:
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
    notsim_pairs = _get_notsim_pairs()

    for sched in all_schedules.values():

        courses_by_block = defaultdict(list)

        for course, value in sched.items():
            for block in _get_assigned_blocks(value):

                if any(
                    not _is_notsim_pair(course, existing, notsim_pairs)
                    for existing in courses_by_block[block]
                ):
                    conflicts += 1
                    break

                courses_by_block[block].append(course)
            else:
                continue
            break

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


def _build_enrollment_groups(sections):
    section_by_id = {
        sec.id: sec
        for sec in sections
    }

    course_to_sections = defaultdict(list)

    for sec in sections:
        course_to_sections[sec.course_code].append(sec)

    groups = {}
    section_to_group = {}
    group_counter = 0
    blocking_rules = load_simultaneous_blocking_rules()

    for c1, c2 in blocking_rules.get("Simultaneous", []):

        if c1 not in course_to_sections:
            continue

        if c2 not in course_to_sections:
            continue

        sections_1 = course_to_sections[c1]
        sections_2 = course_to_sections[c2]

        for i in range(min(len(sections_1), len(sections_2))):
            s1 = sections_1[i]
            s2 = sections_2[i]

            g1 = section_to_group.get(s1.id)
            g2 = section_to_group.get(s2.id)

            if g1 is None and g2 is None:
                gid = f"group_{group_counter}"
                group_counter += 1
                groups[gid] = {s1.id, s2.id}
                section_to_group[s1.id] = gid
                section_to_group[s2.id] = gid

            elif g1 is not None and g2 is None:
                groups[g1].add(s2.id)
                section_to_group[s2.id] = g1

            elif g1 is None and g2 is not None:
                groups[g2].add(s1.id)
                section_to_group[s1.id] = g2

            elif g1 != g2:
                for sid in groups[g2]:
                    groups[g1].add(sid)
                    section_to_group[sid] = g1
                del groups[g2]

    for sec in sections:
        if sec.id in section_to_group:
            continue

        gid = f"group_{group_counter}"
        group_counter += 1
        groups[gid] = {sec.id}
        section_to_group[sec.id] = gid

    return {
        gid: [
            section_by_id[sid]
            for sid in sorted(section_ids)
        ]
        for gid, section_ids in groups.items()
    }


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

    for grouped_sections in _build_enrollment_groups(sections).values():

        enrolled = sum(
            section_enrollment.get(sec.id, 0)
            for sec in grouped_sections
        )

        capacity = max(
            section_capacity.get(sec.id, 0)
            for sec in grouped_sections
        )

        if enrolled >= capacity:
            count += 1

    return count

# =====================================================
# SECTIONS BELOW 50% ENROLLMENT
# =====================================================

def calculate_under_half_sections(sections, section_enrollment, section_capacity):
    count = 0

    for grouped_sections in _build_enrollment_groups(sections).values():

        enrolled = sum(
            section_enrollment.get(sec.id, 0)
            for sec in grouped_sections
        )

        capacity = max(
            section_capacity.get(sec.id, 0)
            for sec in grouped_sections
        )

        if capacity <= 0:
            continue

        if enrolled == 0:
            continue

        if enrolled < capacity * 0.5:
            count += 1

    return count

# timetable metrics 
# =====================================================
# ROOM CONFLICTS
# =====================================================

def calculate_room_conflicts(sections, section_to_block):
    # Room conflicts are group-level, not section-level: simultaneous
    # sections in the same enrollment group intentionally share a room/block.
    room_usage = defaultdict(set)

    for group_id, grouped_sections in _build_enrollment_groups(sections).items():

        for sec in grouped_sections:

            key = (
                sec.room_id,
                section_to_block[sec.id]
            )

            room_usage[key].add(group_id)

    conflicts = 0

    for group_ids in room_usage.values():

        # Count only different groups sharing the same room/block.
        if len(group_ids) > 1:
            conflicts += len(group_ids) - 1

    return conflicts

# =====================================================
# STUDENT CONFLICTS
# =====================================================

def calculate_student_conflicts(
    all_schedules
):
    conflicts = 0
    notsim_pairs = _get_notsim_pairs()

    for sched in all_schedules.values():

        courses_by_block = defaultdict(list)
        has_conflict = False

        for course, value in sched.items():
            for block in _get_assigned_blocks(value):

                if any(
                    not _is_notsim_pair(course, existing, notsim_pairs)
                    for existing in courses_by_block[block]
                ):
                    has_conflict = True
                    break

                courses_by_block[block].append(course)

            if has_conflict:
                break

        if has_conflict:
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
    semester1_blocks = {0, 1, 2, 3}
    semester2_blocks = {4, 5, 6, 7}

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

            if blocking_type == "Simultaneous":
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

            elif blocking_type == "NotSimultaneous":
                min_len = min(
                    len(sec_list_1),
                    len(sec_list_2)
                )

                for i in range(min_len):

                    s1 = sec_list_1[i]
                    s2 = sec_list_2[i]

                    total_rules += 1

                    if (
                        section_to_block[s1.id]
                        !=
                        section_to_block[s2.id]
                    ):
                        violations += 1

            elif blocking_type == "Consecutive":
                total_rules += 1

                first_in_sem1 = any(
                    section_to_block[s.id] in semester1_blocks
                    for s in sec_list_1
                )

                second_in_sem2 = any(
                    section_to_block[s.id] in semester2_blocks
                    for s in sec_list_2
                )

                if not (
                    first_in_sem1
                    and
                    second_in_sem2
                ):
                    violations += 1

    if total_rules == 0:
        return 0

    return (violations / total_rules) * 100

# =====================================================
# SEQUENCING RULE VIOLATION %
# =====================================================

def calculate_sequencing_rule_violation_percent(
    students,
    course_to_sections,
    section_to_block
):
        rules = load_rules()
        sequence_rules = rules.sequence_pairs

        # Match the demand calculation used by the solver
        sequence_demand = defaultdict(int)

        for student in students:

            requested = set(student.main_courses)

            for prereq, advanced in sequence_rules:

                if (
                    prereq in requested
                    and advanced in requested
                ):
                    sequence_demand[(prereq, advanced)] += 1

        semester1_blocks = {0, 1, 2, 3}
        semester2_blocks = {4, 5, 6, 7}

        total_rules = 0
        violations = 0

        for prereq, advanced in sequence_rules:

            demand = sequence_demand.get(
                (prereq, advanced),
                0
            )

            # Ignore rules the solver ignored
            if demand == 0:
                continue

            if prereq not in course_to_sections:
                continue

            if advanced not in course_to_sections:
                continue

            total_rules += 1

            prereq_in_sem1 = any(
                section_to_block[sec.id] in semester1_blocks
                for sec in course_to_sections[prereq]
            )

            advanced_in_sem2 = any(
                section_to_block[sec.id] in semester2_blocks
                for sec in course_to_sections[advanced]
            )

            if not (
                prereq_in_sem1
                and
                advanced_in_sem2
            ):
                violations += 1

        if total_rules == 0:
            return 0.0

        return (violations / total_rules) * 100

# =====================================================
# STUDENT SEQUENCING RULE VIOLATION %
# =====================================================
# Measures the ACTUAL per-student assignments (all_schedules),
# not just the master timetable. A pair counts as a checked rule
# whenever a student was assigned BOTH the prerequisite and the
# subsequent course. It is a violation when, for that student, the
# prerequisite is not placed in semester 1 (blocks 0-3) or the
# subsequent course is not placed in semester 2 (blocks 4-7).

def calculate_student_sequencing_violation_percent(
    students,
    all_schedules
):
    rules = load_rules()
    sequence_rules = rules.sequence_pairs

    semester1_blocks = {0, 1, 2, 3}
    semester2_blocks = {4, 5, 6, 7}

    total_rules = 0
    violations = 0

    for student in students:

        sched = all_schedules.get(student.id, {})

        for prereq, subsequent in sequence_rules:

            if prereq not in sched:
                continue

            if subsequent not in sched:
                continue

            total_rules += 1

            prereq_blocks = _get_assigned_blocks(sched[prereq])
            subsequent_blocks = _get_assigned_blocks(sched[subsequent])

            prereq_in_sem1 = any(
                b in semester1_blocks
                for b in prereq_blocks
            )

            subsequent_in_sem2 = any(
                b in semester2_blocks
                for b in subsequent_blocks
            )

            if not (prereq_in_sem1 and subsequent_in_sem2):
                violations += 1

    if total_rules == 0:
        return 0.0

    return (violations / total_rules) * 100
# =====================================================
# 0-2 UNFULFILLED COURSES
# =====================================================

def calculate_0_to_2_unfulfilled_percent(students, all_schedules):
    successful = 0

    for student in students:
        sched = all_schedules.get(student.id, {})
        unfulfilled = max(0, 8 - len(sched))

        if unfulfilled <= 2:
            successful += 1

    return (successful / len(students)) * 100 if students else 0.0


# =====================================================
# 3-8 UNFULFILLED COURSES
# =====================================================

def calculate_3_to_8_unfulfilled_percent(students, all_schedules):
    count = 0

    for student in students:
        sched = all_schedules.get(student.id, {})
        unfulfilled = max(0, 8 - len(sched))

        if 3 <= unfulfilled <= 8:
            count += 1

    return (count / len(students)) * 100 if students else 0.0
# =====================================================
# COURSES PER BLOCK
# =====================================================
def calculate_courses_per_block(course_to_sections, section_to_block):
    block_courses = defaultdict(set)

    for course_code, sections in course_to_sections.items():
        for sec in sections:
            block = section_to_block[sec.id]
            block_courses[block].add(course_code)

    return {
        block: len(courses)
        for block, courses in block_courses.items()
    }
def format_courses_per_block(block_courses):
    return ", ".join(
        f"Block {block}: {courses}"
        for block, courses in sorted(block_courses.items())
    )

# =====================================================
# BLOCK BALANCE DIFFERENCE
# =====================================================
def calculate_block_balance_difference(course_to_sections, section_to_block):
    courses_per_block = calculate_courses_per_block(course_to_sections, section_to_block)

    values = list(courses_per_block.values())

    return max(values) - min(values) if values else 0

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
    notsim_pairs = _get_notsim_pairs()

    for student_id, sched in all_schedules.items():

        courses_by_block = defaultdict(list)

        for course, value in sched.items():
            for block in _get_assigned_blocks(value):

                if any(
                    not _is_notsim_pair(course, existing, notsim_pairs)
                    for existing in courses_by_block[block]
                ):
                    penalty -= 1000
                else:
                    courses_by_block[block].append(course)

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
