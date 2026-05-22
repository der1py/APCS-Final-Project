from dataclasses import dataclass
from typing import List


@dataclass
class Student:
    """
    Represents a student and their course requests.

    This is used ONLY in the student assignment phase,
    not in the master timetable generation.
    """

    id: int

    main_courses: List[str]
    alt_courses: List[str]

    def __post_init__(self):
        # Ensure lists exist so we don't get None errors later
        if self.main_courses is None:
            self.main_courses = []

        if self.alt_courses is None:
            self.alt_courses = []