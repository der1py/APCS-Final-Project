from datetime import datetime


# =====================================================
# LOGGING
# =====================================================

LOG_FILE = "invalid_data.log"


def log_issue(msg):

    print(msg)

    with open(LOG_FILE, "a") as f:

        f.write(
            f"[{datetime.now()}] {msg}\n"
        )


# =====================================================
# VALIDATE COURSES
# =====================================================

def validate_courses(courses):

    valid_courses = {}

    invalid_courses = set()

    for c in courses:

        # malformed object
        if (
            not hasattr(c, "code")
            or
            not hasattr(c, "num_sections")
        ):

            log_issue(
                f"INVALID COURSE OBJECT: {c}"
            )

            continue

        # impossible section count
        if c.num_sections <= 0:

            log_issue(
                f"COURSE HAS ZERO SECTIONS: "
                f"{c.code}"
            )

            invalid_courses.add(c.code)

            continue

        valid_courses[c.code] = c

    return valid_courses, invalid_courses


# =====================================================
# VALIDATE STUDENTS
# =====================================================

def validate_students(

    students,

    valid_courses
):

    valid_students = []

    for s in students:

        # malformed object
        if not hasattr(s, "main_courses"):

            log_issue(
                f"INVALID STUDENT OBJECT: {s}"
            )

            continue

        cleaned_courses = []
        cleaned_alt_courses = []

        for c in s.main_courses:

            # invalid course request
            if c not in valid_courses:

                log_issue(
                    f"{s.id}: "
                    f"INVALID COURSE REQUEST "
                    f"-> {c}"
                )

                continue

            cleaned_courses.append(c)

        for c in getattr(s, "alt_courses", []):

            if c not in valid_courses:

                log_issue(
                    f"{s.id}: "
                    f"INVALID ALTERNATE COURSE REQUEST "
                    f"-> {c}"
                )

                continue

            if c in cleaned_courses:
                continue

            cleaned_alt_courses.append(c)

        # no usable requests left
        if not cleaned_courses:

            log_issue(
                f"{s.id}: "
                f"HAS NO VALID COURSES "
                f"AFTER CLEANING"
            )

            continue

        # overwrite cleaned list
        s.main_courses = cleaned_courses
        s.alt_courses = cleaned_alt_courses

        valid_students.append(s)

    return valid_students
