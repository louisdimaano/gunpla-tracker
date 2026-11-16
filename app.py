import os
from datetime import date

from flask import Flask, render_template, request, redirect, url_for

from db import get_db, init_db
from kits import GRADES, STATUSES, read_kit_form, decide_finished_on, sort_kits

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-not-secret")
init_db()

RATINGS = [1, 2, 3, 4, 5]


def show_kit_form(heading, form, errors, kit_id=None):
    """Show the Add or Edit form, with any errors at the top."""
    return render_template("kit_form.html", heading=heading, form=form, errors=errors,
                           kit_id=kit_id, grades=GRADES, statuses=STATUSES, ratings=RATINGS)


@app.route("/")
def kit_list():
    conn = get_db()
    kits = conn.execute("SELECT * FROM kits").fetchall()
    conn.close()
    return render_template("kits.html", kits=sort_kits(kits, "name"))


@app.route("/kits/new", methods=["GET", "POST"])
def add_kit():
    if request.method == "GET":
        return show_kit_form("Add a Kit", {}, [])

    values, errors = read_kit_form(request.form)
    if errors:
        return show_kit_form("Add a Kit", request.form, errors)

    values["finished_on"] = decide_finished_on(
        None, values["status"], None, values["finished_on"], date.today()
    )
    conn = get_db()
    conn.execute(
        "INSERT INTO kits (name, grade, series, kit_number, status, difficulty, "
        "build_quality, finished_on, notes) VALUES (:name, :grade, :series, :kit_number, "
        ":status, :difficulty, :build_quality, :finished_on, :notes)",
        values,
    )
    conn.commit()
    conn.close()
    return redirect(url_for("kit_list"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)