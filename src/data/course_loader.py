import csv
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from models.course import Course


DATA_DIR = Path(__file__).resolve().parent / "cleaned data"

COURSE_CSV = DATA_DIR / "course_sections_cleaned.csv"
ROOM_CSV = DATA_DIR / "Staff list with rooms.csv"
OUTPUT_JSON = DATA_DIR / "generated_courses.json"


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


def is_computer_science_course(code, description):
    text = f"{code} {description}".upper()

    return (
        "COMPUTER SCIENCE" in text
        or "COMPUTER PROGRAMMING" in text
        or "PROGRAMMING" in text
        or "ACSC" in code.upper()
    )


def get_course_department(code, description):
    text = f"{code} {description}".upper()

    if is_computer_science_course(code, description):
        return "Computer Science"

    if "ACTIVE LIVING" in text or "PHYSICAL EDUCATION" in text or "PE " in text:
        return "PE"

    if "DANCE" in text:
        return "Dance"

    if "DRAMA" in text or "THEATRE" in text:
        return "Drama"

    if "MUSIC" in text or "BAND" in text or "CHOIR" in text:
        return "Music"

    if "WOOD" in text or "CARPENTRY" in text:
        return "Woodwork"

    if "AUTO" in text:
        return "Automotive"

    if "POWER TECH" in text:
        return "Power Tech"

    if "DRAFT" in text:
        return "Drafting"

    if "ROBOTICS" in text:
        return "Robotics"

    if "PHOTO" in text:
        return "Photography"

    if "FOOD" in text or "TEXTILE" in text or "HOME ECONOMICS" in text:
        return "Home Economics"

    if "ART" in text or "CERAMICS" in text or "STUDIO" in text:
        return "Art"

    if (
        "SCIENCE" in text
        or "PHYSICS" in text
        or "CHEMISTRY" in text
        or "BIOLOGY" in text
        or "ANATOMY" in text
        or "ENVIRONMENTAL" in text
    ):
        return "Science"

    if "MATH" in text or "CALCULUS" in text or "PRE-CALCULUS" in text:
        return "Mathematics"

    if "COMPUTER" in text or "MEDIA" in text:
        return "Computer Lab"

    if "ENGLISH" in text or "WRITING" in text or "LITERATURE" in text:
        return "English"

    if "SOCIAL" in text or "HISTORY" in text or "GEOGRAPHY" in text:
        return "Social Studies"

    return "Open"


def get_special_course_rooms(code, description):
    grade = get_course_grade(code, description)

    if is_computer_science_course(code, description):
        if grade is not None and grade >= 12:
            return ["203"]

        return ["114", "203"]

    return None


def can_use_open_rooms(code, description, department):
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
        "Computer Science",
    }

    if department in no_open_departments:
        return False

    return True


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

    courses = []

    with course_csv.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            code = (row.get("Course") or "").strip()
            name = (row.get("Description") or "").strip()
            sections_raw = (row.get("Sections") or "0").strip()

            if not code or not name:
                continue

            num_sections = int(sections_raw)

            special_rooms = get_special_course_rooms(code, name)

            if special_rooms is not None:
                possible_rooms = special_rooms
            else:
                department = get_course_department(code, name)
                department_rooms = rooms_by_department.get(department, [])

                if can_use_open_rooms(code, name, department):
                    possible_rooms = sorted(set(department_rooms + open_rooms))
                else:
                    possible_rooms = sorted(set(department_rooms))

            course = Course(
                code=code,
                name=name,
                num_sections=num_sections,
                rooms=possible_rooms,
                linear=is_linear_course(code, name),
            )

            courses.append(course)

    return courses


def export_courses_to_json(courses, output_path=OUTPUT_JSON):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [
        asdict(course)
        for course in courses
    ]

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