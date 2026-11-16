import os
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, abort

from db import get_db, init_db
from kits import GRADES, STATUSES, SORT_OPTIONS, read_kit_form, decide_finished_on, sort_kits


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-not-secret")
init_db()

RATINGS = [1, 2, 3, 4, 5]


def show_kit_form(heading, form, errors, kit_id=None):
    """Show the Add or Edit form, with any errors at the top."""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT series FROM kits WHERE series IS NOT NULL ORDER BY series COLLATE NOCASE"
    ).fetchall()
    conn.close()
    series_options = [row["series"] for row in rows]
    return render_template("kit_form.html", heading=heading, form=form, errors=errors,
                           kit_id=kit_id, grades=GRADES, statuses=STATUSES, ratings=RATINGS,
                           series_options=series_options)

def escape_like(text):
    """Make %, _ and \\ in search text match literally in a SQL LIKE search."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def get_kit_or_404(conn, kit_id):
    """Find one kit by id, or show a Not Found page."""
    kit = conn.execute("SELECT * FROM kits WHERE id = ?", (kit_id,)).fetchone()
    if kit is None:
        conn.close()
        abort(404)
    return kit


@app.route("/")
def kit_list():
    search = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "name")

    conn = get_db()
    if search:
        kits = conn.execute(
            "SELECT * FROM kits WHERE name LIKE ? ESCAPE '\\'",
            (f"%{escape_like(search)}%",),
        ).fetchall()
    else:
        kits = conn.execute("SELECT * FROM kits").fetchall()
    conn.close()

    return render_template("kits.html", kits=sort_kits(kits, sort_by), search=search,
                           sort_by=sort_by, sort_options=SORT_OPTIONS, statuses=STATUSES)

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


@app.route("/kits/<int:kit_id>/edit", methods=["GET", "POST"])
def edit_kit(kit_id):
    conn = get_db()
    saved = get_kit_or_404(conn, kit_id)

    if request.method == "GET":
        conn.close()
        return show_kit_form("Edit Kit", dict(saved), [], kit_id)

    values, errors = read_kit_form(request.form)
    if errors:
        conn.close()
        return show_kit_form("Edit Kit", request.form, errors, kit_id)

    values["finished_on"] = decide_finished_on(
        saved["status"], values["status"], saved["finished_on"], values["finished_on"], date.today()
    )
    values["id"] = kit_id
    conn.execute(
        "UPDATE kits SET name = :name, grade = :grade, series = :series, "
        "kit_number = :kit_number, status = :status, difficulty = :difficulty, "
        "build_quality = :build_quality, finished_on = :finished_on, notes = :notes "
        "WHERE id = :id",
        values,
    )
    conn.commit()
    conn.close()
    return redirect(url_for("kit_list"))


@app.route("/kits/<int:kit_id>/delete", methods=["POST"])
def delete_kit(kit_id):
    conn = get_db()
    get_kit_or_404(conn, kit_id)
    conn.execute("DELETE FROM kits WHERE id = ?", (kit_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("kit_list"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)