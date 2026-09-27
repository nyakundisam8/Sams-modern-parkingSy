# Sams-modern-parkingSy

An automated, web-based parking management system designed to streamline vehicle entry, real-time slot tracking, automated fee calculation, and exit barrier control for modern parking facilities in Kenya.

## a) Algorithms for Each Module

### Module 1 — Slot Display
ALGORITHM DisplaySlots
Read every row from the slots table
FOR each slot:
show slot_number and status (available/occupied)
Count how many are 'available' and show the total
### Module 2 — Vehicle Entry
ALGORITHM AssignSlot(plate_number)
IF plate_number already has a row with status = 'parked'
RETURN "already parked"
SCAN slots in order, find the first one with status = 'available'
IF none found
RETURN "parking full"
SET that slot's status = 'occupied'
INSERT a vehicles row: plate_number, slot_id, entry_time = now
RETURN success + slot_number
### Module 3 — Fee Calculation

**Algorithm:**
ALGORITHM CalculateFee(entry_time, exit_time)
duration = exit_time - entry_time (in minutes)
LOOK UP duration in the fee table below
RETURN duration, fee
**Fee Table:**

| Duration Parked | Fee (Kshs.) |
|---|---|
| Up to 30 minutes | Free (0) |
| Up to 2 hours | 50 |
| Up to 4 hours | 100 |
| Up to 6 hours | 300 |
| Over 6 hours | 500 |

### Module 4 — Payment & Barrier Control
ALGORITHM ProcessExit(plate_number)
vehicle = FIND row WHERE plate_number = ? AND status = 'parked'
IF not found -> RETURN error
(duration, fee) = CalculateFee(vehicle.entry_time, now)
UPDATE vehicle row: exit_time = now, fee = fee, status = 'exited'
UPDATE that slot's status = 'available'
SIMULATE "barrier open" once payment step succeeds
RETURN receipt (plate, duration, fee)
## b) Data Structures Used and Reasons

| Structure | Where used | Reason |
|---|---|---|
| List / fixed-size array (`slots` table) | Slot Display, slot allocation | The number of physical bays is fixed, so an ordered list mirrors the layout and makes "first available" scanning simple. |
| Hash-map style lookup (`WHERE plate_number = ?` on `vehicles`) | Finding a parked car on exit | Cars are only ever looked up by plate, so a keyed lookup gives near-O(1) access instead of scanning every record. |
| Queue (conceptual, easy upgrade) | Slot allocation at larger scale | Free slots behave FIFO (first freed, first given out); a `collections.deque` can replace the linear scan if the car park grows. |
| Record / struct (`sqlite3.Row`) | Every vehicle and slot entry | Groups related fields (plate, slot, entry_time, fee) as one unit, mapping directly to a database row. |
| In-memory dictionary | Fast repeated slot-status reads | Constant-time status checks between database writes. |

## c) Dynamic Database Design
slots                          vehicles
slot_id (PK)                   id (PK)
slot_number (e.g. "A1")        plate_number
status ('available'/           slot_id (FK -> slots.slot_id)
'occupied')            entry_time
exit_time
fee
status ('parked'/'exited')
- One slot relates to many vehicle records over time , but only one active (`status='parked'`) vehicle at a time.
- Vehicle records are kept as a running log rather than deleted on exit, giving a full parking history/audit trail.
- Tables are populated and updated at runtime, nothing is hard-coded except the initial slot count.