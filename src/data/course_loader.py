import csv
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from models.course import Course


COURSE_CSV = Path("src/data/cleaned data/course_sections_cleaned.csv")
ROOM_CSV = Path("src/data/cleaned data/Staff list with rooms.csv")
OUTPUT_JSON = Path("src/data/cleaned data/generated_courses.json")


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


def get_course_department(code, description):
    text = f"{code} {description}".upper()

    if "MATH" in text or "CALCULUS" in text or "PRE-CALCULUS" in text:
        return "Mathematics"

    if "SCIENCE" in text or "PHYSICS" in text or "CHEMISTRY" in text or "BIOLOGY" in text:
        return "Science"

    if "ENGLISH" in text or "WRITING" in text or "LITERATURE" in text:
        return "English"

    if "COMPUTER" in text or "ROBOTICS" in text:
        return "Computer Lab"

    if "ART" in text:
        return "Art"

    if "MUSIC" in text:
        return "Music"

    if "DRAMA" in text:
        return "Drama"

    if "DANCE" in text:
        return "Dance"

    if "PE" in text or "ACTIVE LIVING" in text:
        return "PE"

    if "WOOD" in text:
        return "Woodwork"

    if "AUTO" in text:
        return "Automotive"

    if "DRAFT" in text:
        return "Drafting"

    if "SOCIAL" in text or "HISTORY" in text or "GEOGRAPHY" in text:
        return "Social Studies"

    return "Open"


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
            department = get_course_department(code, name)

            possible_rooms = sorted(set(
                rooms_by_department.get(department, []) + open_rooms
            ))

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