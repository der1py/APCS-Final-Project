from dataclasses import dataclass
from typing import Dict, Set, Tuple


@dataclass
class Rules:
    """
    Stores all global scheduling constraints for the timetable system.
    This class does NOT contain logic, only data used by the solver.
    """

    # -------------------------
    # Pair constraints
    # -------------------------

    split_pairs: Set[Tuple[str, str]]
    """
    Courses that must be scheduled in a linked/split manner.
    Example: ("BIO11A", "BIO11B")
    """

    sequence_pairs: Set[Tuple[str, str]]
    """
    Courses that must be ordered in sequence.
    Example: ("MATH10A", "MATH10B")
    """

    # -------------------------
    # Mapping constraints
    # -------------------------

    course_room_map: Dict[str, Set[str]]
    """
    Maps each course to the set of allowed rooms.
    Example:
    {
        "CHEM11": {"LAB1", "LAB2"},
        "MATH10": {"R101", "R102"}
    }
    """

    teacher_constraints: Dict[str, Set[str]]
    """
    Maps each teacher to the set of courses they can teach.
    Example:
    {
        "T1": {"MATH10", "PHYS11"}
    }
    """

    # -------------------------
    # Initialization safety
    # -------------------------

    def __post_init__(self):
        # Ensure no None values break the solver later
        if self.split_pairs is None:
            self.split_pairs = set()

        if self.sequence_pairs is None:
            self.sequence_pairs = set()

        if self.course_room_map is None:
            self.course_room_map = {}

        if self.teacher_constraints is None:
            self.teacher_constraints = {}

    # -------------------------
    # Helper functions
    # -------------------------

    def is_room_allowed(self, course_code: str, room: str) -> bool:
        """
        Returns True if the course can be scheduled in the given room.
        """

        if course_code not in self.course_room_map:
            return False

        return room in self.course_room_map[course_code]

    def is_sequence_pair(self, a: str, b: str) -> bool:
        """
        Returns True if (a, b) is a sequence constraint.
        """

        return (a, b) in self.sequence_pairs