import os
import secrets
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect, url_for, abort, session
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, init_db, like_pattern
from kits import GRADES, STATUSES, SORT_OPTIONS, read_kit_form, decide_finished_on, sort_kits
from paints import read_paint_form, change_quantity
from tools import CATEGORIES, read_tool_form, sort_tools
from shading import DARKER, shade_steps
from auth import read_new_password, new_recovery_code, normalize_code


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "gunpla_session"
app.config["WTF_CSRF_TIME_LIMIT"] = None
csrf = CSRFProtect(app)
init_db()

RATINGS = [1, 2, 3, 4, 5]


# ---------- Login ----------

OPEN_PAGES = {"login", "setup", "forgot", "static"}


def saved_user():
    """The one account's saved hashes, or None if no password has been set yet."""
    conn = get_db()
    row = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
    conn.close()
    return row


def save_password(password, new_account=False):
    """Save a password and a fresh recovery code. Returns the code, to show once."""
    code = new_recovery_code()
    hashes = (generate_password_hash(password), generate_password_hash(normalize_code(code)))
    conn = get_db()
    if new_account:
        conn.execute("INSERT INTO users (password_hash, recovery_hash) VALUES (?, ?)", hashes)
    else:
        conn.execute("UPDATE users SET password_hash = ?, recovery_hash = ?", hashes)
    conn.commit()
    conn.close()
    return code


def log_in():
    """Give this browser a fresh logged-in session that lasts 30 days."""
    session.clear()
    session["logged_in"] = True
    session.permanent = True


@app.before_request
def require_login():
    if session.get("logged_in") or request.endpoint in OPEN_PAGES:
        return None
    if saved_user() is None:
        return redirect(url_for("setup"))
    return redirect(url_for("login"))


@app.errorhandler(CSRFError)
def csrf_failed(error):
    return render_template("csrf_error.html"), 400


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if saved_user() is not None:
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template("setup.html", errors=[])

    password, errors = read_new_password(request.form)
    if errors:
        return render_template("setup.html", errors=errors)

    code = save_password(password, new_account=True)
    log_in()
    return render_template("recovery_code.html", code=code)


@app.route("/login", methods=["GET", "POST"])
def login():
    user = saved_user()
    if user is None:
        return redirect(url_for("setup"))
    if request.method == "GET":
        return render_template("login.html", error=None)

    if not check_password_hash(user["password_hash"], request.form.get("password", "")):
        return render_template("login.html", error="Wrong password.")
    log_in()
    return redirect(url_for("kit_list"))


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    user = saved_user()
    if user is None:
        return redirect(url_for("setup"))
    if request.method == "GET":
        return render_template("forgot.html", errors=[])

    code = normalize_code(request.form.get("code", ""))
    if not check_password_hash(user["recovery_hash"], code):
        return render_template("forgot.html", errors=["Wrong recovery code."])

    password, errors = read_new_password(request.form)
    if errors:
        return render_template("forgot.html", errors=errors)

    new_code = save_password(password)
    log_in()
    return render_template("recovery_code.html", code=new_code)


@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "GET":
        return render_template("account.html", errors=[], changed=False)

    user = saved_user()
    if not check_password_hash(user["password_hash"], request.form.get("current", "")):
        return render_template("account.html", errors=["Your current password is wrong."], changed=False)

    password, errors = read_new_password(request.form)
    if errors:
        return render_template("account.html", errors=errors, changed=False)

    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ?", (generate_password_hash(password),))
    conn.commit()
    conn.close()
    return render_template("account.html", errors=[], changed=True)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Kits ----------

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
             (like_pattern(search),),
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

# ---------- Paints ----------

def show_paint_form(heading, form, errors, paint_id=None):
    """Show the Add or Edit paint form, with any errors at the top."""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT brand FROM paints WHERE brand IS NOT NULL ORDER BY brand COLLATE NOCASE"
    ).fetchall()
    conn.close()
    brand_options = [row["brand"] for row in rows]
    return render_template("paint_form.html", heading=heading, form=form, errors=errors,
                           paint_id=paint_id, brand_options=brand_options)

def get_paint_or_404(conn, paint_id):
    """Find one paint by id, or show a Not Found page."""
    paint = conn.execute("SELECT * FROM paints WHERE id = ?", (paint_id,)).fetchone()
    if paint is None:
        conn.close()
        abort(404)
    return paint


@app.route("/paints")
def paint_list():
    search = request.args.get("q", "").strip()
    show_used_up = request.args.get("used_up") == "1"

    conditions = []
    params = []
    if search:
        conditions.append("(name LIKE ? ESCAPE '\\' OR code LIKE ? ESCAPE '\\')")
        params += [like_pattern(search), like_pattern(search)]
    if not show_used_up:
        conditions.append("quantity > 0")

    sql = "SELECT * FROM paints"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY brand IS NULL, brand COLLATE NOCASE, name COLLATE NOCASE"

    conn = get_db()
    paints = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("paints.html", paints=paints, search=search,
                           show_used_up=show_used_up)


