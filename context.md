# High School Timetable Scheduler — System Context

This document defines the canonical system design, data structures, constraints, and rules for the timetable scheduling project.

It is the single source of truth for implementation decisions.

---

# 1. System Overview

This project generates:

- A **master timetable** (global schedule of all course sections)
- **student-level schedules** derived from the master timetable

The system assigns:

- Courses → Sections (in time blocks)
- Teachers → Sections
- Rooms → Sections
- Students → Sections (via constraints satisfaction)

---

## Optimization Engine

Primary solver:
- OR-Tools CP-SAT (constraint satisfaction optimization)
- use this to write constraitns for master timetable

---

## Scale Assumptions

- ~1000 students
- ~100 teachers
- ~300 course sections
- 2 semesters
- 4 blocks per semester → total 8 time slots

---

# 2. Time Representation

Time is represented as:


0–3 → Semester 1 (A, B, C, D)
4–7 → Semester 2 (A, B, C, D)


Index mapping is fixed and MUST NOT change.

---

# 3. Core Design Principle

> The master timetable is the ONLY source of truth.

All student schedules are derived from it.

Student schedules must never independently modify global assignments.

---

# 4. Data Sources (Immutable Inputs)

All datasets are considered **fixed for a given run**.

## 4.1 Room–Course Constraints
- Room ID
- Courses allowed in room
- Room capacity (if available)

## 4.2 Course Catalog
- course_code
- course_name
- number_of_sections (fixed)

## 4.3 Student Requests
Each student contains:
- primary course requests
- alternate course requests

⚠️ Primary and alternate requests are treated equivalently for current milestone.

## 4.4 Course Sequencing Rules
Defines ordered dependencies:
- Example: A → B means:
  - A must be in Semester 1
  - B must be in Semester 2
  - If both are selected by a student

## 4.5 Simultaneous Block Rules (Split Classes)
Defines courses that must share the same time slot:
- Example: CS11 and CS12 must be scheduled in same block

---

# 5. Data Models (Canonical Schemas)

These are the ONLY valid runtime structures.

---

## 5.1 Course

Represents course definition (not scheduled instance)

```python
Course:
- course_code: str
- course_name: str
- num_sections: int


# 2. Time Representation

Time slots use fixed indices:

| Index | Semester | Block |
|------|------|------|
| 0 | 1 | A |
| 1 | 1 | B |
| 2 | 1 | C |
| 3 | 1 | D |
| 4 | 2 | A |
| 5 | 2 | B |
| 6 | 2 | C |
| 7 | 2 | D |

This mapping MUST remain constant throughout the system.

---

## 3. Core Design Principle

The master timetable is the single source of truth.

Student schedules are always derived from the finalized master timetable.

Student-level scheduling logic must never independently modify global timetable assignments.

---

## 4. Immutable Input Datasets

All datasets are considered fixed for a given scheduling run.

---

# 4.1 Room Constraints Dataset

Contains:
- room_id
- allowed_courses
- room capacity (if available)

---

## 4.2 Course Dataset

Contains:
- course_code
- course_name
- num_sections

Number of sections is fixed and must not change dynamically.

---

## 4.3 Student Requests Dataset

Each student contains:
- primary course requests
- alternate course requests

Current milestone rule:
- Primary and alternate requests are treated equivalently.

---

## 4.4 Sequence Rules Dataset

Defines ordered semester dependencies.

Example:
- Course A → Course B

Meaning:
- A must be in semester 1
- B must be in semester 2
- if the student selected both courses

---

## 4.5 Simultaneous Blocking Dataset

Defines courses that must share the same time slot.

Example:
- CS11 and CS12 split class

Meaning:
- Both sections must run in the same block.

---

## 5. Canonical Data Models

These structures are the authoritative runtime models.

---

## 5.1 Course

Represents a course definition.

Fields:
- course_code: str
- course_name: str
- num_sections: int

---

## 5.2 Section

Represents a scheduled instance of a course.

Fields:
- id: str
- course_code: str
- time_slot: int (0–7)
- teacher_id: Optional[str]
- room_id: Optional[str]

Invariants:
- 0 <= time_slot <= 7
- id must not be empty
- course_code must be valid

---

## 5.3 Student

Fields:
- student_id: int
- requested_courses: List[str]
- alternate_courses: List[str]

---

## 5.4 StudentSchedule

Derived structure representing a finalized student timetable.

Fields:
- student_id: int
- assignments: Dict[int, Section]

Meaning:
- time_slot → assigned Section

---

## 5.5 Room (WIP)

Fields:
- room_id: str
- capacity: int
- allowed_courses: List[str]
- schedule: Dict[int, Section]

This structure is still evolving and should not be treated as finalized.

---

# 6. Hard Constraints

These constraints must never be violated.

---

## 6.1 Student Conflict Constraint

A student cannot be assigned two sections in the same time slot.

---

## 6.2 Course Section Count Constraint

Each course must have exactly num_sections scheduled.

---

## 6.3 Room Compatibility Constraint

A section may only be placed in a compatible room.

---

## 6.4 Capacity Constraint

Assigned students must not exceed room capacity.

---

## 6.5 Sequence Constraint

If course A precedes course B:
- A must be in semester 1
- B must be in semester 2

when both are selected by the same student.

---

## 6.6 Split Class Constraint

Linked courses must share the same time slot.

---

# 7. Soft Constraints

These are optimization goals and may be violated if necessary.

Examples:
- maximize student course satisfaction
- balance section sizes
- reduce timetable gaps
- improve teacher load balancing

---

# 8. Scheduling Pipeline

The system pipeline is:

1. Load datasets
2. Expand courses into sections
3. Generate master timetable
4. Validate constraints
5. Generate student schedules

---

## Critical Rule

Student schedules must never be generated before the master timetable is finalized.

---

# 9. Implementation Rules

---

## 9.1 Language and Style

- Python only
- Use type hints consistently
- Keep modules domain-specific and modular

Recommended structure:

- models/
- solver/
- constraints/
- scheduling/
- data/
- validation/

---

## 9.2 Comment Style

Comments should:
- be understandable to someone with AP Computer Science A / Java-level background
- explain WHY the logic exists
- avoid unnecessary jargon

Good example:

# Prevent students from being double-booked in the same block

Bad example:

# Loop through variables

---

# 10. Source of Truth Hierarchy

If conflicts exist, priority order is:

1. This context file
2. CP-SAT constraints
3. Dataset inputs
4. Default implementation behavior

---

# 11. Current Design Decisions

- Alternate requests are treated equally to primary requests
- Room assignment may occur after initial section scheduling
- Teacher assignment may be delayed to later scheduling phases

---

# 12. Future Extensions - ignore for now

Potential future features:
- teacher preference optimization
- dynamic rescheduling
- multi-objective optimization
- LLM-assisted constraint debugging
- schedule repair systems

# 13. Repository Structure

src/
│
├── main.py
│
├── models/
│   ├── course.py
│   ├── section.py
│   ├── student.py
|   └── rules.py  
│
├── data/ # input datasets, usually a bunch of csv
│
├── output/ # any file output
│   ├── json/ # for json objects to be used in other parts of code
│   ├── master_timetable.csv # human readable csv output
│   ├── student_timetables.csv
│   └── logging/ # log any potential issues
│
├── solver/ # core problem-solving logic
│   ├── master_timetable_builder.py
│   └── student_timetable_builder.py
│
└── context.md # this file :D