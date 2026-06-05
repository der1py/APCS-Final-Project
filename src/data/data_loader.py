from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from models.course import Course
from models.rules import Rules
from models.student import Student


STUDENT_DATA_PATH = Path(__file__).resolve().parent / "cleaned data" / "student_requests_cleaned.csv"
COURSE_DATA_PATH = Path(__file__).resolve().parent / "cleaned data" / "course_sections_cleaned.csv"
COURSE_STATS_PATH = Path(__file__).resolve().parent / "cleaned data" / "course_stats.json"
SEQUENCING_DATA_PATH = Path(__file__).resolve().parent / "cleaned data" / "course_sequencing_cleaned.csv"
BLOCKING_DATA_PATH = Path(__file__).resolve().parent / "cleaned data" / "course_blocking_cleaned.csv"


def load_students(csv_path: Path | None = None) -> List[Student]:
    """Load student course requests from the cleaned CSV and return Student objects."""
    path = Path(csv_path) if csv_path is not None else STUDENT_DATA_PATH

    students: Dict[int, Dict[str, List[str]]] = {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            student_id_raw = row.get("id", "")
            course = (row.get("course") or "").strip()
            alternate_raw = (row.get("alternate") or "").strip()

            if not student_id_raw or not course:
                continue

            student_id = int(student_id_raw)
            if student_id not in students:
                students[student_id] = {"main_courses": [], "alt_courses": []}

            is_alternate = alternate_raw.lower() in {"true", "1", "yes", "y"}
            bucket = "alt_courses" if is_alternate else "main_courses"
            students[student_id][bucket].append(course)

    return [
        Student(
            id=student_id,
            main_courses=students[student_id]["main_courses"],
            alt_courses=students[student_id]["alt_courses"],
        )
        for student_id in sorted(students)
    ]

def load_courses_from_json(json_path: Path | None = None) -> List[Course]:
    """Load course definitions from the JSON cache and return Course objects."""
    path = Path(json_path) if json_path is not None else COURSE_STATS_PATH

    with path.open("r", encoding="utf-8") as file:
        course_data = json.load(file)

    return [Course(**course_entry) for course_entry in course_data]


def load_simultaneous_blocking_rules(csv_path: Path | None = None) -> Dict[str, List[Tuple[str, str]]]:
    """Load simultaneous blocking rules from the cleaned CSV."""
    path = Path(csv_path) if csv_path is not None else BLOCKING_DATA_PATH

    grouped: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            course_1 = (row.get("Course_1") or "").strip()
            course_2 = (row.get("Course_2") or "").strip()
            blocking_type = (row.get("Blocking_Type") or "").strip()

            if not course_1 or not course_2 or not blocking_type:
                continue

            grouped[blocking_type].append((course_1, course_2))

    return grouped


def load_rules(
    sequencing_csv_path: Path | None = None,
    blocking_csv_path: Path | None = None,
) -> Rules:
    """Load scheduling rules from cleaned CSVs into a Rules object."""
    sequencing_path = Path(sequencing_csv_path) if sequencing_csv_path is not None else SEQUENCING_DATA_PATH
    blocking_path = Path(blocking_csv_path) if blocking_csv_path is not None else BLOCKING_DATA_PATH

    sequence_pairs: Set[Tuple[str, str]] = set()
    split_pairs: Set[Tuple[str, str]] = set()

    with sequencing_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            prerequisite = (row.get("Prerequisite") or "").strip()
            subsequent = (row.get("Subsequent_Course") or "").strip()

            if not prerequisite or not subsequent:
                continue

            sequence_pairs.add((prerequisite, subsequent))

    with blocking_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            course_1 = (row.get("Course_1") or "").strip()
            course_2 = (row.get("Course_2") or "").strip()
            blocking_type = (row.get("Blocking_Type") or "").strip()

            if not course_1 or not course_2:
                continue

            if blocking_type == "Simultaneous":
                split_pairs.add(tuple(sorted((course_1, course_2))))

    return Rules(
        split_pairs=split_pairs,
        sequence_pairs=sequence_pairs,
        course_room_map={},
        teacher_constraints={},
    )