@app.route("/paints/new", methods=["GET", "POST"])
def add_paint():
    if request.method == "GET":
        return show_paint_form("Add a Paint", {"quantity": 1}, [])

    values, errors = read_paint_form(request.form)
    if errors:
        return show_paint_form("Add a Paint", request.form, errors)

    conn = get_db()
    conn.execute(
        "INSERT INTO paints (name, brand, code, color, quantity, running_low, notes) "
        "VALUES (:name, :brand, :code, :color, :quantity, :running_low, :notes)",
        values,
    )
    conn.commit()
    conn.close()
    return redirect(url_for("paint_list"))

@app.route("/paints/<int:paint_id>/edit", methods=["GET", "POST"])
def edit_paint(paint_id):
    conn = get_db()
    saved = get_paint_or_404(conn, paint_id)

    if request.method == "GET":
        conn.close()
        return show_paint_form("Edit Paint", dict(saved), [], paint_id)

    values, errors = read_paint_form(request.form)
    if errors:
        conn.close()
        return show_paint_form("Edit Paint", request.form, errors, paint_id)

    values["id"] = paint_id
    conn.execute(
        "UPDATE paints SET name = :name, brand = :brand, code = :code, color = :color, "
        "quantity = :quantity, running_low = :running_low, notes = :notes WHERE id = :id",
        values,
    )
    conn.commit()
    conn.close()
    return redirect(url_for("paint_list"))


@app.route("/paints/<int:paint_id>/adjust", methods=["POST"])
def adjust_paint(paint_id):
    change = request.form.get("change")
    if change not in ("1", "-1"):
        abort(400)

    conn = get_db()
    saved = get_paint_or_404(conn, paint_id)
    new_quantity = change_quantity(saved["quantity"], int(change))
    conn.execute("UPDATE paints SET quantity = ? WHERE id = ?", (new_quantity, paint_id))
    conn.commit()
    conn.close()
    return redirect(url_for("paint_list", q=request.form.get("q") or None))


@app.route("/paints/<int:paint_id>/delete", methods=["POST"])
def delete_paint(paint_id):
    conn = get_db()
    get_paint_or_404(conn, paint_id)
    conn.execute("DELETE FROM paints WHERE id = ?", (paint_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("paint_list"))

@app.route("/paints/<int:paint_id>/shade")
def shade_paint(paint_id):
    conn = get_db()
    paint = get_paint_or_404(conn, paint_id)
    conn.close()
    return render_template("shade.html", paint=paint, steps=shade_steps(paint["color"]),
                           start=len(DARKER))

# ---------- Tools ----------

def show_tool_form(heading, form, errors, tool_id=None):
    """Show the Add or Edit tool form, with any errors at the top."""
    return render_template("tool_form.html", heading=heading, form=form, errors=errors,
                           tool_id=tool_id, categories=CATEGORIES)


def get_tool_or_404(conn, tool_id):
    """Find one tool by id, or show a Not Found page."""
    tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    if tool is None:
        conn.close()
        abort(404)
    return tool


@app.route("/tools")
def tool_list():
    search = request.args.get("q", "").strip()

    conn = get_db()
    if search:
        tools = conn.execute(
            "SELECT * FROM tools WHERE name LIKE ? ESCAPE '\\'", (like_pattern(search),)
        ).fetchall()
    else:
        tools = conn.execute("SELECT * FROM tools").fetchall()
    conn.close()
    return render_template("tools.html", tools=sort_tools(tools), search=search)


@app.route("/tools/new", methods=["GET", "POST"])
def add_tool():
    if request.method == "GET":
        return show_tool_form("Add a Tool", {}, [])

    values, errors = read_tool_form(request.form)
    if errors:
        return show_tool_form("Add a Tool", request.form, errors)

    conn = get_db()
    conn.execute(
        "INSERT INTO tools (name, category, runs_out, running_low, notes) "
        "VALUES (:name, :category, :runs_out, :running_low, :notes)",
        values,
    )
    conn.commit()
    conn.close()
    return redirect(url_for("tool_list"))


@app.route("/tools/<int:tool_id>/edit", methods=["GET", "POST"])
def edit_tool(tool_id):
    conn = get_db()
    saved = get_tool_or_404(conn, tool_id)

    if request.method == "GET":
        conn.close()
        return show_tool_form("Edit Tool", dict(saved), [], tool_id)

    values, errors = read_tool_form(request.form)
    if errors:
        conn.close()
        return show_tool_form("Edit Tool", request.form, errors, tool_id)

    values["id"] = tool_id
    conn.execute(
        "UPDATE tools SET name = :name, category = :category, runs_out = :runs_out, "
        "running_low = :running_low, notes = :notes WHERE id = :id",
        values,
    )
    conn.commit()
    conn.close()
    return redirect(url_for("tool_list"))


@app.route("/tools/<int:tool_id>/delete", methods=["POST"])
def delete_tool(tool_id):
    conn = get_db()
    get_tool_or_404(conn, tool_id)
    conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tool_list"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)