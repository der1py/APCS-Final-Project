import pickle
from dataclasses import dataclass
from pathlib import Path

from solver.student_timetable_result import StudentTimetableResult


SRC_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SRC_DIR / "output"
MASTER_TIMETABLE_PICKLE = OUTPUT_DIR / "master_timetable.pkl"
STUDENT_TIMETABLE_PICKLE = OUTPUT_DIR / "student_timetables.pkl"


@dataclass
class CachedMasterTimetable:
    sections: list
    section_to_block: dict
    course_to_sections: dict
    section_by_id: dict
    course_lookup: dict
    section_to_blocks: dict


class TimetableUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "solver.master_timetable_builder" and name == "MasterTimetable":
            return CachedMasterTimetable

        return super().find_class(module, name)


def save_student_timetable_result(
    all_schedules,
    section_enrollment,
    pickle_path=STUDENT_TIMETABLE_PICKLE,
):
    result = StudentTimetableResult(
        all_schedules=all_schedules,
        section_enrollment=dict(section_enrollment),
    )

    with Path(pickle_path).open("wb") as file:
        pickle.dump(result, file)

    return result


def load_master_timetable(pickle_path=MASTER_TIMETABLE_PICKLE):
    path = Path(pickle_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} was not found. Run src/main.py first to generate it."
        )

    with path.open("rb") as file:
        return TimetableUnpickler(file).load()


def load_student_timetable_result(pickle_path=STUDENT_TIMETABLE_PICKLE):
    path = Path(pickle_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} was not found. Run src/main.py first to generate it."
        )

    with path.open("rb") as file:
        result = pickle.load(file)

    if not hasattr(result, "all_schedules"):
        raise ValueError(
            f"{path} does not contain a student timetable result. "
            "Run src/main.py again to regenerate it."
        )

    if not hasattr(result, "section_enrollment"):
        raise ValueError(
            f"{path} is missing section enrollment data. "
            "Run src/main.py again to regenerate it."
        )

    return result
