# SmartPark KE — Modern Parking Management System

A web-based parking system built with **Python (Flask)** for the Data
Structures & Algorithms Task 1/2 assignment. It shows live slot
availability, records vehicles on arrival, and calculates the fee owed
on exit before "opening the barrier."

---

## 1. Modules & Algorithms (Part a)

The client's terms of reference break down into four modules:

### Module 1 — Slot Display
**Goal:** let a driver see free bays before entering.
```
ALGORITHM DisplaySlots
  1. Read every row from the slots table
  2. FOR each slot:
        show slot_number and status (available/occupied)
  3. Count how many are 'available' and show the total
```

### Module 2 — Vehicle Entry
**Goal:** record a car on arrival and give it a bay.
```
ALGORITHM AssignSlot(plate_number)
  1. IF plate_number already has a row with status = 'parked'
        RETURN "already parked" (stops duplicate entries)
  2. SCAN slots in order, find the first one with status = 'available'
  3. IF none found
        RETURN "parking full"
  4. SET that slot's status = 'occupied'
  5. INSERT a vehicles row: plate_number, slot_id, entry_time = now
  6. RETURN success + slot_number
```
This is a **linear search / first-fit allocation** — simple, and fast
enough for a car park of realistic size (tens to low hundreds of
bays). For a much larger car park you'd swap step 2 for a **queue** of
free slot IDs (pop from the front) to make allocation O(1).

### Module 3 — Vehicle Exit & Fee Calculation
**Goal:** work out how long the car was parked and what it owes.
```
ALGORITHM CalculateFee(entry_time, exit_time)
  1. duration = exit_time - entry_time (in minutes)
  2. IF duration <= 30        -> fee = 0
     ELSE IF duration <= 120  -> fee = 50
     ELSE IF duration <= 240  -> fee = 100
     ELSE IF duration <= 360  -> fee = 300
     ELSE                     -> fee = 500
  3. RETURN duration, fee
```
This is a straightforward **tiered/bracket lookup**, same idea as an
income-tax band table.

### Module 4 — Payment & Barrier Control
**Goal:** confirm payment, free the slot, and open the barrier.
```
ALGORITHM ProcessExit(plate_number)
  1. vehicle = FIND row WHERE plate_number = ? AND status = 'parked'
  2. IF not found -> RETURN error
  3. (duration, fee) = CalculateFee(vehicle.entry_time, now)
  4. UPDATE vehicle row: exit_time = now, fee = fee, status = 'exited'
  5. UPDATE that slot's status = 'available'
  6. SIMULATE "barrier open" once payment step succeeds
  7. RETURN receipt (plate, duration, fee)
```

---

## 2. Data Structures & Why (Part b)

| Structure | Where used | Why |
|---|---|---|
| **List / fixed-size array** (the `slots` table, read into a list of rows) | Slot Display, slot allocation | The number of physical bays is fixed once installed, so a simple ordered list mirrors the physical layout and makes "first available" scanning trivial. |
| **Hash-map style lookup** (`WHERE plate_number = ?` on the `vehicles` table) | Finding a parked car on exit | We only ever look a car up by its plate, never by position, so a keyed/indexed lookup gives near-O(1) access instead of scanning every record. |
| **Queue (conceptual / easy upgrade)** | Slot allocation at bigger scale | Free slots naturally behave FIFO (first freed, first given out) — swapping the linear scan for `collections.deque` is a one-line change if the car park grows. |
| **Record / struct** (each `sqlite3.Row`) | Every vehicle and slot entry | Groups related fields (plate, slot, entry_time, fee) as one unit, which maps directly to a database row and to Python dictionaries. |
| **In-memory Python dict (optional cache)** | Fast repeated reads of slot status without hitting disk each time | Constant-time status checks between database writes. |

---

## 3. Dynamic Database Design (Part c)

Two tables, linked by a foreign key — "dynamic" because rows are
created and updated continuously at runtime (nothing is hard-coded
except the initial slot count).

```
slots                          vehicles
---------------------          -------------------------------
slot_id (PK)                   id (PK)
slot_number (e.g. "A1")        plate_number
status ('available'/           slot_id (FK -> slots.slot_id)
        'occupied')            entry_time
                                exit_time
                                fee
                                status ('parked'/'exited')
```

* One slot can appear in **many** vehicle records over time (1-to-many),
  but only **one** active (`status='parked'`) vehicle at a time —
  enforced in code, not just the schema.
* Keeping `vehicles` as a running log (rather than deleting exited
  cars) means you automatically get a full parking history/audit
  trail for free — useful for reporting revenue per day, busiest
  hours, etc.

---

## 4. Running it yourself

```bash
pip install -r requirements.txt
python app.py
```
Then open **http://127.0.0.1:5000** in your browser. Try:
- `/` — the slot display
- `/entry` — type a plate number to "arrive"
- `/exit` — type the same plate number to "leave" and see the receipt

The database file `parking.db` is created automatically on first run
(and is deliberately excluded from Git via `.gitignore`, since it's
generated data, not source code).

---

## 5. Pushing this to GitHub (step by step)

1. **Create the repo on GitHub first** (github.com → New repository →
   name it e.g. `smartpark-ke` → don't add a README there, you already
   have one).
2. On your computer, open a terminal **inside this project folder**
   and run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: SmartPark KE parking system"
   git branch -M main
   git remote add origin https://github.com/<your-username>/smartpark-ke.git
   git push -u origin main
   ```
3. Refresh your GitHub page — your files should be there.

If `git` asks for a password and rejects it: GitHub no longer accepts
your account password over HTTPS. Use a **Personal Access Token**
instead (GitHub → Settings → Developer settings → Personal access
tokens → generate one, then paste it in place of your password when
prompted), or set up SSH keys if you'd rather not deal with tokens.

---

## 6. If you want to extend it further

- Add a login for parking attendants
- Add a daily revenue report page (sum of `fee` grouped by date)
- Add slot *types* (e.g. disabled/motorbike bays) as an extra column
- Swap SQLite for PostgreSQL when moving beyond a single-file prototype
