from dataclasses import dataclass
from typing import Optional


@dataclass
class Section:
    """
    Represents a scheduled instance of a course in the master timetable.
    """

    id: str # purely for internal use to identify sections
    course_code: str

    # 0–7 encoding for (1A–2D)
    time_slot: int

    teacher_id: Optional[str] = None
    room_id: Optional[str] = None

    # TODO -1 is some placeholder shit, maybe clean up later
    def __post_init__(self):
        if not (-1 <= self.time_slot <= 7):
            raise ValueError("time_slot must be in range -1–7")

        if not self.id:
            raise ValueError("Section id cannot be empty")

        if not self.course_code:
            raise ValueError("course_code cannot be empty")

    def __str__(self):
        return f"{self.id} ({self.course_code}) -> slot {self.time_slot}"