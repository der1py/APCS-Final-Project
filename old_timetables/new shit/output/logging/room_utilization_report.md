# Room Utilization Analysis

## Current Implementation

- Production room assignment is enabled through `RoomAssignmentConstraint`.
- Room capacities are centralized in `src/solver/room_config.py`.
- Band room `119` allows two groups per block only when the shared groups are
  linear concert band groups. Non-band music courses in `119`, such as guitar,
  still use the room alone.
- The `BandRoomSharingConstraint` is self-contained; removing its single
  registry line disables the special band-room sharing rule.
- A soft `RoomSpreadPenaltyConstraint` penalizes avoidable group stacking in the
  same room/block.
- Linear and multi-block groups now use one consistent room across all occupied
  blocks.
- Main output now reports room-block utilization, hard capacity violations,
  shared room-block excess, low-use rooms, and busiest rooms.

## Why Strict 1 Group/Block Is Infeasible

Static room-demand checks show that strict `1 group/block` cannot satisfy the
current data:

- Rooms `108`/`109`: Resource and Learning Strategies demand requires 101
  room-block slots, but two rooms with eight blocks provide only 16 slots.
- `Gym`: PE demand requires 24 room-block slots, but strict capacity provides
  only 8 slots.
- `119`: Music demand requires 10 room-block slots, but strict capacity provides
  only 8 slots. The data has four linear concert band room-block uses that can
  be paired because they are not daily room uses.

Linear courses make this tighter because one section can consume two room-block
slots.

## Latest Verification

Command:

```bash
python3 src/main.py
```

Key results:

- Request Completion: 79.82%
- 7-8/8 Requested Courses: 63.10%
- 8/8 Courses with Alternates: 50.73%
- Unassigned Course Requests: 1594
- Room Capacity Violations: 0
- Invalid Room Assignments: 0
- Room Block Utilization: 243/392 (62.0%)
- Room Group Occupancies: 393
- Shared excess: 150
- Student Conflicts: 0

Band room `119` verification:

- Block 3: `MMUCB10--L` shares with `XBA--09C-L`.
- Block 7: `MIMCB11--L`/`MIMCB12--L` shares with `MMUCB10--L`.
- Blocks 0, 1, 5, and 6 each contain one non-band/guitar group only.
- There are no hard room-capacity violations.

Compared with the previous no-spread baseline, room-block utilization improved
from about 45.9% to 62.0%. The special band rule prevents the broader `119`
capacity from allowing guitar and concert band to share the same physical room
block.
