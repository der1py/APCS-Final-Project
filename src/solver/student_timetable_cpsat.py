from collections import defaultdict
from ortools.sat.python import cp_model

from data.data_loader import load_rules, load_simultaneous_blocking_rules
from solver.student_constraints import (
    AssignmentVariablesConstraint,
    BalanceSectionsConstraint,
    BlockConflictConstraint,
    CourseAssignmentConstraint,
    CourseSequencingConstraint,
    FullScheduleConstraint,
    GroupSurvivalConstraint,
    SectionEnrollmentConstraint,
    StudentSolverContext,
)


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

    def unique_courses(courses):
        seen = set()
        result = []

        for course_code in courses:
            if course_code in seen:
                continue

            seen.add(course_code)
            result.append(course_code)

        return result

    blocking_rules = load_simultaneous_blocking_rules()

    notsim_pairs = {
        frozenset((c1, c2))
        for c1, c2 in blocking_rules.get("NotSimultaneous", [])
    }

    def build_enrollment_groups():
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

    rules = load_rules()
    sequence_rules = list(rules.sequence_pairs)

    ctx = StudentSolverContext(
        model=model,
        students=students,
        master_timetable=master_timetable,
        course_lookup=course_lookup,
        semester1_blocks=semester1_blocks,
        semester2_blocks=semester2_blocks,
        blocking_rules=blocking_rules,
        sequence_rules=sequence_rules,
        notsim_pairs=notsim_pairs,
        student_course_options=student_course_options,
        section_capacity=section_capacity,
        group_sections=group_sections,
        section_to_group=section_to_group,
    )

    # =====================================================
    # MODULAR CONSTRAINTS
    # =====================================================

    constraints = [
        AssignmentVariablesConstraint(),
        CourseAssignmentConstraint(),
        FullScheduleConstraint(),
        BlockConflictConstraint(),
        CourseSequencingConstraint(),
        SectionEnrollmentConstraint(),
        GroupSurvivalConstraint(),
        BalanceSectionsConstraint(),
    ]

    for constraint in constraints:
        constraint.apply(ctx)

    x = ctx.x
    active = ctx.active
    group_enrollment = ctx.group_enrollment

    # =====================================================
    # OBJECTIVE
    # =====================================================

    FULL_SCHEDULE_WEIGHT = 500_000_000
    MAIN_COURSE_WEIGHT = 100_000_000
    ALTERNATE_COURSE_WEIGHT = 10_000
    ACTIVE_SECTION_WEIGHT = 100
    UNDER_HALF_PENALTY_WEIGHT = 1_000

    model.Maximize(

        FULL_SCHEDULE_WEIGHT
        *
        sum(ctx.full_schedule_vars)

        +

        MAIN_COURSE_WEIGHT
        *
        sum(ctx.assigned_course_vars)

        +

        ALTERNATE_COURSE_WEIGHT
        *
        sum(ctx.assigned_alternate_vars)

        +

        ACTIVE_SECTION_WEIGHT
        *
        sum(ctx.active_groups.values())

        -

        UNDER_HALF_PENALTY_WEIGHT
        *
        sum(ctx.under_half_penalties)

        -

        sum(ctx.balance_penalties)

    )

    # =====================================================
    # SOLVE
    # =====================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 120
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

    # print("\nGROUP ENROLLMENTS\n")

    # for gid, grouped_sections in group_sections.items():
    #     group_capacity = max(
    #         section_capacity[sec.id]
    #         for sec in grouped_sections
    #     )
    #     section_ids = ", ".join(
    #         sec.id
    #         for sec in grouped_sections
    #     )

    #     print(
    #         f"{gid:12}"
    #         f"{group_enrollment_values[gid]:3}"
    #         f"/{group_capacity:3}"
    #         f" active={solver.Value(active_groups[gid])}"
    #         f" sections={section_ids}"
    #     )

    # print("\nSECTION ENROLLMENTS\n")

    # for sec in master_timetable.sections:

    #     print(
    #         f"{sec.id:20}"
    #         f"{section_enrollment[sec.id]:3}"
    #         f"/{section_capacity[sec.id]:3}"
    #         f" active={solver.Value(active[sec.id])}"
    #     )

    return (
        all_schedules,
        section_enrollment
    )
