from collections import defaultdict
from ortools.sat.python import cp_model
import math

from data.data_loader import load_rules, load_simultaneous_blocking_rules


def build_student_timetables(
    students,
    master_timetable,
    course_lookup
):

    model = cp_model.CpModel()

    # =====================================================
    # SEMESTER BLOCK SETS
    # =====================================================
    # Mirrors master_timetable_builder: blocks 0-3 are semester 1,
    # blocks 4-7 are semester 2. Used by the sequencing constraint
    # below so prerequisites land in semester 1 and subsequent
    # courses land in semester 2 for every student.

    semester1_blocks = {0, 1, 2, 3}
    semester2_blocks = {4, 5, 6, 7}

    def section_occupied(sec):
        occupied = getattr(sec, "occupied_blocks", None)
        if not occupied:
            occupied = [sec.time_slot]
        return occupied

    def section_in_semester(sec, semester_blocks):
        return any(
            b in semester_blocks
            for b in section_occupied(sec)
        )

    def unique_courses(courses):
        seen = set()
        result = []

        for course_code in courses:
            if course_code in seen:
                continue

            seen.add(course_code)
            result.append(course_code)

        return result

    def build_enrollment_groups():
        blocking_rules = load_simultaneous_blocking_rules()

        groups = {}
        section_to_group = {}
        group_counter = 0

        for c1, c2 in blocking_rules.get("Simultaneous", []):

            if c1 not in master_timetable.course_to_sections:
                continue

            if c2 not in master_timetable.course_to_sections:
                continue

            sections_1 = master_timetable.course_to_sections[c1]
            sections_2 = master_timetable.course_to_sections[c2]

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

        for sec in master_timetable.sections:
            if sec.id in section_to_group:
                continue

            gid = f"group_{group_counter}"
            group_counter += 1
            groups[gid] = {sec.id}
            section_to_group[sec.id] = gid

        group_sections = {
            gid: [
                master_timetable.section_by_id[sid]
                for sid in sorted(section_ids)
            ]
            for gid, section_ids in groups.items()
        }

        return group_sections, section_to_group

    student_course_options = {}

    for student in students:
        main_courses = unique_courses(student.main_courses)
        alternate_courses = [
            course_code
            for course_code in unique_courses(getattr(student, "alt_courses", []))
            if course_code not in main_courses
        ]

        student_course_options[student.id] = {
            "main": main_courses,
            "alternate": alternate_courses,
            "all": main_courses + alternate_courses,
        }

    # =====================================================
    # SECTION CAPACITY
    # =====================================================

    section_capacity = {}

    for sec in master_timetable.sections:

        course = course_lookup[sec.course_code]

        capacity = course.enrollment_max

        if capacity <= 0:
            capacity = 30

        section_capacity[sec.id] = capacity

    group_sections, section_to_group = build_enrollment_groups()

    # =====================================================
    # ASSIGNMENT VARIABLES
    # =====================================================

    x = {}

    for student in students:

        for course_code in student_course_options[student.id]["all"]:

            sections = (
                master_timetable.course_to_sections
                .get(course_code, [])
            )

            for sec in sections:

                x[
                    (
                        student.id,
                        course_code,
                        sec.id
                    )
                ] = model.NewBoolVar(
                    f"x_{student.id}_{sec.id}"
                )

    # =====================================================
    # COURSE ASSIGNMENT
    # =====================================================

    assigned_course_vars = []
    assigned_alternate_vars = []
    assigned_by_course = {}
    assigned_main_by_student = defaultdict(list)
    assigned_alternate_by_student = defaultdict(list)
    assigned_all_by_student = defaultdict(list)

    for student in students:

        for course_code in student_course_options[student.id]["all"]:

            vars_for_course = []

            for sec in (
                master_timetable.course_to_sections
                .get(course_code, [])
            ):

                vars_for_course.append(
                    x[
                        (
                            student.id,
                            course_code,
                            sec.id
                        )
                    ]
                )

            if not vars_for_course:
                continue

            assigned = model.NewBoolVar(
                f"assigned_{student.id}_{course_code}"
            )

            model.Add(
                sum(vars_for_course) == assigned
            )

            assigned_by_course[(student.id, course_code)] = assigned
            assigned_all_by_student[student.id].append(
                assigned
            )

            if course_code in student_course_options[student.id]["main"]:
                assigned_course_vars.append(
                    assigned
                )
                assigned_main_by_student[student.id].append(
                    assigned
                )

            else:
                assigned_alternate_vars.append(
                    assigned
                )
                assigned_alternate_by_student[student.id].append(
                    assigned
                )

    for student in students:
        main_count = len(student_course_options[student.id]["main"])

        model.Add(
            sum(assigned_alternate_by_student[student.id])
            <=
            main_count
            -
            sum(assigned_main_by_student[student.id])
        )

    # =====================================================
    # 8/8 SCHEDULE COMPLETION
    # =====================================================

    full_schedule_vars = []

    for student in students:
        assigned_count = sum(assigned_all_by_student[student.id])

        full_schedule = model.NewBoolVar(
            f"full_schedule_{student.id}"
        )

        model.Add(
            assigned_count >= 8
        ).OnlyEnforceIf(full_schedule)

        model.Add(
            assigned_count <= 7
        ).OnlyEnforceIf(full_schedule.Not())

        full_schedule_vars.append(full_schedule)

    # =====================================================
    # BLOCK CONFLICTS
    # =====================================================

    for student in students:

        for block in range(8):

            block_vars = []

            for course_code in student_course_options[student.id]["all"]:

                for sec in (
                    master_timetable.course_to_sections
                    .get(course_code, [])
                ):

                    occupied = getattr(
                        sec,
                        "occupied_blocks",
                        [sec.time_slot]
                    )

                    if block in occupied:

                        block_vars.append(
                            x[
                                (
                                    student.id,
                                    course_code,
                                    sec.id
                                )
                            ]
                        )

            model.Add(
                sum(block_vars)
                <= 1
            )

    # =====================================================
    # COURSE SEQUENCING RULES
    # =====================================================
    # Mirror of master_timetable_builder C7, applied per student:
    # whenever a student requests both a prerequisite and its
    # subsequent course, the prerequisite must be placed in
    # semester 1 (blocks 0-3) and the subsequent course in
    # semester 2 (blocks 4-7).
    #
    # We enforce this by forbidding the student from being assigned
    # to any prerequisite section that lives outside semester 1, or
    # any subsequent section that lives outside semester 2. Section
    # blocks are already fixed by the master timetable, so this is a
    # simple filter on the assignment variables.

    rules = load_rules()
    sequence_rules = list(rules.sequence_pairs)

    for student in students:

        requested = set(student_course_options[student.id]["all"])

        for prereq, subsequent in sequence_rules:

            if prereq not in requested:
                continue

            if subsequent not in requested:
                continue

            prereq_assigned = assigned_by_course.get(
                (
                    student.id,
                    prereq
                )
            )

            subsequent_assigned = assigned_by_course.get(
                (
                    student.id,
                    subsequent
                )
            )

            if prereq_assigned is None:
                continue

            if subsequent_assigned is None:
                continue

            # If both courses are assigned, prerequisites must be in semester 1.
            for sec in (
                master_timetable.course_to_sections
                .get(prereq, [])
            ):

                if not section_in_semester(sec, semester1_blocks):

                    model.Add(
                        x[
                            (
                                student.id,
                                prereq,
                                sec.id
                            )
                        ] == 0
                    ).OnlyEnforceIf(subsequent_assigned)

            # If both courses are assigned, subsequent courses must be in semester 2.
            for sec in (
                master_timetable.course_to_sections
                .get(subsequent, [])
            ):

                if not section_in_semester(sec, semester2_blocks):

                    model.Add(
                        x[
                            (
                                student.id,
                                subsequent,
                                sec.id
                            )
                        ] == 0
                    ).OnlyEnforceIf(prereq_assigned)

    enrollment = {}

    for sec in master_timetable.sections:

        cap = section_capacity[sec.id]

        e = model.NewIntVar(
            0,
            cap,
            f"enrollment_{sec.id}"
        )

        enrollment[sec.id] = e

        vars_for_section = []

        for student in students:

            if (
                sec.course_code
                not in student_course_options[student.id]["all"]
            ):
                continue

            vars_for_section.append(
                x[
                    (
                        student.id,
                        sec.course_code,
                        sec.id
                    )
                ]
            )

        model.Add(
            e == sum(vars_for_section)
        )

    # =====================================================
    # GROUP SURVIVAL
    # =====================================================

    active = {}
    active_groups = {}
    group_enrollment = {}

    for gid, grouped_sections in group_sections.items():

        group_capacity = max(
            section_capacity[sec.id]
            for sec in grouped_sections
        )

        minimum = math.ceil(max(1, group_capacity) * 0.5)

        group_enrollment_var = model.NewIntVar(
            0,
            group_capacity,
            f"enrollment_{gid}"
        )

        group_enrollment[gid] = group_enrollment_var

        model.Add(
            group_enrollment_var
            ==
            sum(
                enrollment[sec.id]
                for sec in grouped_sections
            )
        )

        a = model.NewBoolVar(
            f"active_{gid}"
        )

        active_groups[gid] = a

        model.Add(
            group_enrollment_var
            >= minimum
        ).OnlyEnforceIf(a)

        model.Add(
            group_enrollment_var
            == 0
        ).OnlyEnforceIf(a.Not())

        for sec in grouped_sections:
            active[sec.id] = a

    # =====================================================
    # BALANCE SECTIONS
    # =====================================================

    balance_penalties = []

    for course_code, sections in (
        master_timetable.course_to_sections.items()
    ):

        if len(sections) <= 1:
            continue

        total_cap = sum(
            section_capacity[s.id]
            for s in sections
        )

        target = total_cap // len(sections)

        for sec in sections:

            diff = model.NewIntVar(
                -1000,
                1000,
                f"diff_{sec.id}"
            )

            abs_diff = model.NewIntVar(
                0,
                1000,
                f"abs_{sec.id}"
            )

            model.Add(
                diff ==
                enrollment[sec.id] - target
            )

            model.AddAbsEquality(
                abs_diff,
                diff
            )

            balance_penalties.append(
                abs_diff
            )

    # =====================================================
    # OBJECTIVE
    # =====================================================

    FULL_SCHEDULE_WEIGHT = 500_000_000
    MAIN_COURSE_WEIGHT = 100_000_000
    ALTERNATE_COURSE_WEIGHT = 10_000
    ACTIVE_SECTION_WEIGHT = 100

    model.Maximize(

        FULL_SCHEDULE_WEIGHT
        *
        sum(full_schedule_vars)

        +

        MAIN_COURSE_WEIGHT
        *
        sum(assigned_course_vars)

        +

        ALTERNATE_COURSE_WEIGHT
        *
        sum(assigned_alternate_vars)

        +

        ACTIVE_SECTION_WEIGHT
        *
        sum(active_groups.values())

        -

        sum(balance_penalties)

    )

    # =====================================================
    # SOLVE
    # =====================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):
        raise RuntimeError(
            "No feasible student assignment found."
        )

    # =====================================================
    # EXTRACT SCHEDULES
    # =====================================================

    all_schedules = {}

    section_enrollment = defaultdict(int)
    group_enrollment_values = {}

    for student in students:

        schedule = {}

        for course_code in student_course_options[student.id]["all"]:

            for sec in (
                master_timetable.course_to_sections
                .get(course_code, [])
            ):

                if solver.Value(
                    x[
                        (
                            student.id,
                            course_code,
                            sec.id
                        )
                    ]
                ):

                    blocks = getattr(
                        sec,
                        "occupied_blocks",
                        [sec.time_slot]
                    )

                    schedule[
                        course_code
                    ] = (
                        sec.id,
                        blocks
                    )

                    section_enrollment[
                        sec.id
                    ] += 1

                    break

        all_schedules[
            student.id
        ] = schedule

    for gid, group_var in group_enrollment.items():
        group_enrollment_values[gid] = solver.Value(group_var)

    for sec in master_timetable.sections:
        gid = section_to_group[sec.id]
        sec.enrollment_group_id = gid
        sec.enrollment_group_size = len(group_sections[gid])
        sec.enrollment_group_count = group_enrollment_values[gid]
        sec.cancelled = solver.Value(active[sec.id]) == 0

    # =====================================================
    # REPORT
    # =====================================================

    print("\nGROUP ENROLLMENTS\n")

    for gid, grouped_sections in group_sections.items():
        group_capacity = max(
            section_capacity[sec.id]
            for sec in grouped_sections
        )
        section_ids = ", ".join(
            sec.id
            for sec in grouped_sections
        )

        print(
            f"{gid:12}"
            f"{group_enrollment_values[gid]:3}"
            f"/{group_capacity:3}"
            f" active={solver.Value(active_groups[gid])}"
            f" sections={section_ids}"
        )

    print("\nSECTION ENROLLMENTS\n")

    for sec in master_timetable.sections:

        print(
            f"{sec.id:20}"
            f"{section_enrollment[sec.id]:3}"
            f"/{section_capacity[sec.id]:3}"
            f" active={solver.Value(active[sec.id])}"
        )

    return (
        all_schedules,
        section_enrollment
    )
