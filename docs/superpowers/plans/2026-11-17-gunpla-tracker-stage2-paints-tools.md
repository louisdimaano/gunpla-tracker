# Gunpla Tracker Stage 2 (Paints and Tools) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **For this project specifically:** Louis builds it himself on his Windows PC, guided step by step. Every piece of code gets explained in plain, non-technical terms, including why it's there, before he types it.

**Goal:** Add a paints inventory (searchable by name or paint code, with a color swatch and a count) and a tools inventory (searchable by name, with a "running low" flag for things that run out), next to the existing kits.

**Architecture:** Same pattern as stage 1. Each inventory gets a rules file (`paints.py`, `tools.py`) that checks its form and can be tested without a web page, plus routes in `app.py` and two templates (list and form). Form helpers that kits, paints, and tools all need move into `forms.py`, and the search helper moves into `db.py`. New tables are added to `schema.sql`; `CREATE TABLE IF NOT EXISTS` adds them to Louis's existing database the next time the app starts, with his kits untouched.

**Tech Stack:** Python 3.13, Flask, SQLite (`sqlite3`, no ORM), Jinja, pytest.

**Spec:** `docs/superpowers/specs/2026-11-14-gunpla-tracker-design.md` (Goals 2 and 3; build order step 2). Barcode scanning (Goal 4) is a later stage and is not part of this plan.

## Global Constraints

- Paint fields: name (required), brand, paint code, color, quantity, running low, notes
- A paint at quantity 0 is **kept, not deleted**, and hidden from the normal list and search (spec Goal 2). A "Show used-up paints" link shows them.
- Paint search matches the **name or the paint code** (so "C-5" finds Gundam Blue)
- Quantity never goes below 0
- Tool fields: name (required), category, runs out, running low, notes. "Running low" is only saved for tools that run out.
- Tool categories, in this order: `Nippers`, `Knives`, `Sanding`, `Scribing`, `Panel lining`, `Top coat`, `Glue and cement`, `Other`
- Same rules as stage 1: `?` placeholders for every value in SQL, server-side form checks, the form keeps what was typed on an error, phone-first, no nagging
- The menu becomes Kits, Paints, Tools. Each list page gets its own Add button.
- All 32 stage 1 tests keep passing

## Review Focus

1. **Tapping −1 on a paint at 0** (double tap, or a slow phone). Should stay at 0, never −1. Pinned in Tasks 2 and 4.
2. **A used-up paint showing up in a search.** In a store, "Gundam Blue: 0 on hand" next to real paints is confusing. Search hides used-up paints unless asked. Pinned in Task 3.
3. **An invalid color value** (an old browser without a color picker sends plain text, or someone edits the form). It's put into a `style` attribute on the card, so it has to be a real `#rrggbb` color or it's rejected. Pinned in Tasks 2 and 3.
4. **"Running low" ticked on a tool that doesn't run out** (nippers). Should save as not running low, so no confusing badge. Pinned in Tasks 5.
5. **A tampered ±1 button** (`change=50`). Only +1 and −1 are accepted; anything else is refused and nothing changes. Pinned in Task 4.

---

### Task 1: Shared form and search helpers

**Files:**
- Create: `forms.py`, `tests/test_forms.py`
- Modify: `kits.py` (remove `read_number`, import it from `forms`), `db.py` (add `like_pattern`), `app.py` (remove `escape_like`, use `like_pattern`)

**Interfaces:**
- Produces in `forms.py`: `read_number(text, lowest, highest=None) -> (int | None, bool)` (moved unchanged from `kits.py`), `read_text(form, field) -> str | None`, `read_checkbox(form, field) -> int` (1 or 0)
- Produces in `db.py`: `like_pattern(text) -> str`, the search text with `\`, `%`, `_` escaped and wrapped in `%...%`. Used with `LIKE ? ESCAPE '\'`.

- [ ] **Step 1: Write the failing tests** (`tests/test_forms.py`)

```python
from db import like_pattern
from forms import read_number, read_text, read_checkbox


def test_read_number_turns_text_into_a_number():
    assert read_number(" 15 ", lowest=1) == (15, True)


def test_read_number_allows_an_empty_box():
    assert read_number("", lowest=0) == (None, True)


def test_read_number_rejects_bad_text_and_out_of_range():
    assert read_number("two", lowest=0) == (None, False)
    assert read_number("-1", lowest=0) == (None, False)
    assert read_number("6", lowest=1, highest=5) == (None, False)


def test_read_text_trims_and_turns_blank_into_none():
    assert read_text({"brand": "  Mr. Color "}, "brand") == "Mr. Color"
    assert read_text({"brand": "   "}, "brand") is None
    assert read_text({}, "brand") is None


def test_read_checkbox():
    assert read_checkbox({"running_low": "on"}, "running_low") == 1
    assert read_checkbox({}, "running_low") == 0


def test_like_pattern_escapes_wildcards():
    assert like_pattern("exia") == "%exia%"
    assert like_pattern("100%") == "%100\\%%"
    assert like_pattern("Zaku_II") == "%Zaku\\_II%"
```

