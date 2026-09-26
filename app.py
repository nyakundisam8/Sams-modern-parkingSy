"""
app.py
------
SmartPark KE - Modern Parking Management System
A primer/DSA assignment: web-based, records vehicle entry/exit,
shows live slot availability, and calculates parking fees.

Run with:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import database as db

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # needed for flash messages

# Create the database tables (and seed slots) the first time we run.
db.init_db()


@app.route("/")
def home():
    """
    SLOT DISPLAY MODULE
    Shows every slot and whether it's available or occupied, so a
    driver can see space before they even enter the gate.
    """
    slots = db.get_all_slots()
    total = len(slots)
    available = sum(1 for s in slots if s["status"] == "available")
    return render_template("index.html", slots=slots, total=total, available=available)


@app.route("/entry", methods=["GET", "POST"])
def entry():
    """VEHICLE ENTRY MODULE"""
    if request.method == "POST":
        plate = request.form.get("plate_number", "")
        success, message, slot_number = db.assign_slot_to_vehicle(plate)
        flash(message, "success" if success else "error")
        return redirect(url_for("entry"))

    available_slots = db.get_available_slots()
    return render_template("entry.html", available_count=len(available_slots))


@app.route("/exit", methods=["GET", "POST"])
def exit_vehicle():
    """VEHICLE EXIT + PAYMENT + BARRIER MODULE"""
    receipt = None
    if request.method == "POST":
        plate = request.form.get("plate_number", "")
        success, message, details = db.process_exit(plate)
        flash(message, "success" if success else "error")
        if success:
            receipt = details

    return render_template("exit.html", receipt=receipt)


if __name__ == "__main__":
    app.run(debug=True)
