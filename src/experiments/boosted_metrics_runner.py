"""
Run boosted timetable metrics from saved pickle artifacts.

This runner does not rebuild the master timetable and does not run the student
assignment CP-SAT. It expects src/main.py to have generated both pickle files.
"""

from data.data_loader import BLOCKING_DATA_PATH
from output_scripts.boosted_metrics import run_boosted_metrics
from timetable_cache import (
    MASTER_TIMETABLE_PICKLE,
    OUTPUT_DIR,
    STUDENT_TIMETABLE_PICKLE,
)


def main():
    summary = run_boosted_metrics(
        master_pickle_path=MASTER_TIMETABLE_PICKLE,
        student_pickle_path=STUDENT_TIMETABLE_PICKLE,
        blocking_rules_path=BLOCKING_DATA_PATH,
        output_dir=OUTPUT_DIR,
    )

    print("Boosted metrics written:")
    for path in summary["output_files"].values():
        print(path)


if __name__ == "__main__":
    main()
