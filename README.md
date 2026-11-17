# Gunpla Tracker

A web app I'm building to keep track of my Gunpla collection. It shows every kit I own and how far along each build is, and I can search it from my phone, like when I'm in a hobby store and can't remember if I already have a kit.

It uses the same stack as my [SpoolManager](https://github.com/louisdimaano/spool-manager) project.

## Features

- Add, edit, and delete kits (name, grade, kit number, series, status, difficulty, build quality, notes)
- Build progress on every kit: Not Started, Snapped Fit, Built, Painted
- A finished date that fills in by itself when a kit is marked Built or Painted, and can be typed in by hand for kits I finished before I had the app
- Search by name, and sort by name, grade, series, kit number, or status
- Series suggestions while typing, so the same series doesn't get spelled three different ways
- Works on phones, with light and dark mode

## Built With

- Python and Flask
- SQLite (Python's built-in sqlite3, no ORM)
- Jinja templates, HTML, and CSS
- pytest, including page tests with Flask's test client

## How the Finished Date Works

| What happens | Finished date |
| --- | --- |
| A new kit is added as Built or Painted with no date | Today |
| A date is typed in (backfilling an older build) | The typed date |
| Status changes from Built to Painted and the date isn't touched | Moves to today |
| The date is changed by hand | The typed date |
| Status changes back to Not Started or Snapped Fit | Cleared |

## Project Structure

```
gunpla-tracker/
├── app.py              # Routes and page logic
├── kits.py             # Form checks, the finished-date rule, and sorting
├── db.py               # Database connection and setup
├── schema.sql          # Database table
├── templates/          # Jinja page templates
├── static/style.css    # Styles
├── tests/              # pytest tests
└── docs/               # Design and build plan
```

## Running It Locally

```
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5001. The database (`kits.db`) is created automatically on the first run.

> **Note:** there is no login, so only run this on a private network. Don't expose it to the internet.

## Running the Tests

```
pip install -r requirements-dev.txt
pytest
```

Each test gets its own empty database, so running the tests never touches my real collection.

## What I Learned

- Writing each test before the code and watching it fail first. Two tests passed before their feature even existed, which meant they weren't testing anything, so they had to be rewritten.
- Testing whole pages with Flask's test client, not just single functions
- Giving every test its own temporary database with pytest fixtures and `monkeypatch`
- Keeping the rules (form checks, dates, sorting) in their own file so they can be tested without a web page
- Making `%` and `_` in a search match literally in a SQL `LIKE` search
- Sorting with key functions and tuples, and putting missing values last so Python never has to compare a number with `None`
- Using GET for searches and POST for anything that changes data, so following a link can never delete a kit
- CSS variables for light and dark mode, and `clip-path` for the cut corners on the cards

## Roadmap

- Paints and tools inventory with search
- Run it in Docker on my home server and reach it from my phone anywhere over Tailscale
- A "what should I build next" suggestion that follows my plan: HGs first, then alternate RG and HG
- A shading mixer that gives a mixing ratio for lighter or darker versions of a paint
- Scan paint barcodes with my phone camera, and remember them for rebuys

This is a personal fan project and isn't affiliated with Bandai.