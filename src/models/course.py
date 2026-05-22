from dataclasses import dataclass
# note: dataclass just abstracts a lot of boilerplate stuff like init methods etc

@dataclass
class Course:
    """
    Represents a course definition in the scheduling system.

    This is PURE data (no scheduling logic).
    """
    code: str
    name: str
    num_sections: int

    def __post_init__(self):
        # Basic validation (optional but useful)
        if self.num_sections < 0:
            raise ValueError("num_sections cannot be negative")

        if not self.code:
            raise ValueError("course code cannot be empty")

        if not self.name:
            raise ValueError("course name cannot be empty")

    def __str__(self):
        return f"{self.code} - {self.name} ({self.num_sections} sections)"