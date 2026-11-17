# Gunpla Tracker Stage 4 (Shading Mixer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **For this project specifically:** Louis builds it himself on his Windows PC, guided step by step, with every piece of code explained in plain terms before he types it.

**Goal:** A Shade page for every paint: a slider from darker to lighter that shows a preview of the mix and a ratio in whole parts, like "2 parts base : 1 part white".

**Architecture:** A new rules file, `shading.py`, works out every slider stop ahead of time: a fixed list of darker mixes (with black), the paint itself, and a fixed list of lighter mixes (with white). Each stop has a color and a label. Colors are mixed with Mixbox, a library that imitates real pigment. The page gets the stops from Flask, and a few lines of JavaScript swap the preview and the label as the slider moves. All the math stays in Python, where pytest can check it.

**Tech Stack:** Python 3.13, Flask, Jinja, pytest, `pymixbox==2.0.0`, a small amount of JavaScript.

**Spec:** `docs/superpowers/specs/2026-11-14-gunpla-tracker-design.md` (Goal 7; build order step 5)

## Global Constraints

- Lighter mixes with white, darker mixes with black (Louis's choice, Nov 17, 2026)
- Previews use Mixbox (Louis's choice). Mixbox is licensed CC BY-NC 4.0: free for non-commercial use. The README credits it and says so.
- Ratios are whole parts, base first: lighter `10:1, 5:1, 3:1, 2:1, 1:1, 1:2, 1:3`; darker `20:1, 10:1, 5:1, 3:1, 2:1, 1:1` (black is much stronger than white, so its steps start smaller)
- The page says the result is a starting point to test, not an exact recipe (spec Goal 7)
- No database changes; the 77 existing tests keep passing

## Review Focus

1. **`requirements.txt` with no line break at the end.** Adding a package on the same line makes `gunicorn==27.0.1pymixbox==2.0.0`, which breaks the install on the server. Checked in Task 1.
2. **Slider order.** Left must always be darker and right lighter, for any color. Pinned in Task 1 (checked on 300+ random colors while planning).
3. **Pure white or pure black paints.** Every stop must still be a valid color. Pinned in Task 1.
4. **A used-up or missing paint.** Shade works for used-up paints; a missing id gives 404. Pinned in Task 2.
5. **The page without JavaScript.** The full list of mixes is printed on the page too, so it's useful even if the slider script fails. Pinned in Task 2.

---

### Task 1: Shading rules

**Files:** Modify `requirements.txt`; create `shading.py`, `tests/test_shading.py`

**Interfaces:**
- Produces: `WHITE`, `BLACK` (RGB tuples), `LIGHTER`, `DARKER` (lists of `(base_parts, partner_parts)`), `hex_to_rgb(color) -> tuple`, `rgb_to_hex(rgb) -> str`, `parts(count, name) -> str`, `mix(base_color, partner, base_parts, partner_parts) -> str`, `shade_steps(base_color) -> list[dict]` (each `{"color", "label"}`, darkest first, the paint itself at index `len(DARKER)` labeled "Straight from the jar")

- [ ] **Step 1:** Add `pymixbox==2.0.0` to `requirements.txt` on its own line, then `pip install -r requirements-dev.txt`
- [ ] **Step 2: Write the failing tests** (`tests/test_shading.py`)

```python
from shading import hex_to_rgb, rgb_to_hex, parts, mix, shade_steps, WHITE, BLACK, LIGHTER, DARKER

BLUE = "#1d4e9e"


def brightness(color):
    r, g, b = hex_to_rgb(color)
    return r + g + b


def test_hex_and_rgb_convert_both_ways():
    assert hex_to_rgb(BLUE) == (29, 78, 158)
    assert rgb_to_hex((29, 78, 158)) == BLUE


def test_parts_uses_singular_for_one():
    assert parts(1, "white") == "1 part white"
    assert parts(3, "base") == "3 parts base"


def test_mixing_with_white_is_lighter_and_black_is_darker():
    assert brightness(mix(BLUE, WHITE, 2, 1)) > brightness(BLUE)
    assert brightness(mix(BLUE, BLACK, 2, 1)) < brightness(BLUE)


def test_steps_have_the_paint_itself_in_the_middle():
    steps = shade_steps(BLUE)
    assert len(steps) == len(DARKER) + 1 + len(LIGHTER)
    middle = steps[len(DARKER)]
    assert middle == {"color": BLUE, "label": "Straight from the jar"}


def test_steps_go_from_darkest_to_lightest():
    values = [brightness(step["color"]) for step in shade_steps(BLUE)]
    assert values == sorted(values)


def test_step_labels():
    steps = shade_steps(BLUE)
    assert steps[0]["label"] == "1 part base : 1 part black"
    assert steps[len(DARKER) - 1]["label"] == "20 parts base : 1 part black"
    assert steps[len(DARKER) + 1]["label"] == "10 parts base : 1 part white"
    assert steps[-1]["label"] == "1 part base : 3 parts white"


def test_works_for_white_and_black_paints():
    for color in ("#ffffff", "#000000"):
        steps = shade_steps(color)
        assert all(step["color"].startswith("#") and len(step["color"]) == 7 for step in steps)
```

- [ ] **Step 3:** Run, expect `ModuleNotFoundError: No module named 'shading'`
- [ ] **Step 4:** Write `shading.py`. `mix` turns the parts into an amount (`partner_parts / (base_parts + partner_parts)`) and calls `mixbox.lerp`. `shade_steps` builds the darker list, reverses it so the darkest comes first, then adds the paint itself and the lighter list.
- [ ] **Step 5:** `pytest`, expect 84 passed
- [ ] **Step 6:** Commit: "Add shading rules with Mixbox"

### Task 2: Shade page

**Files:** Modify `app.py`, `templates/paints.html`, `static/style.css`; create `templates/shade.html`, `tests/test_shade_page.py`

**Interfaces:**
- Consumes: `shade_steps`, `DARKER` (Task 1); `get_paint_or_404` (stage 2)
- Produces: route `shade_paint` at `/paints/<int:paint_id>/shade` (GET), rendering `shade.html` with `paint`, `steps`, and `start` (`len(DARKER)`, the slider's starting stop)

- [ ] **Step 1: Write the failing tests** (`tests/test_shade_page.py`)

```python
import db

PAINT = {"name": "Gundam Blue", "brand": "Mr. Color", "code": "C-5", "color": "#1d4e9e",
         "quantity": "1", "notes": ""}


def add_paint(client):
    client.post("/paints/new", data=PAINT)
    conn = db.get_db()
    paint_id = conn.execute("SELECT id FROM paints").fetchone()["id"]
    conn.close()
    return paint_id


def test_shade_page_shows_every_mix(client):
    paint_id = add_paint(client)
    page = client.get(f"/paints/{paint_id}/shade")
    assert page.status_code == 200
    assert b"Shade Gundam Blue" in page.data
    assert b"Straight from the jar" in page.data
    assert b"10 parts base : 1 part white" in page.data
    assert b"20 parts base : 1 part black" in page.data


def test_paint_card_links_to_shade_page(client):
    paint_id = add_paint(client)
    assert f'href="/paints/{paint_id}/shade"'.encode() in client.get("/paints").data


def test_shade_page_for_missing_paint_is_not_found(client):
    assert client.get("/paints/999/shade").status_code == 404
```

- [ ] **Step 2:** Run, expect 2 failed, 85 passed (the not-found test passes early, as in earlier stages, because the route doesn't exist yet)
- [ ] **Step 3:** Write the route, `shade.html` (two big swatches, the ratio, a range slider from 0 to the last stop starting at `start`, the "starting point" note, an "All mixes" list, a Back link, and a short script that reads `steps` through `tojson` and updates the preview and ratio on `input`), a "Shade" button on each paint card, and the styles
- [ ] **Step 4:** `pytest`, expect 87 passed; try the slider at phone size
- [ ] **Step 5:** Commit: "Add the shading mixer page"

### Task 3: README and deploy

- [ ] **Step 1:** README: Features (shading mixer), Built With (Mixbox, with its non-commercial license and a link), Project Structure (`shading.py`), What I Learned (Louis's words), Roadmap (remove the mixer)
- [ ] **Step 2:** `pytest`, `git status`, commit, `git push`
- [ ] **Step 3:** On the server: `cd ~/gunpla-tracker`, `git pull`, `docker compose up -d --build`; then open a paint's Shade page on the phone
