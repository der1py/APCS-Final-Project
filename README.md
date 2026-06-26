# School Timetable Optimizer

A constraint-programming project that builds a school-wide master timetable and assigns students to course sections across eight blocks, using real school data.

The project uses [Google OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver) to balance course demand, room availability, section capacity, sequencing rules, simultaneous course groupings, and student request conflicts. It was built as a learning project rather than a production-ready scheduling system.

## Results

On an idealized sample dataset of approximately 953 students, the solver produced strong scheduling outcomes:

| Metric | Result |
|---|---:|
| Students receiving at least half of a full schedule | **99.27%** |
| Students with only 0-2 unfilled course slots | **86.27%** |
| Students receiving 7-8 requested courses | **67.61%** |
| Students receiving a full 8-course schedule with alternates | **61.43%** |

Additionally, NO hard constraints were violated:

- **0 student block conflicts**
- **0 room double-bookings**
- **0 invalid room assignments**
- **0 room-capacity violations**

These results demonstrate that the approach can generate useful schedules using real school data under idealized constraints. Real-world edge cases may introduce additional complexity that is not covered by the scope of this project.

## How it works

Scheduling happens in two CP-SAT stages:

1. **Master timetable generation** assigns every course section to blocks and rooms while enforcing global rules.
2. **Student assignment** places students into the generated sections while respecting block conflicts, section capacities, course sequences, and alternate choices.

The master timetable remains the single source of truth: student schedules are derived from it and cannot change global section placements.

The solver currently models:

- eight blocks split across two semesters;
- room eligibility and capacity;
- section enrollment limits;
- simultaneous and non-simultaneous course rules;
- semester-based course sequencing;
- linear courses spanning both semesters;
- balanced section distribution;
- student request conflicts and alternate courses; and
- special room-sharing rules for compatible course groups.

## Project structure

```text
src/
|-- main.py                         # Complete scheduling pipeline
|-- data/                           # Loaders, cleaned sample data, and cleaning scripts
|-- models/                         # Course, section, student, and rule models
|-- solver/
|   |-- master_timetable_builder.py # Master model setup and solve orchestration
|   |-- student_timetable_cpsat.py  # Student assignment orchestration
|   |-- solver_context.py           # Shared master-solver API
|   |-- constraints/                # Modular master timetable constraints
|   `-- student_constraints/        # Modular student assignment constraints
|-- output_scripts/                 # CSV/JSON exports and metrics
`-- output/                         # Generated timetables and reports
```

Each constraint is implemented as a self-contained class operating through a shared solver context. Constraints can be enabled or removed through their registry lists without changing other constraint files or embedding their logic in the timetable builders.

## Running the project

### Requirements

- Python 3.10+
- Google OR-Tools

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ortools
python src\main.py
```

The full solve is configured to use up to eight worker threads. The master timetable solver has a five-minute limit, followed by a two-minute student-assignment limit, so results depends on the computer and dataset.

Specs used: Intel Core 9 288V, 32GB RAM

## Inputs

The default cleaned inputs are located in `src/data/cleaned data/`:

- `student_requests_cleaned.csv` - primary and alternate student requests;
- `clean_courses_stats.json` - course, section, capacity, room, and timetable data;
- `course_sequencing_cleaned.csv` - prerequisite-to-subsequent course rules; and
- `course_blocking_cleaned.csv` - simultaneous and non-simultaneous rules.

Room capacity and room-spread settings are centralized in `src/solver/room_config.py`.

## Outputs

A successful run writes its results to `src/output/`, including:

- `master_timetable.csv` and `master_timetable_by_room.csv`;
- `student_schedules.csv` and `student_schedules_by_name.csv`;
- JSON versions of the master and student timetables;
- cached pickle files for later analysis; and
- a console metrics report covering request fulfillment, conflicts, enrollment, room use, and rule violations.

## Further documentation

- [`constraints.md`](constraints.md) describes the modeled scheduling constraints.
- [`context.md`](context.md) contains the original design notes and data-model decisions.
