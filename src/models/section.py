from dataclasses import dataclass
from typing import Optional


@dataclass
class Section:
    """
    Represents a scheduled instance of a course in the master timetable.
    """

    id: str
    course_code: str

    # 0–7 encoding for (1A–2D)
    time_slot: int

    teacher_id: Optional[str] = None
    room_id: Optional[str] = None

    def __post_init__(self):
        if not (0 <= self.time_slot <= 7):
            raise ValueError("time_slot must be in range 0–7")

        if not self.id:
            raise ValueError("Section id cannot be empty")

        if not self.course_code:
            raise ValueError("course_code cannot be empty")

    def __str__(self):
        return f"{self.id} ({self.course_code}) -> slot {self.time_slot}"