- [ ] **Step 2: Run and watch it fail.** `pytest -v`. Expected: `ModuleNotFoundError: No module named 'forms'`
- [ ] **Step 3: Create `forms.py`, move `read_number` into it, add `read_text` and `read_checkbox`. Add `like_pattern` to `db.py`, and switch `kit_list` to it.** A ticked checkbox sends its name and an unticked one sends nothing, so `read_checkbox` checks whether the name is present.
- [ ] **Step 4: Run all tests.** Expected: 38 passed (the 32 old ones prove the move broke nothing)
- [ ] **Step 5: Commit.** `git add .` then `git commit -m "Move shared form and search helpers into their own files"`

---

### Task 2: Paint rules

**Files:**
- Create: `paints.py`, `tests/test_paints.py`

**Interfaces:**
- Consumes: `read_number`, `read_text`, `read_checkbox` (Task 1)
- Produces: `DEFAULT_COLOR = "#808080"`; `read_paint_form(form) -> (dict, list[str])` with keys `name`, `brand`, `code`, `color` (lowercase `#rrggbb`), `quantity` (int, blank means 1), `running_low` (1 or 0), `notes`; `change_quantity(quantity, change) -> int` (never below 0)

- [ ] **Step 1: Write the failing tests** (`tests/test_paints.py`)

```python
from paints import read_paint_form, change_quantity


def good_paint(**changes):
    form = {"name": "Gundam Blue", "brand": "Mr. Color", "code": "C-5",
            "color": "#1D4E9E", "quantity": "2", "notes": ""}
    form.update(changes)
    return form


def test_valid_paint_form_has_no_errors():
    values, errors = read_paint_form(good_paint())
    assert errors == []
    assert values["name"] == "Gundam Blue"
    assert values["code"] == "C-5"
    assert values["color"] == "#1d4e9e"
    assert values["quantity"] == 2
    assert values["running_low"] == 0
    assert values["notes"] is None


def test_blank_paint_name_is_rejected():
    _, errors = read_paint_form(good_paint(name=" "))
    assert errors == ["Give the paint a name."]


def test_blank_quantity_means_one():
    values, errors = read_paint_form(good_paint(quantity=""))
    assert errors == []
    assert values["quantity"] == 1


def test_zero_quantity_is_allowed():
    values, errors = read_paint_form(good_paint(quantity="0"))
    assert errors == []
    assert values["quantity"] == 0


def test_bad_quantity_is_rejected():
    for bad in ("-1", "two", "1.5"):
        _, errors = read_paint_form(good_paint(quantity=bad))
        assert errors == ["Quantity must be a whole number, 0 or more."]


def test_bad_color_is_rejected():
    for bad in ("blue", "#12345", "#12345g", ""):
        _, errors = read_paint_form(good_paint(color=bad))
        assert errors == ["Pick a color with the color picker."]


def test_running_low_checkbox():
    values, _ = read_paint_form(good_paint(running_low="on"))
    assert values["running_low"] == 1


def test_quantity_never_goes_below_zero():
    assert change_quantity(2, 1) == 3
    assert change_quantity(1, -1) == 0
    assert change_quantity(0, -1) == 0
```

- [ ] **Step 2: Run and watch it fail.** Expected: `ModuleNotFoundError: No module named 'paints'`
- [ ] **Step 3: Write `paints.py`.** Same pattern as `read_kit_form`. Color is checked with the regular expression `#[0-9a-fA-F]{6}` using `re.fullmatch`, then lowercased.
- [ ] **Step 4: Run all tests.** Expected: 46 passed
- [ ] **Step 5: Commit.** `git add .` then `git commit -m "Add paint form rules"`

---

### Task 3: Paints list, Add Paint, and search

**Files:**
- Modify: `schema.sql` (add the `paints` and `tools` tables), `app.py`, `templates/base.html` (menu), `templates/kits.html` (Add button, class renames), `static/style.css`
- Create: `templates/paints.html`, `templates/paint_form.html`, `tests/test_paint_pages.py`

