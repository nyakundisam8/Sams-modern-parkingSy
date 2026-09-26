"""
database.py
-----------
This file is the ONLY place that talks to the database (SQLite).
Keeping all SQL in one file makes the rest of the app easier to read
for someone new to Python/Flask.

Data structures used here (explained more in README.md):

1. The `slots` table behaves like an ARRAY / LIST of fixed size (e.g. 10
   parking bays). Each row is one bay, with a status flag.
2. The `vehicles` table behaves like a HASH MAP keyed on plate_number:
   we put a UNIQUE index-style lookup (WHERE plate_number = ? AND
   status = 'parked') so finding a parked car is a fast, direct lookup
   instead of scanning every record.
3. Inside the app (app.py) we also keep a small in-memory Python
   dictionary cache of slot status for instant page-refresh reads
   without hitting the disk every time.
"""

import sqlite3
from datetime import datetime

DB_NAME = "parking.db"
TOTAL_SLOTS = 10  # change this to resize the car park


def get_connection():
    """Open a connection to the SQLite database file."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["plate_number"]
    return conn


def init_db():
    """
    Create the tables if they don't already exist, and seed the
    `slots` table with TOTAL_SLOTS empty bays the first time the
    app is run. This is what makes the database "dynamic": slots and
    vehicle records are created/updated at runtime, not hard-coded.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS slots (
            slot_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_number TEXT UNIQUE NOT NULL,
            status      TEXT NOT NULL DEFAULT 'available'  -- 'available' or 'occupied'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number  TEXT NOT NULL,
            slot_id       INTEGER NOT NULL,
            entry_time    TEXT NOT NULL,
            exit_time     TEXT,
            fee           REAL,
            status        TEXT NOT NULL DEFAULT 'parked',  -- 'parked' or 'exited'
            FOREIGN KEY (slot_id) REFERENCES slots (slot_id)
        )
    """)

    # Seed slots only if the table is empty (first run)
    cur.execute("SELECT COUNT(*) FROM slots")
    if cur.fetchone()[0] == 0:
        for i in range(1, TOTAL_SLOTS + 1):
            cur.execute(
                "INSERT INTO slots (slot_number, status) VALUES (?, 'available')",
                (f"A{i}",)
            )

    conn.commit()
    conn.close()


def get_all_slots():
    """Return every slot row, ordered by slot number. Used for the visual display."""
    conn = get_connection()
    slots = conn.execute("SELECT * FROM slots ORDER BY slot_id").fetchall()
    conn.close()
    return slots


def get_available_slots():
    """Return only the slots that are free right now."""
    conn = get_connection()
    slots = conn.execute(
        "SELECT * FROM slots WHERE status = 'available' ORDER BY slot_id"
    ).fetchall()
    conn.close()
    return slots


def find_parked_vehicle(plate_number):
    """
    Fast lookup: is this plate currently parked?
    This is the 'hash-map style' lookup mentioned above.
    """
    conn = get_connection()
    vehicle = conn.execute(
        "SELECT * FROM vehicles WHERE plate_number = ? AND status = 'parked'",
        (plate_number.strip().upper(),)
    ).fetchone()
    conn.close()
    return vehicle


def assign_slot_to_vehicle(plate_number):
    """
    ENTRY MODULE ALGORITHM:
    1. Reject if this plate is already parked somewhere (no double entry).
    2. Scan slots for the first one with status = 'available'
       (this is a simple linear-search allocation algorithm -
       see README for the pseudocode and why it's O(n) but fine for
       a car park of realistic size).
    3. Mark that slot 'occupied'.
    4. Create a vehicle record with entry_time = now.
    Returns (success: bool, message: str, slot_number: str|None)
    """
    plate_number = plate_number.strip().upper()
    if not plate_number:
        return False, "Please enter a valid number plate.", None

    if find_parked_vehicle(plate_number):
        return False, f"{plate_number} is already parked inside.", None

    conn = get_connection()
    slot = conn.execute(
        "SELECT * FROM slots WHERE status = 'available' ORDER BY slot_id LIMIT 1"
    ).fetchone()

    if slot is None:
        conn.close()
        return False, "Sorry, the parking is full. No available slots.", None

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE slots SET status = 'occupied' WHERE slot_id = ?", (slot["slot_id"],))
    conn.execute(
        "INSERT INTO vehicles (plate_number, slot_id, entry_time, status) VALUES (?, ?, ?, 'parked')",
        (plate_number, slot["slot_id"], now)
    )
    conn.commit()
    conn.close()
    return True, f"Welcome! {plate_number} has been assigned slot {slot['slot_number']}.", slot["slot_number"]


def calculate_fee(entry_time_str, exit_time):
    """
    FEE ALGORITHM (pure function, easy to test on its own):
    Given how long the car has been parked, apply the tiered
    pricing from the assignment brief.
    """
    entry_time = datetime.fromisoformat(entry_time_str)
    duration = exit_time - entry_time
    minutes = duration.total_seconds() / 60

    if minutes <= 30:
        fee = 0
    elif minutes <= 120:        # up to 2 hours
        fee = 50
    elif minutes <= 240:        # up to 4 hours
        fee = 100
    elif minutes <= 360:        # up to 6 hours
        fee = 300
    else:                       # over 6 hours
        fee = 500

    return duration, fee


def process_exit(plate_number):
    """
    EXIT + PAYMENT + BARRIER MODULE ALGORITHM:
    1. Look up the parked vehicle by plate number.
    2. Compute duration parked and fee owed (calculate_fee).
    3. Mark the vehicle record 'exited' and free up its slot.
       (In a real installation, step 3 only happens *after* payment
       is confirmed; here "confirm & pay" and "open barrier" are the
       same button, simulating the barrier lifting once payment clears.)
    Returns (success, message, details_dict|None)
    """
    plate_number = plate_number.strip().upper()
    vehicle = find_parked_vehicle(plate_number)

    if vehicle is None:
        return False, f"No parked vehicle found with plate {plate_number}.", None

    exit_time = datetime.now()
    duration, fee = calculate_fee(vehicle["entry_time"], exit_time)

    conn = get_connection()
    conn.execute(
        "UPDATE vehicles SET exit_time = ?, fee = ?, status = 'exited' WHERE id = ?",
        (exit_time.isoformat(timespec="seconds"), fee, vehicle["id"])
    )
    conn.execute(
        "UPDATE slots SET status = 'available' WHERE slot_id = ?",
        (vehicle["slot_id"],)
    )
    conn.commit()
    conn.close()

    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)

    details = {
        "plate_number": plate_number,
        "duration": f"{hours}h {minutes}m",
        "fee": fee,
    }
    return True, "Payment received. Barrier opening — drive safe!", details
