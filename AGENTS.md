Modularity Requirements

The long-term goal is that each constraint is fully self-contained.

A constraint file should:

- Define its own constraint class.
- Encapsulate all logic related to that constraint.
- Be removable by deleting a single line from the constraint registry/list.
- Be addable by adding a single line to the constraint registry/list.
- Not require modifications inside other constraint files.
- Not require modifications to the master timetable builder.

Constraints may depend on the shared SolverContext API, but should not depend directly on implementation details inside master_timetable_builder.py.

The master timetable builder should act only as:
1. Data preparation
2. SolverContext construction
3. Constraint registration/execution
4. Objective assembly
5. Solve + result extraction

Constraint logic should not remain in the builder.