**Interfaces:**
- Consumes: `read_paint_form` (Task 2), `like_pattern` (Task 1)
- Produces: routes `paint_list` at `/paints` (reads `?q=` and `?used_up=1`) and `add_paint` at `/paints/new`; `show_paint_form(heading, form, errors, paint_id=None)` with brand suggestions; test helpers `PAINT`, `add_paint(client, **changes)`, `only_paint()`

Tables (both added now, so stage 2 only touches `schema.sql` once):

```sql
CREATE TABLE IF NOT EXISTS paints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT,
    code TEXT,
    color TEXT NOT NULL DEFAULT '#808080',
    quantity INTEGER NOT NULL DEFAULT 1,
    running_low INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    runs_out INTEGER NOT NULL DEFAULT 0,
    running_low INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);
```

- [ ] **Step 1: Write the failing tests** (`tests/test_paint_pages.py`, first part)

```python
import db

PAINT = {"name": "Gundam Blue", "brand": "Mr. Color", "code": "C-5", "color": "#1d4e9e",
         "quantity": "1", "notes": ""}


def add_paint(client, **changes):
    return client.post("/paints/new", data={**PAINT, **changes})


def only_paint():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM paints").fetchone()
    conn.close()
    return row


def test_empty_paint_list_says_no_paints_yet(client):
    page = client.get("/paints")
    assert page.status_code == 200
    assert b"No paints yet" in page.data
    assert b'href="/paints/new"' in page.data


def test_added_paint_shows_in_list(client):
    assert add_paint(client).status_code == 302
    assert b"Gundam Blue" in client.get("/paints").data


def test_bad_color_shows_error_and_keeps_input(client):
    page = add_paint(client, color="blue")
    assert b"Pick a color with the color picker." in page.data
    assert b'value="Gundam Blue"' in page.data


def test_search_matches_name_or_code(client):
    add_paint(client)
    add_paint(client, name="Titanium Gold", code="XF-1")
    page = client.get("/paints?q=c-5").data
    assert b"Gundam Blue" in page
    assert b"Titanium Gold" not in page
    page = client.get("/paints?q=gold").data
    assert b"Titanium Gold" in page
    assert b"Gundam Blue" not in page


def test_search_with_no_match_says_so(client):
    add_paint(client)
    assert b"No paints match" in client.get("/paints?q=purple").data


def test_used_up_paint_is_hidden_until_asked_for(client):
    add_paint(client, name="Empty Red", quantity="0")
    add_paint(client)
    assert b"Empty Red" not in client.get("/paints").data
    assert b"Empty Red" not in client.get("/paints?q=red").data
    assert b"Empty Red" in client.get("/paints?used_up=1").data


def test_paint_form_suggests_existing_brands(client):
    add_paint(client)
    assert b'<option value="Mr. Color">' in client.get("/paints/new").data


def test_menu_links_to_paints(client):
    assert b'href="/paints"' in client.get("/").data
```

