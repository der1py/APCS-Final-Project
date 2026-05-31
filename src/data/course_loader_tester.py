import sys
from pathlib import Path


# Find the src folder whether this script is run from project root or src/data.
THIS_FILE = Path(__file__).resolve()

if THIS_FILE.parent.name == "data":
    SRC_DIR = THIS_FILE.parents[1]
else:
    SRC_DIR = THIS_FILE.parent / "src"

sys.path.insert(0, str(SRC_DIR))

from data.course_loader import (
    load_courses_from_csv,
    load_rooms_by_department,
    export_courses_to_json,
)


OUTPUT_JSON = SRC_DIR / "data" / "cleaned data" / "course_stats.json"


def main() -> None:
    print("Loading rooms by department...")
    rooms = load_rooms_by_department()
    print(f"Loaded {len(rooms)} departments with rooms.")

    print("Loading courses from CSV...")
    courses = load_courses_from_csv()
    print(f"Loaded {len(courses)} courses.")

    print("Exporting courses to JSON...")
    export_courses_to_json(courses, OUTPUT_JSON)
    print(f"Exported {len(courses)} courses to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()