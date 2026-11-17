from datetime import date

from forms import read_number

GRADES = ["HG", "RG", "MG", "PG", "SD", "EG", "FM", "Other"]
STATUSES = ["Not Started", "Snapped Fit", "Built", "Painted"]
FINISHED_STATUSES = ("Built", "Painted")


def read_kit_form(form):
    """Check the kit form and return (values, errors)."""
    errors = []

    name = form.get("name", "").strip()
    if not name:
        errors.append("Give the kit a name.")

    grade = form.get("grade", "")
    if grade not in GRADES:
        errors.append("Pick a grade from the list.")

    status = form.get("status", "")
    if status not in STATUSES:
        errors.append("Pick a status from the list.")

    kit_number, ok = read_number(form.get("kit_number", ""), lowest=1)
    if not ok:
        errors.append("Kit number must be a whole number above 0.")

    difficulty, difficulty_ok = read_number(form.get("difficulty", ""), lowest=1, highest=5)
    build_quality, quality_ok = read_number(form.get("build_quality", ""), lowest=1, highest=5)
    if not (difficulty_ok and quality_ok):
        errors.append("Ratings must be from 1 to 5.")

    finished_on = form.get("finished_on", "").strip() or None
    if finished_on:
        try:
            finished_on = date.fromisoformat(finished_on).isoformat()
        except ValueError:
            errors.append("Finished date must be a real date.")
            finished_on = None

    values = {
        "name": name,
        "grade": grade,
        "series": form.get("series", "").strip() or None,
        "kit_number": kit_number,
        "status": status,
        "difficulty": difficulty,
        "build_quality": build_quality,
        "finished_on": finished_on,
        "notes": form.get("notes", "").strip() or None,
    }
    return values, errors


def decide_finished_on(old_status, new_status, old_date, submitted_date, today):
    """Work out a kit's finished date when it's saved."""
    if new_status not in FINISHED_STATUSES:
        return None
    if new_status != old_status and submitted_date == old_date:
        return today.isoformat()
    return submitted_date


SORT_OPTIONS = {
    "name": "Name",
    "grade": "Grade",
    "series": "Series",
    "number": "Kit number",
    "status": "Status",
}


def position(value, choices):
    """Where a value sits in a list of choices. Unknown values go last."""
    if value in choices:
        return choices.index(value)
    return len(choices)


def last_if_missing(value):
    """Sort key piece that puts missing values (None) after real ones."""
    return (value is None, value)


def sort_kits(kits, sort_by):
    """Return the kits in the order picked on the list page."""

    def sort_key(kit):
        name = kit["name"].casefold()
        if sort_by == "grade":
            return (position(kit["grade"], GRADES), name)
        if sort_by == "series":
            series = kit["series"].casefold() if kit["series"] else None
            return (last_if_missing(series), name)
        if sort_by == "number":
            return (position(kit["grade"], GRADES), last_if_missing(kit["kit_number"]), name)
        if sort_by == "status":
            return (position(kit["status"], STATUSES), name)
        return (name,)

    return sorted(kits, key=sort_key)