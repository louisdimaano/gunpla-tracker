# Gunpla Tracker Stage 1 (Kits) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **For this project specifically:** Louis builds it himself on his Windows PC, guided step by step. Every piece of code gets explained in plain, non-technical terms, including why it's there, before he types it.

**Goal:** A working Flask app where Louis can add, edit, delete, search, and sort his Gunpla kits from his phone or PC.

**Architecture:** Same shape as SpoolManager. `app.py` holds the routes, `db.py` opens the SQLite database, `schema.sql` defines the table, and `kits.py` holds the rules that don't need a web page (form checks, the finished-date rule, sorting) so they can be tested on their own. Jinja templates share one layout.

**Tech Stack:** Python 3.13, Flask, SQLite (built-in `sqlite3`, no ORM), Jinja, pytest (unit tests plus Flask's test client for page tests).

**Spec:** `docs/superpowers/specs/2026-11-14-gunpla-tracker-design.md` (Goal 1 and the "finished date" rule; build order step 1)

## Global Constraints

- Statuses, exactly: `Not Started`, `Snapped Fit`, `Built`, `Painted`
- Grades, in this order (used for sorting): `HG`, `RG`, `MG`, `PG`, `SD`, `EG`, `FM`, `Other`
- Difficulty and build quality: optional whole numbers from 1 to 5
- Finished date: set automatically when the status changes to `Built` or `Painted`, editable by hand for backfilling, cleared when the status is anything else
- SQL always uses `?` or named placeholders; user input never goes into a SQL string
- Every form is checked on the server; on an error the form is shown again with what Louis typed still filled in
- Must be comfortable on a phone screen
- Local dev port is 5001 (5000 is SpoolManager's); the Docker port is decided in stage 3
- No reminders, streaks, or anything that nags (spec anti-goal)

## Review Focus

1. **Sorting by kit number when some kits have no number.** Python can't compare a number with "nothing" and would crash. Unnumbered kits should sort last. Pinned in Task 2.
2. **Searching for text with `%`, `_`, or an apostrophe** (like "100%" or "Zeta's"). In SQL `LIKE`, `%` and `_` are wildcards, so they would match everything. They should match literally. Pinned in Task 5.
3. **A typo in the kit number** ("15a", "-3"). Should show a clear error and keep everything else he typed. Pinned in Task 3.
4. **Opening or deleting a kit that no longer exists** (old bookmark, double tap on Delete). Should show Not Found, not crash. Pinned in Task 4.
5. **An empty collection** (first run, or after deleting everything). The list page should say there are no kits yet and link to Add, not show a blank page. Pinned in Task 3.

---

### Task 1: Project setup and kit form rules

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `.dockerignore` (same contents as SpoolManager's), `kits.py`, `tests/test_kits.py`
- Copy in: `docs/superpowers/specs/2026-11-14-gunpla-tracker-design.md` and this plan

**Interfaces:**
- Produces in `kits.py`:
  - `GRADES: list[str]`, `STATUSES: list[str]`, `FINISHED_STATUSES = ("Built", "Painted")`
  - `read_kit_form(form) -> tuple[dict, list[str]]`. Keys in the dict: `name`, `grade`, `series`, `kit_number`, `status`, `difficulty`, `build_quality`, `finished_on`, `notes`. Blank optional fields become `None`. Numbers become `int`. `finished_on` is the typed date as a `"YYYY-MM-DD"` string or `None`.
  - `decide_finished_on(old_status, new_status, old_date, submitted_date, today) -> str | None`

- [ ] **Step 1: Set up the folder**

Create `gunpla-tracker`, make a virtual environment, and run `git init`. `requirements.txt` has `Flask` and `gunicorn` (pin the same versions as SpoolManager). `requirements-dev.txt` has `-r requirements.txt` and `pytest`. `pytest.ini` matches SpoolManager's.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

- [ ] **Step 2: Write the failing tests for the form rules**

```python
from datetime import date
from kits import read_kit_form, decide_finished_on

TODAY = date(2026, 11, 16)


def good_form(**changes):
    form = {"name": "Gundam Exia", "grade": "HG", "series": "HG Gundam 00",
            "kit_number": "", "status": "Not Started", "difficulty": "",
            "build_quality": "", "finished_on": "", "notes": ""}
    form.update(changes)
    return form


def test_valid_form_has_no_errors():
    values, errors = read_kit_form(good_form(kit_number="15", difficulty="3"))
    assert errors == []
    assert values["name"] == "Gundam Exia"
    assert values["kit_number"] == 15
    assert values["difficulty"] == 3
    assert values["build_quality"] is None
    assert values["notes"] is None


def test_blank_name_is_rejected():
    _, errors = read_kit_form(good_form(name="   "))
    assert errors == ["Give the kit a name."]


def test_unknown_grade_is_rejected():
    _, errors = read_kit_form(good_form(grade="XX"))
    assert errors == ["Pick a grade from the list."]


def test_unknown_status_is_rejected():
    _, errors = read_kit_form(good_form(status="Half done"))
    assert errors == ["Pick a status from the list."]


def test_bad_kit_number_is_rejected():
    for bad in ("15a", "-3", "0"):
        _, errors = read_kit_form(good_form(kit_number=bad))
        assert errors == ["Kit number must be a whole number above 0."]


def test_rating_out_of_range_is_rejected():
    _, errors = read_kit_form(good_form(build_quality="6"))
    assert errors == ["Ratings must be from 1 to 5."]


def test_bad_date_is_rejected():
    _, errors = read_kit_form(good_form(status="Built", finished_on="2026-13-40"))
    assert errors == ["Finished date must be a real date."]


def test_new_painted_kit_gets_todays_date():
    assert decide_finished_on(None, "Painted", None, None, TODAY) == "2026-11-16"


def test_backfilled_date_is_kept():
    assert decide_finished_on(None, "Built", None, "2025-03-01", TODAY) == "2025-03-01"


def test_built_to_painted_moves_date_to_today():
    assert decide_finished_on("Built", "Painted", "2026-01-10", "2026-01-10", TODAY) == "2026-11-16"


def test_date_typed_by_hand_wins():
    assert decide_finished_on("Built", "Painted", "2026-01-10", "2026-02-01", TODAY) == "2026-02-01"


def test_same_status_keeps_its_date():
    assert decide_finished_on("Painted", "Painted", "2026-01-10", "2026-01-10", TODAY) == "2026-01-10"


def test_unfinished_status_clears_date():
    assert decide_finished_on("Built", "Not Started", "2026-01-10", "2026-01-10", TODAY) is None
```

- [ ] **Step 3: Run them and watch them fail**

Run: `pytest tests/test_kits.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kits'`

- [ ] **Step 4: Write `kits.py`**

`read_kit_form` follows SpoolManager's `read_spool_form` pattern: strip text, collect error messages in a list, and return `(values, errors)`. Use the exact error messages from the tests. Dates are checked with `date.fromisoformat`.

The `decide_finished_on` rule, in order:
1. If `new_status` isn't in `FINISHED_STATUSES`, return `None`.
2. If the status changed (`new_status != old_status`) and the date wasn't touched (`submitted_date == old_date`), return `today.isoformat()`.
3. Otherwise return `submitted_date`.

- [ ] **Step 5: Run the tests and see them pass**

Run: `pytest tests/test_kits.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```powershell
git add .
git commit -m "Set up project and add kit form rules"
```

---

### Task 2: Sorting rules

**Files:**
- Modify: `kits.py`
- Test: `tests/test_kits.py`

**Interfaces:**
- Produces: `SORT_OPTIONS = ("name", "grade", "series", "number", "status")` and `sort_kits(kits, sort_by: str) -> list`. `kits` is any list of dict-like rows (`sqlite3.Row` works). An unknown `sort_by` falls back to `"name"`.

- [ ] **Step 1: Write the failing tests**

```python
from kits import sort_kits


def kit(name, grade="HG", series=None, kit_number=None, status="Not Started"):
    return {"name": name, "grade": grade, "series": series,
            "kit_number": kit_number, "status": status}


def names(kits):
    return [k["name"] for k in kits]


def test_name_sort_ignores_case():
    kits = [kit("zaku"), kit("Exia"), kit("barbatos")]
    assert names(sort_kits(kits, "name")) == ["barbatos", "Exia", "zaku"]


def test_grade_sort_follows_grade_list():
    kits = [kit("A", grade="MG"), kit("B", grade="HG"), kit("C", grade="RG")]
    assert names(sort_kits(kits, "grade")) == ["B", "C", "A"]


def test_number_sort_puts_unnumbered_last():
    kits = [kit("A", grade="RG", kit_number=15), kit("B", grade="RG"),
            kit("C", grade="RG", kit_number=3)]
    assert names(sort_kits(kits, "number")) == ["C", "A", "B"]


def test_series_sort_puts_blank_series_last():
    kits = [kit("A"), kit("B", series="Gundam 00"), kit("C", series="Build Fighters")]
    assert names(sort_kits(kits, "series")) == ["C", "B", "A"]


def test_status_sort_follows_status_list():
    kits = [kit("A", status="Painted"), kit("B", status="Not Started"), kit("C", status="Built")]
    assert names(sort_kits(kits, "status")) == ["B", "C", "A"]


def test_unknown_sort_falls_back_to_name():
    kits = [kit("Zaku"), kit("Exia")]
    assert names(sort_kits(kits, "price")) == ["Exia", "Zaku"]
```

- [ ] **Step 2: Run them and watch them fail**

Run: `pytest tests/test_kits.py -v`
Expected: the new tests FAIL with `ImportError: cannot import name 'sort_kits'`

- [ ] **Step 3: Write `sort_kits`**

Use `sorted` with a key function. Grades and statuses sort by their position in `GRADES` and `STATUSES`. "Number" sorts by grade, then kit number, then name. Missing series or numbers go last: make the key a pair like `(value is None, value)` so `None` never gets compared to a number. Every sort ends on the name (case-insensitive) as a tie-breaker.

- [ ] **Step 4: Run the tests and see them pass**

Run: `pytest tests/test_kits.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```powershell
git commit -am "Add kit sorting"
```

---

### Task 3: Database, list page, and Add Kit

**Files:**
- Create: `schema.sql`, `db.py`, `app.py`, `templates/base.html`, `templates/kits.html`, `templates/kit_form.html`, `static/style.css` (start from SpoolManager's), `tests/conftest.py`, `tests/test_routes.py`

**Interfaces:**
- Consumes: `read_kit_form`, `decide_finished_on`, `GRADES`, `STATUSES` from Tasks 1 and 2
- Produces:
  - `db.get_db()` and `db.init_db()`, same as SpoolManager's. `DB_PATH` comes from the `DATABASE_PATH` environment variable, defaulting to `kits.db` next to the code. `get_db` must read `DB_PATH` each time it's called so tests can point it at a temporary file.
  - Routes: `kit_list` at `/` and `add_kit` at `/kits/new` (GET and POST)
  - Test fixture `client` in `tests/conftest.py`

- [ ] **Step 1: Write `schema.sql`**

```sql
CREATE TABLE IF NOT EXISTS kits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    series TEXT,
    kit_number INTEGER,
    status TEXT NOT NULL DEFAULT 'Not Started',
    difficulty INTEGER,
    build_quality INTEGER,
    finished_on TEXT,
    notes TEXT
);
```

- [ ] **Step 2: Write the test setup, `tests/conftest.py`**

```python
import os
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "import.db"))

import pytest
import db
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    app.config["TESTING"] = True
    return app.test_client()
```

The environment variable line runs before `app` is imported, so the import never creates a database inside the project folder. Each test then gets its own empty database.

- [ ] **Step 3: Write the failing page tests in `tests/test_routes.py`**

```python
FORM = {"name": "Gundam Exia", "grade": "HG", "series": "HG Gundam 00", "kit_number": "",
        "status": "Not Started", "difficulty": "", "build_quality": "", "finished_on": "", "notes": ""}


def add_kit(client, **changes):
    return client.post("/kits/new", data={**FORM, **changes})


def test_empty_list_says_no_kits_yet(client):
    page = client.get("/")
    assert page.status_code == 200
    assert b"No kits yet" in page.data
    assert b'href="/kits/new"' in page.data


def test_added_kit_shows_in_list(client):
    response = add_kit(client)
    assert response.status_code == 302
    assert b"Gundam Exia" in client.get("/").data


def test_bad_kit_number_shows_error_and_keeps_input(client):
    page = add_kit(client, kit_number="15a")
    assert page.status_code == 200
    assert b"Kit number must be a whole number above 0." in page.data
    assert b'value="Gundam Exia"' in page.data
    assert b"No kits yet" in client.get("/").data
```

- [ ] **Step 4: Run them and watch them fail**

Run: `pytest tests/test_routes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 5: Write `db.py`, `app.py`, and the templates**

- `db.py`: same as SpoolManager's, minus the column migration code (nothing to migrate yet).
- `app.py`: `kit_list` gets all kits and shows `kits.html`. `add_kit` follows SpoolManager's `add_spool` pattern: show the form on GET; on POST, run `read_kit_form`, then `decide_finished_on(None, status, None, finished_on, date.today())`, then INSERT, then redirect to `kit_list`. The bottom of the file runs `app.run(debug=True, port=5001)`.
- `base.html`: SpoolManager's layout, titled "Gunpla Tracker", with nav links "Kits" and "Add kit".
- `kits.html`: one card per kit showing name, grade with kit number (like "RG 15"), series, status, ratings, and finished date, plus an Edit link. When there are no kits, show "No kits yet." and a link to `/kits/new`.
- `kit_form.html`: inputs for every field. Grade and status are dropdowns. Ratings are 1 to 5 dropdowns with a blank choice. Finished date is `type="date"`. Errors appear at the top. On an error, every field keeps what was typed.

- [ ] **Step 6: Run all tests and see them pass**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 7: Try it by hand**

Run `python app.py`, open http://127.0.0.1:5001, add two kits, then use the browser's phone view (F12, then the phone icon) to check it reads well on a narrow screen.

- [ ] **Step 8: Commit**

```powershell
git add .
git commit -m "Add database, kit list, and Add Kit page"
```

---

### Task 4: Edit and delete

**Files:**
- Modify: `app.py`, `templates/kit_form.html`, `templates/kits.html`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `add_kit` test helper and `client` fixture (Task 3), `decide_finished_on` (Task 1)
- Produces: `get_kit_or_404(conn, kit_id)`; routes `edit_kit` at `/kits/<int:kit_id>/edit` (GET and POST) and `delete_kit` at `/kits/<int:kit_id>/delete` (POST only)

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date

import db


def only_kit():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM kits").fetchone()
    conn.close()
    return row


def test_edit_built_to_painted_moves_date_to_today(client):
    add_kit(client, status="Built", finished_on="2026-01-10")
    kit_id = only_kit()["id"]
    client.post(f"/kits/{kit_id}/edit", data={**FORM, "status": "Painted", "finished_on": "2026-01-10"})
    assert only_kit()["status"] == "Painted"
    assert only_kit()["finished_on"] == date.today().isoformat()


def test_edit_form_shows_saved_values(client):
    add_kit(client, notes="Falls apart")
    page = client.get(f"/kits/{only_kit()['id']}/edit")
    assert b"Falls apart" in page.data


def test_delete_removes_kit(client):
    add_kit(client)
    client.post(f"/kits/{only_kit()['id']}/delete")
    assert only_kit() is None


def test_missing_kit_is_not_found(client):
    assert client.get("/kits/999/edit").status_code == 404
    assert client.post("/kits/999/edit", data=FORM).status_code == 404
    assert client.post("/kits/999/delete").status_code == 404
```

- [ ] **Step 2: Run them and watch them fail**

Run: `pytest tests/test_routes.py -v`
Expected: the new tests FAIL with 404 or 405 status codes, because the routes don't exist yet

- [ ] **Step 3: Write `get_kit_or_404`, `edit_kit`, and `delete_kit`**

These follow SpoolManager's `get_spool_or_404`, `edit_spool`, and `delete_spool`. One difference: `delete_kit` also uses `get_kit_or_404`. On save, `edit_kit` calls `decide_finished_on(saved["status"], values["status"], saved["finished_on"], values["finished_on"], date.today())`. The Delete button lives on the edit page inside its own small form, with a browser `confirm()` so a mis-tap doesn't wipe a kit. Each kit card in `kits.html` links to its edit page.

- [ ] **Step 4: Run all tests and see them pass**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```powershell
git commit -am "Add editing and deleting kits"
```

---

### Task 5: Search, sort, and series suggestions on the list page

**Files:**
- Modify: `app.py`, `templates/kits.html`, `templates/kit_form.html`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `sort_kits`, `SORT_OPTIONS` (Task 2)
- Produces: `kit_list` reads `?q=` (search text) and `?sort=` (one of `SORT_OPTIONS`) from the address bar

- [ ] **Step 1: Write the failing tests**

```python
def test_search_matches_part_of_name_ignoring_case(client):
    add_kit(client, name="Gundam Exia")
    add_kit(client, name="Zaku II")
    page = client.get("/?q=exia").data
    assert b"Gundam Exia" in page
    assert b"Zaku II" not in page


def test_search_treats_percent_and_underscore_literally(client):
    add_kit(client, name="100% Exia")
    add_kit(client, name="Zaku_II")
    add_kit(client, name="Barbatos")
    page = client.get("/?q=%25").data
    assert b"100% Exia" in page
    assert b"Barbatos" not in page
    page = client.get("/?q=_").data
    assert b"Zaku_II" in page
    assert b"Barbatos" not in page


def test_search_with_apostrophe_works(client):
    add_kit(client, name="Zeta's Return")
    assert b"Zeta&#39;s Return" in client.get("/?q=zeta's").data


def test_search_with_no_match_says_so(client):
    add_kit(client)
    assert b"No kits match" in client.get("/?q=nothing").data


def test_sort_by_grade_orders_list(client):
    add_kit(client, name="Master One", grade="MG")
    add_kit(client, name="High One", grade="HG")
    page = client.get("/?sort=grade").data
    assert page.index(b"High One") < page.index(b"Master One")


def test_form_suggests_existing_series(client):
    add_kit(client, series="HG Gundam 00")
    assert b'<option value="HG Gundam 00">' in client.get("/kits/new").data
```

- [ ] **Step 2: Run them and watch them fail**

Run: `pytest tests/test_routes.py -v`
Expected: the new tests FAIL (search returns every kit, no "No kits match" message, no series options)

- [ ] **Step 3: Add search, sort, and suggestions**

- Search in SQL: `WHERE name LIKE ? ESCAPE '\'`, with the search text's `\`, `%`, and `_` each escaped with a `\` first, then wrapped in `%...%`. SQLite's `LIKE` already ignores upper and lower case for English letters.
- Sort in Python with `sort_kits` after the query.
- `kits.html`: a search box and a sort dropdown in one small GET form at the top, both keeping their current values. "No kits match." shows when a search finds nothing; "No kits yet." still shows when the collection is empty.
- `kit_form.html`: the series input uses a `<datalist>` filled with every series already saved (`SELECT DISTINCT series ... WHERE series IS NOT NULL ORDER BY series`), so "HG Gundam 00" isn't typed three different ways.

- [ ] **Step 4: Run all tests and see them pass**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 5: Try it on a phone-sized screen**

Run `python app.py`. Search, sort, and add a kit with the series suggestion, all in the browser's phone view.

- [ ] **Step 6: Commit**

```powershell
git commit -am "Add search, sorting, and series suggestions"
```

---

### Task 6: README and publish to GitHub

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Use the same sections as SpoolManager's: what it is, Features (stage 1 only), Built With, Project Structure, Running It Locally (port 5001), Running the Tests (`pip install -r requirements-dev.txt`, then `pytest`), What I Learned (new things from this stage, written by Louis), and Roadmap (stages 2 to 6 from the spec, in plain words). Note that there's no login, and that it's only meant to be reached over a private network.

- [ ] **Step 2: Run the full test suite one last time**

Run: `pytest -v`
Expected: all PASS

- [ ] **Step 3: Commit and publish**

Create an empty public repo named `gunpla-tracker` on GitHub, then:

```powershell
git add README.md
git commit -m "Add README"
git branch -M main
git remote add origin https://github.com/louisdimaano/gunpla-tracker.git
git push -u origin main
```

Expected: the repo page on GitHub shows the code and the README.
