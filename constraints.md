# Constraints

## C1 - Section Assignment
- Each section must be assigned to exactly one of 8 blocks.
- A section cannot appear in more than one block.

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