- [ ] **Step 2: Run and watch it fail.** Expected: 8 new failures (404s, because `/paints` doesn't exist)
- [ ] **Step 3: Add the tables, routes, and pages**
  - `paint_list` builds its `WHERE` from a list of conditions: a name-or-code `LIKE` when searching, and `quantity > 0` unless `used_up=1`. Order: brand (blank brands last), then name, both ignoring case.
  - `add_paint` follows `add_kit`. The empty form starts with quantity 1.
  - `paints.html`: page heading with an "Add paint" button, a search box, a card per paint (code as the red tag, a round color swatch, name, brand, "N on hand" or "Used up", a yellow "Running low" badge, notes, and buttons for −1, +1, and Edit), empty and no-match messages, and a "Show used-up paints" / "Hide used-up paints" link.
  - `paint_form.html`: name, brand (with `<datalist>` suggestions), code, `type="color"` picker, quantity, a "Running low" checkbox, and notes.
  - `base.html` menu: Kits, Paints, Tools (highlighted by `request.path`). `kits.html` gets its own "Add kit" button. The `kit-card`/`kit-grid` CSS classes become `plate`/`plate-grid`, since paints and tools use the same card shape. The Tools link is added in Task 5, once `tool_list` exists.
- [ ] **Step 4: Run all tests.** Expected: 54 passed
- [ ] **Step 5: Try it** at phone size: add three paints, search by a code, and add one with quantity 0 to check it's hidden.
- [ ] **Step 6: Commit.** `git add .` then `git commit -m "Add paints list, Add Paint, and paint search"`

---

### Task 4: Edit, delete, and ±1 for paints

**Files:**
- Modify: `app.py`, `templates/paints.html`, `templates/paint_form.html`
- Test: `tests/test_paint_pages.py` (add to the bottom)

**Interfaces:**
- Consumes: `change_quantity` (Task 2), `PAINT`, `add_paint`, `only_paint` (Task 3)
- Produces: `get_paint_or_404(conn, paint_id)`; routes `edit_paint` (`/paints/<int:paint_id>/edit`, GET and POST), `adjust_paint` (`/paints/<int:paint_id>/adjust`, POST, `change` must be `"1"` or `"-1"`, otherwise 400, then redirects to the list keeping `q`), `delete_paint` (`/paints/<int:paint_id>/delete`, POST)

- [ ] **Step 1: Write the failing tests**

```python
def test_minus_one_never_goes_below_zero(client):
    add_paint(client, quantity="1")
    paint_id = only_paint()["id"]
    client.post(f"/paints/{paint_id}/adjust", data={"change": "-1"})
    client.post(f"/paints/{paint_id}/adjust", data={"change": "-1"})
    assert only_paint()["quantity"] == 0


def test_plus_one_adds_one(client):
    add_paint(client, quantity="1")
    client.post(f"/paints/{only_paint()['id']}/adjust", data={"change": "1"})
    assert only_paint()["quantity"] == 2


def test_adjust_only_accepts_plus_or_minus_one(client):
    add_paint(client, quantity="1")
    response = client.post(f"/paints/{only_paint()['id']}/adjust", data={"change": "50"})
    assert response.status_code == 400
    assert only_paint()["quantity"] == 1


def test_adjust_keeps_the_search(client):
    add_paint(client)
    response = client.post(f"/paints/{only_paint()['id']}/adjust", data={"change": "1", "q": "blue"})
    assert response.headers["Location"].endswith("/paints?q=blue")


def test_edit_paint_saves_changes(client):
    add_paint(client)
    client.post(f"/paints/{only_paint()['id']}/edit",
                data={**PAINT, "quantity": "3", "running_low": "on"})
    assert only_paint()["quantity"] == 3
    assert only_paint()["running_low"] == 1


def test_edit_form_shows_saved_color(client):
    add_paint(client)
    assert b'value="#1d4e9e"' in client.get(f"/paints/{only_paint()['id']}/edit").data


def test_delete_removes_paint(client):
    add_paint(client)
    client.post(f"/paints/{only_paint()['id']}/delete")
    assert only_paint() is None


def test_missing_paint_is_not_found(client):
    assert client.get("/paints/999/edit").status_code == 404
    assert client.post("/paints/999/edit", data=PAINT).status_code == 404
    assert client.post("/paints/999/adjust", data={"change": "1"}).status_code == 404
    assert client.post("/paints/999/delete").status_code == 404
```

- [ ] **Step 2: Run and watch it fail.** Expected: 7 failed, 1 passed (the not-found test passes early for the same reason as in stage 1)
- [ ] **Step 3: Write `get_paint_or_404`, `edit_paint`, `adjust_paint`, `delete_paint`; add the −1/+1/Edit buttons to the cards and the Delete button to the edit form.** The −1 and +1 buttons are two buttons in one small POST form, sharing `name="change"` with values `-1` and `1`; a hidden `q` field carries the current search back.
- [ ] **Step 4: Run all tests.** Expected: 62 passed
- [ ] **Step 5: Commit.** `git commit -am "Add editing, deleting, and +1/-1 for paints"`

---

### Task 5: Tools

**Files:**
- Create: `tools.py`, `templates/tools.html`, `templates/tool_form.html`, `tests/test_tools.py`, `tests/test_tool_pages.py`
- Modify: `app.py`, `templates/base.html` (Tools link), `static/style.css` (checkbox rows)

**Interfaces:**
- Consumes: `read_text`, `read_checkbox`, `like_pattern` (Task 1)
- Produces: `CATEGORIES`, `read_tool_form(form) -> (dict, list[str])` with keys `name`, `category`, `runs_out`, `running_low` (forced to 0 unless `runs_out`), `notes`; `sort_tools(tools) -> list` (category order, then name ignoring case); routes `tool_list` (`/tools`, `?q=`), `add_tool`, `edit_tool`, `delete_tool`, with `get_tool_or_404`

- [ ] **Step 1: Write the failing rule tests** (`tests/test_tools.py`)

```python
from tools import read_tool_form, sort_tools


def good_tool(**changes):
    form = {"name": "GodHand SPN-120", "category": "Nippers", "notes": ""}
    form.update(changes)
    return form


def test_valid_tool_form_has_no_errors():
    values, errors = read_tool_form(good_tool())
    assert errors == []
    assert values["name"] == "GodHand SPN-120"
    assert values["runs_out"] == 0
    assert values["notes"] is None


def test_blank_tool_name_is_rejected():
    _, errors = read_tool_form(good_tool(name=""))
    assert errors == ["Give the tool a name."]


def test_unknown_category_is_rejected():
    _, errors = read_tool_form(good_tool(category="Lightsaber"))
    assert errors == ["Pick a category from the list."]


def test_running_low_needs_runs_out():
    values, _ = read_tool_form(good_tool(running_low="on"))
    assert values["running_low"] == 0
    values, _ = read_tool_form(good_tool(runs_out="on", running_low="on"))
    assert values["running_low"] == 1


def test_tools_sort_by_category_then_name():
    tools = [{"name": "Tamiya Cement", "category": "Glue and cement"},
             {"name": "sanding stick", "category": "Sanding"},
             {"name": "GodHand", "category": "Nippers"},
             {"name": "Art knife", "category": "Knives"},
             {"name": "Alpha nippers", "category": "Nippers"}]
    assert [t["name"] for t in sort_tools(tools)] == [
        "Alpha nippers", "GodHand", "Art knife", "sanding stick", "Tamiya Cement"]
```

- [ ] **Step 2: Write the failing page tests** (`tests/test_tool_pages.py`)

```python
import db

TOOL = {"name": "GodHand SPN-120", "category": "Nippers", "notes": ""}


def add_tool(client, **changes):
    return client.post("/tools/new", data={**TOOL, **changes})


def only_tool():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM tools").fetchone()
    conn.close()
    return row


def test_empty_tool_list_says_no_tools_yet(client):
    page = client.get("/tools")
    assert page.status_code == 200
    assert b"No tools yet" in page.data
    assert b'href="/tools/new"' in page.data


def test_added_tool_shows_in_list(client):
    assert add_tool(client).status_code == 302
    assert b"GodHand SPN-120" in client.get("/tools").data


def test_blank_name_shows_error(client):
    page = add_tool(client, name="")
    assert b"Give the tool a name." in page.data


def test_search_matches_part_of_name(client):
    add_tool(client)
    add_tool(client, name="Tamiya Extra Thin Cement", category="Glue and cement")
    page = client.get("/tools?q=godhand").data
    assert b"GodHand SPN-120" in page
    assert b"Tamiya Extra Thin Cement" not in page


def test_tools_list_by_category(client):
    add_tool(client, name="Tamiya Extra Thin Cement", category="Glue and cement")
    add_tool(client)
    page = client.get("/tools").data
    assert page.index(b"GodHand SPN-120") < page.index(b"Tamiya Extra Thin Cement")


def test_running_low_only_shows_for_things_that_run_out(client):
    add_tool(client, running_low="on")
    assert b"Running low" not in client.get("/tools").data
    add_tool(client, name="400 grit sandpaper", category="Sanding", runs_out="on", running_low="on")
    assert b"Running low" in client.get("/tools").data


def test_edit_tool_saves_changes(client):
    add_tool(client)
    client.post(f"/tools/{only_tool()['id']}/edit", data={**TOOL, "notes": "Use on thin gates only"})
    assert only_tool()["notes"] == "Use on thin gates only"


def test_delete_removes_tool(client):
    add_tool(client)
    client.post(f"/tools/{only_tool()['id']}/delete")
    assert only_tool() is None


def test_missing_tool_is_not_found(client):
    assert client.get("/tools/999/edit").status_code == 404
    assert client.post("/tools/999/edit", data=TOOL).status_code == 404
    assert client.post("/tools/999/delete").status_code == 404


def test_menu_links_to_tools(client):
    assert b'href="/tools"' in client.get("/").data
```

- [ ] **Step 3: Run and watch them fail.** Expected: `ModuleNotFoundError: No module named 'tools'`
- [ ] **Step 4: Write `tools.py`, the four tool routes, both templates, and the Tools menu link.** Same patterns as paints, without quantity or ±1. The card's red tag shows the category.
- [ ] **Step 5: Run all tests.** Expected: 77 passed
- [ ] **Step 6: Commit.** `git add .` then `git commit -m "Add tools inventory"`

---

### Task 6: README and publish

- [ ] **Step 1:** Update the README: Features (paints and tools), Project Structure (`forms.py`, `paints.py`, `tools.py`), What I Learned (Louis's words), and Roadmap (remove paints and tools).
- [ ] **Step 2:** `pytest`, expected 77 passed
- [ ] **Step 3:** `git status` (check that no `.db` file or `.venv` is listed), then commit and `git push`.
