from collections import defaultdict
from ortools.sat.python import cp_model
import math


def build_student_timetables(
    students,
    master_timetable,
    course_lookup
):

    model = cp_model.CpModel()

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

    # =====================================================
    # ASSIGNMENT VARIABLES
    # =====================================================

    x = {}

    for student in students:

        for course_code in student.main_courses:

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

    for student in students:

        for course_code in student.main_courses:

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

            assigned_course_vars.append(
                assigned
            )

    # =====================================================
    # BLOCK CONFLICTS
    # =====================================================

    for student in students:

        for block in range(8):

            block_vars = []

            for course_code in student.main_courses:

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
    # SECTION ENROLLMENT
    # =====================================================

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
                not in student.main_courses
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
    # SECTION SURVIVAL
    # =====================================================

    active = {}

    for sec in master_timetable.sections:

        course = course_lookup[
            sec.course_code
        ]

        minimum = math.ceil(
            max(
                1,
                course.enrollment_max
            ) * 0.5
        )

        a = model.NewBoolVar(
            f"active_{sec.id}"
        )

        active[sec.id] = a

        model.Add(
            enrollment[sec.id]
            >= minimum
        ).OnlyEnforceIf(a)

        model.Add(
            enrollment[sec.id]
            <= minimum - 1
        ).OnlyEnforceIf(a.Not())

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

    model.Maximize(

        10000
        *
        sum(assigned_course_vars)

        +

        100
        *
        sum(active.values())

        -

        sum(balance_penalties)

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

    for student in students:

        schedule = {}

        for course_code in student.main_courses:

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

    # =====================================================
    # REPORT
    # =====================================================

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