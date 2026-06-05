import csv
import json
import re
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from models.course import Course

# Preprocessing-only module: CSV -> course_stats.json generation.
# Runtime should load course definitions from course_stats.json instead.
DATA_DIR = Path(__file__).resolve().parent / "cleaned data"

COURSE_CSV = DATA_DIR / "course_sections_cleaned.csv"
ROOM_CSV = DATA_DIR / "Staff list with rooms.csv"
OUTPUT_JSON = DATA_DIR / "course_stats.json"


def load_rooms_by_department(room_csv=ROOM_CSV):
    rooms_by_department = defaultdict(list)

    with room_csv.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            department = (row.get("Department") or "").strip()
            room = (row.get("Num") or "").strip()

            if department and room:
                rooms_by_department[department].append(room)

    return dict(rooms_by_department)


def get_course_grade(code, description):
    text = f"{code} {description}".upper()

    if " 12" in text or "-12" in text or "12-" in text:
        return 12
    if " 11" in text or "-11" in text or "11-" in text:
        return 11
    if " 10" in text or "-10" in text or "10-" in text:
        return 10
    if " 9" in text or "-09" in text or "09-" in text:
        return 9

    return None


def has_word(text, word):
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def is_computer_science_course(code, description):
    text = f"{code} {description}".upper()

    return (
        "COMPUTER SCIENCE" in text
        or "COMPUTER PROGRAMMING" in text
        or "PROGRAMMING" in text
        or "ACSC" in code.upper()
    )


def get_special_course_rooms(code, description):
    text = f"{code} {description}".upper()
    grade = get_course_grade(code, description)

    if "PHYSICAL AND HEALTH EDUCATION" in text:
        return ["Gym"]

    if "ENGINEERING" in text:
        return ["104"]

    if "ELECTRONICS" in text or "ROBOTIC" in text:
        return ["104"]

    if "PROGRAMMING" in text or has_word(text, "AI"):
        return ["203"]

    if is_computer_science_course(code, description):
        if grade is not None and grade >= 12:
            return ["203"]

        return ["114", "203"]

    if "WEB DEVELOPMENT" in text:
        return ["203"]

    if "3D ANIMATION" in text or "MEDIA DESIGN" in text:
        return ["114"]

    if "INFORMATION" in text and "COMMUNICA" in text:
        return ["114", "203"]

    return None


def get_course_department(code, description):
    text = f"{code} {description}".upper()

    if "ACTIVE LIVING" in text:
        return "PE"

    if "CROSS TRAINING" in text or "YOGA" in text or "OUTDOOR EDUCATION" in text:
        return "PE"

    if "DANCE" in text:
        return "Dance"

    if "DRAMA" in text or "THEATRE" in text:
        return "Drama"

    if "MUSIC" in text or "BAND" in text or "CHOIR" in text or "STRINGS" in text:
        return "Music"

    if (
        "SCIENCE" in text
        or "PHYSICS" in text
        or "CHEMISTRY" in text
        or "BIOLOGY" in text
        or "ANATOMY" in text
        or "ENVIRONMENTAL" in text
    ):
        return "Science"

    if "WOOD" in text or "CARPENTRY" in text:
        return "Woodwork"

    if "AUTO" in text or "AUTOMOTIVE" in text or "DRIVETRAIN" in text:
        return "Automotive"

    if "POWER TECH" in text:
        return "Power Tech"

    if "DRAFT" in text:
        return "Drafting"

    if "PHOTO" in text:
        return "Photography"

    if "FOOD" in text or "TEXTILE" in text or "HOME ECONOMICS" in text:
        return "Home Economics"

    if has_word(text, "ART") or "CERAMICS" in text or "ART STUDIO" in text:
        return "Art"

    if "MATH" in text or "CALCULUS" in text or "PRE-CALCULUS" in text:
        return "Mathematics"

    if "ENGLISH" in text or "WRITING" in text or "LITERATURE" in text:
        return "English"

    if "SOCIAL" in text or "HISTORY" in text or "GEOGRAPHY" in text:
        return "Social Studies"

    return "Open"


def can_use_open_rooms(department):
    no_open_departments = {
        "PE",
        "Dance",
        "Music",
        "Drama",
        "Woodwork",
        "Automotive",
        "Power Tech",
        "Drafting",
        "Robotics",
        "Art",
        "Photography",
        "Home Economics",
        "Science",
    }

    return department not in no_open_departments


def is_linear_course(code, description):
    code = code.upper().strip()
    description = description.upper().strip()

    if "LINEAR" in description:
        return True

    if code.endswith("L") or code.endswith("-L"):
        return True

    return False


def load_courses_from_csv(course_csv=COURSE_CSV, room_csv=ROOM_CSV):
    rooms_by_department = load_rooms_by_department(room_csv)
    open_rooms = rooms_by_department.get("Open", [])

    out_of_schedule_courses = load_out_of_schedule_courses()

    courses = []

    with course_csv.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            code = (row.get("Course") or "").strip()
            name = (row.get("Description") or "").strip()
            sections_raw = (row.get("Sections") or "0").strip()

            if not code or not name:
                continue

            if code.upper().endswith("--L") or code.upper().endswith("-L"):
                continue

            num_sections = int(sections_raw)

            special_rooms = get_special_course_rooms(code, name)

            if special_rooms is not None:
                possible_rooms = special_rooms
            else:
                department = get_course_department(code, name)
                department_rooms = rooms_by_department.get(department, [])

                if can_use_open_rooms(department):
                    possible_rooms = sorted(set(department_rooms + open_rooms))
                else:
                    possible_rooms = sorted(set(department_rooms))

            course = Course(
                code=code,
                name=name,
                num_sections=num_sections,
                rooms=possible_rooms,
                linear=is_linear_course(code, name),
                outside_tt=code.upper() in out_of_schedule_courses,
            )

            courses.append(course)

    return courses

OUT_OF_SCHEDULE_CSV = DATA_DIR / "outOfScheduleCourses.csv"

def load_out_of_schedule_courses(csv_path=OUT_OF_SCHEDULE_CSV):
    courses = set()

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)

        for row in reader:
            if len(row) > 1:
                courses.add(normalize_code(row[1]))

    return courses

def normalize_code(code):
    code = code.upper().strip()

    if code.endswith("--L"):
        code = code[:-3]
    elif code.endswith("-L"):
        code = code[:-2]

    return code

def export_courses_to_json(courses, output_path=OUTPUT_JSON):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(course) for course in courses]

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


if __name__ == "__main__":
    courses = load_courses_from_csv()
    export_courses_to_json(courses)

    print("Number of courses:", len(courses))
    print("Exported to:", OUTPUT_JSON)

    for course in courses[:10]:
        print(course)
        print("Rooms:", course.rooms)
        print("Linear:", course.linear)
        print()