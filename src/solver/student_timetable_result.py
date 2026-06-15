from dataclasses import dataclass


@dataclass
class StudentTimetableResult:
    """Persisted result of the student timetable assignment phase."""

    all_schedules: dict
    section_enrollment: dict
