# Constraints

## C1 - Section Assignment
- Each section must be assigned to exactly one of 8 blocks.
- A section cannot appear in more than one block.

### C1.1 - Linear Course Constraints
- Linear courses span both semesters as a single connected section.
- A linear section is assigned exactly one Semester 1 block and one Semester 2 block.
- Both semester assignments are jointly determined and cannot be chosen independently.
- Linear sections are treated as atomic scheduling units for:
  - block assignment
  - room assignment
  - teacher assignment
  - conflict calculation
- Linear courses may be part of blocking rules, but must always remain internally consistent across both semesters.
- Linear sections cannot be partially scheduled or split across different pairing choices after assignment.

## C2 - Group Synchronization
- Sections that belong to the same group must be scheduled in the same block.
- Group membership is derived from simultaneous blocking rules.
- Every section belongs to exactly one group.

## C3 - Room Constraints
- Each group can only use rooms that are valid for all its sections.
- Each group must be assigned exactly one room per scheduled block.
- A room can only host at most one group per block.
- If no valid room is found, a fallback room is assigned.

## C4 - Simultaneous Blocking Rules
- Certain course pairs must be scheduled in the same block.
- Matched sections from blocked courses must share identical block assignments.

## C5 - Conflict Constraints (Student Overlap)
- Students should not have requested courses scheduled in the same block.
- Conflict strength is weighted by how many students request each course pair.
- Conflict is modeled using binary same-block variables.

## C6 - Balance Constraints
- Sections should be evenly distributed across all 8 blocks.
- Each block should have approximately the same number of sections.
- Deviation from target block size is penalized.

## C7 - Course Sequencing Rules
- Certain course pairs have prerequisite ordering requirements.
- Sequencing is enforced across semesters (not individual blocks).
- If a student requests both courses in a sequence:
  - The prerequisite course must be scheduled in Semester 1.
  - The advanced course must be scheduled in Semester 2.
- Sequencing constraints are demand-driven:
  - They are only enforced for courses where students have requested both.
  - The number of available sections must be sufficient to accommodate sequencing demand.
- Sequencing applies at the course/section level, not per individual student assignment.

## O1 - Objective Function
- Minimize total student scheduling conflicts.
- Minimize imbalance between block sizes.
- Final objective is a weighted sum of:
  - conflict cost
  - balance penalty (weighted heavily)

## SYSTEM CONSTRAINT INVARIANTS
- Every section has exactly one block assignment.
- Grouping enforces atomic scheduling for linked sections.
- Room assignment happens at the group level, not per section.
- All hard constraints must be satisfied before objective optimization.